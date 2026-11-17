from app.ai.schemas import Inquiry

# Steps where the reply goes to the sender, because they have to send something first.
SENDER_STEPS = {"ask-details"}

# Opportunities the assistant may handle until all details are in.
WORK_KINDS = {"job", "freelance", "consulting"}


def resolve_inquiry(inquiry: Inquiry) -> str:
    """Decide the next step for an opportunity. The model reports, Python decides.

    - "ask-details": reply asking for what is missing (see missing_details).
    - "pass-to-chris": details complete; thank them, Chris reviews it personally.
    - "escalate": Chris handles it from the start (investors, partnerships, anything else).
    """
    if inquiry.kind not in WORK_KINDS:
        return "escalate"
    if missing_details(inquiry):
        return "ask-details"
    return "pass-to-chris"


def missing_details(inquiry: Inquiry) -> list[str]:
    """The details about-me.md says to ask for, that the sender has not given yet."""
    missing = []
    if not inquiry.role_or_project:
        missing.append("the role or project")
    if not inquiry.timeline:
        missing.append("the timeline")
    if not inquiry.budget:
        missing.append("the budget")
    return missing
