from app.ai.agent import write_reply
from app.ai.classifier import classify
from app.ai.rules import resolve_inquiry
from app.ai.schemas import Decision, Inquiry


def decide(thread: str, has_attachments: bool = False) -> Decision:
    """Run the AI steps for one email thread. The models propose, this function decides."""
    classification = classify(thread)

    def escalate(reason: str, proposed_action: str | None = None) -> Decision:
        return Decision(
            action="escalate",
            section=classification.section,
            reply=classification.acknowledgement,
            reason=reason,
            proposed_action=proposed_action,
        )

    if has_attachments:
        return escalate("The email has attachments", "Chris: review the attachments")
    if classification.needs_human:
        return escalate(classification.reason)

    answer = write_reply(thread, classification.section)
    if answer.action == "escalate":
        return escalate(answer.reasoning)
    if not answer.enough_information:
        return escalate("The knowledge base does not answer this")
    if answer.promises_an_action:
        return escalate("The reply promises something only Chris can commit to")

    proposed_action = None
    if answer.inquiry:
        step = resolve_inquiry(answer.inquiry)
        if step == "escalate":
            return escalate(f"{answer.inquiry.kind} inquiry", proposed_action=describe(answer.inquiry))
        if step == "pass-to-chris":
            # Sender gets the agent's reply; the ticket records what Chris should do next.
            proposed_action = describe(answer.inquiry)
        # "ask-details": the agent's reply asks the sender for what is missing.

    return Decision(
        action="reply",
        section=classification.section,
        reply=answer.reply,
        reason=answer.reasoning,
        proposed_action=proposed_action,
    )


def describe(inquiry: Inquiry) -> str:
    """One line for the ticket, e.g. 'Review freelance offer from Acme: RAG chatbot'."""
    text = f"Review {inquiry.kind} offer"
    if inquiry.organization:
        text += f" from {inquiry.organization}"
    if inquiry.role_or_project:
        text += f": {inquiry.role_or_project}"
    return text
