from typing import Literal

from pydantic import BaseModel, Field

# One value per file in knowledge_base/ (the file stem is the section name).
Section = Literal["about-me"]


class Classification(BaseModel):
    """First pass on an incoming email to Chris: what it is about and who must handle it."""

    section: Section = Field(description="Knowledge base section that can answer this email")
    language: str = Field(description="Language of the sender's latest message, e.g. English")
    needs_human: bool = Field(
        description=(
            "True when Chris must answer personally: investor or partnership interest, "
            "anything personal or sensitive, or a request for a call, meeting, price, "
            "start date or deliverable"
        )
    )
    reason: str = Field(description="One sentence explaining the classification")
    acknowledgement: str = Field(
        description="Short note to the sender, in their language, that Chris will reply personally"
    )


class Inquiry(BaseModel):
    """Details of an opportunity someone is offering Chris."""

    kind: Literal["job", "freelance", "consulting", "investor", "partnership", "other"]
    organization: str | None = Field(default=None, description="Company or person behind it")
    role_or_project: str | None = Field(
        default=None, description="The role offered or the project to build, in a few words"
    )
    skills_requested: list[str] = Field(
        default_factory=list,
        description="Skills they ask for, e.g. AI engineering, ML engineering, backend",
    )
    timeline: str | None = Field(default=None, description="Start date or deadline, as stated")
    budget: str | None = Field(default=None, description="Salary, rate or budget, as stated")


class AgentReply(BaseModel):
    """The agent's answer to an email, written on Chris's behalf from the knowledge base only."""

    action: Literal["reply", "escalate"]
    reply: str = Field(description="The email to the sender, plain text")
    reasoning: str = Field(description="Which knowledge base entries you used and why")
    enough_information: bool = Field(
        description="True when the knowledge base answers the question about Chris or Chris's work"
    )
    promises_an_action: bool = Field(
        description=(
            "True when the reply promises a call, meeting, price, start date, deliverable "
            "or anything else only Chris can commit to"
        )
    )
    inquiry: Inquiry | None = Field(
        default=None,
        description="Fill in when the email offers a job, freelance, consulting, investment or partnership",
    )


class Decision(BaseModel):
    """Final outcome stored on the ticket."""

    action: Literal["reply", "escalate"]
    section: str
    reply: str
    reason: str
    proposed_action: str | None = Field(
        default=None,
        description="What Chris should do next, e.g. 'review freelance offer from Acme'",
    )
