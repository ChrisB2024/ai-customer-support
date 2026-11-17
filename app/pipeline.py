import logging
from email.utils import parseaddr

from app import db
from app.gmail import PROCESSED_LABEL, Gmail, get_body, get_headers
from app.guards import skip_reason

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3

ACKNOWLEDGEMENT = """Hi,

Thanks for your email. We received your message and will get back to you soon.

Christopher Bouda Support!
"""

def handle_message(gmail: Gmail, message_id: str) -> None:
    event = db.start_event(message_id)
    if event is None:
        # Not claimable: either finished (label may have failed last time) or
        # still 'processing'. Only label finished ones; a crashed 'processing'
        # claim must stay unlabeled so a later poll can reclaim it once stale.
        if db.get_event_status(message_id) in ("processed", "skipped"):
            gmail.add_label(message_id, PROCESSED_LABEL)
        return
    try:
        status, result = process(gmail, message_id)
        db.finish_event(event["id"], status, result)
    except Exception as error:
        db.fail_event(event["id"], str(error))
        if event["attempts"] >= MAX_ATTEMPTS:
            # Give up, so the message does not loop forever.
            gmail.add_label(message_id, PROCESSED_LABEL)
        raise
    # Outside the try: the work is recorded, so a label failure must not mark
    # the event failed. The next poll sees 'processed' above and retries the label.
    gmail.add_label(message_id, PROCESSED_LABEL)

def process(gmail: Gmail, message_id: str) -> tuple[str, dict]:
    message = gmail.get_message(message_id)
    headers = get_headers(message)

    reason = skip_reason(message, headers, gmail.address)
    if reason:
        return "skipped", {"reason": reason}
    
    sender = parseaddr(headers.get("from", ""))[1]

    ticket_id = db.upsert_ticket(message["threadId"], sender, headers.get("subject", ""))
    db.save_message(ticket_id, message_id, "in", sender, get_body(message))

    # On a retry the reply may already be out; never email the customer twice.
    if not db.has_reply(message_id):
        sent = gmail.send_reply(message, ACKNOWLEDGEMENT)
        db.save_message(ticket_id, sent["id"], "out", gmail.address, ACKNOWLEDGEMENT)
    db.update_ticket(ticket_id, "answered")
    return "processed", {"action": "acknowledged"}