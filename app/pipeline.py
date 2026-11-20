import logging
from email.utils import parseaddr

from app import db
from app.ai.decide import decide
from app.gmail import (
    ESCALATED_LABEL,
    PROCESSED_LABEL,
    Gmail,
    format_thread,
    get_body,
    get_headers,
    has_attachments,
)
from app.guards import skip_reason

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


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

    thread = gmail.get_thread(message["threadId"])
    if gmail.is_escalated(thread):
        # Chris owns this thread until the needs-human label is removed.
        return "skipped", {"reason": "thread is escalated"}

    # On a retry the reply may already be out: never email the sender twice,
    # and skip the model calls too.
    if db.has_reply(message_id):
        return "processed", {"action": "already replied"}

    decision = decide(format_thread(thread, gmail.address), has_attachments(message))
    sent = gmail.send_reply(message, decision.reply)
    db.save_message(ticket_id, sent["id"], "out", gmail.address, decision.reply)

    if decision.action == "escalate":
        gmail.add_label(message_id, ESCALATED_LABEL)
        db.update_ticket(ticket_id, "escalated", decision.section, decision.proposed_action)
    else:
        db.update_ticket(ticket_id, "answered", decision.section, decision.proposed_action)
    return "processed", {
        "action": decision.action,
        "reason": decision.reason,
        "proposed_action": decision.proposed_action,
    }
