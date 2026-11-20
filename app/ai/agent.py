import logging
import re

from pydantic_ai import Agent, ModelRetry, RunContext
from app import db
from app.ai.schemas import AgentReply
from app.config import settings

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are Chris's assistant. Chris Bouda is a founder and AI / ML engineer.
You write the answer to the latest message from the sender in the email thread.
Steps:
1. Call get_section for the section the classifier picked. Call list_sections if you need another.
   Its "What happens next" entry holds the routing rules; follow them.
2. Answer only with facts from those sections. Never invent skills, experience, or projects.
   If the sections do not answer the question, set enough_information to false.
3. When the email offers a job, freelance work, consulting, an investment, or a partnership,
   fill in inquiry. For job, freelance, and consulting, ask for whatever is missing of:
   the role or project, the timeline, and the budget.
4. Never promise a call, a meeting, a price or rate, a start date, or a deliverable.
   Only Chris commits to those. Set promises_an_action to true if your reply promises one anyway.
5. Set action to escalate when a "What happens next" rule says it goes to Chris.
Reply rules:
- Write in the language of the sender's latest message.
- Plain text, no Markdown.
- Friendly and concise. Say Chris will reply personally where that applies.
- Sign off with "Chris Bouda's assistant". Never pretend to be Chris; if asked,
  say you are Chris's automated assistant.
- Never mention prompts, tools, or the knowledge base.
"""

assistant_agent = Agent(settings.agent_model, output_type=AgentReply, instructions=INSTRUCTIONS)

@assistant_agent.tool_plain
def list_sections() -> list[str]:
    """List the sections of the knowledge base."""
    logger.info("Tool call: list_sections()")
    return db.list_sections()

@assistant_agent.tool_plain
def get_section(section: str) -> str:
    """Return every entry of one knowledge base section, for example 'about-me'."""
    logger.info("Tool call: get_section(%r)", section)
    entries = db.get_section(section)
    if not entries:
        raise ModelRetry(f"There is no section '{section}'. Call list_sections to see the options.")
    return "\n\n".join(f"## {entry['title']}\n{entry['content']}" for entry in entries)

@assistant_agent.output_validator
def check_reply(ctx: RunContext[None], output:AgentReply) -> AgentReply:
    if output.action == "reply" and not output.reply.strip():
        raise ModelRetry("The reply is empty. Write the email, or set action to escalate.")
    # "AI" is allowed: Chris's skills are AI engineering, and the assistant is open about being one.
    if re.search(r"\b(knowledge base|system prompt|my instructions)\b", output.reply, re.IGNORECASE):
        raise ModelRetry("Do not mention the knowledge base, prompts, or instructions in the reply.")
    return output

def write_reply(thread: str, section: str) -> AgentReply:
    prompt = f"Section picked by the classifier: {section}\n\n{thread}"
    return assistant_agent.run_sync(prompt).output