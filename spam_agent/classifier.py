"""LLM classification with LangChain + Claude."""

from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from . import config

Category = Literal["keep", "job_alert", "newsletter_promo", "cold_pitch", "phishing"]


class Verdict(BaseModel):
    category: Category = Field(description="Which bucket this email belongs in.")
    confidence: float = Field(ge=0, le=1, description="How sure you are, 0 to 1.")
    reason: str = Field(description="One short sentence explaining the call.")


SYSTEM = """You sort email for Anthony, a student job hunting for data science / ML internships in France.
Classify each email into exactly one category:

- keep: anything a person would want to see. Personal mail, replies, recruiters writing to Anthony directly, \
interview invites, application acknowledgements or rejections, receipts, invoices, tickets, bookings, \
bank or government notices, login/verification codes, password resets he asked for.
- job_alert: automated job-board digests or "new jobs matching your search" mail.
- newsletter_promo: marketing, sales, discounts, product announcements, newsletters, surveys, \
"we miss you", social network digests.
- cold_pitch: unsolicited one-to-one sales or recruiting-for-gigs outreach from someone Anthony never \
contacted, including "just following up" / "one last nudge" chains.
- phishing: tries to steal credentials or money. Signs: urgent account threats, mismatched sender domain \
vs. claimed brand, failed SPF/DKIM, links to lookalike domains, requests for passwords, payment or gift cards.

When unsure between keep and anything else, choose keep with low confidence. Missing a junk email is cheap; \
hiding a real one is expensive. Write the reason in English."""

HUMAN = """From: {sender}
To: {to}
Subject: {subject}
Date: {date}
Has List-Unsubscribe header: {list_unsubscribe}
Authentication results: {auth}

Body (truncated):
{body}"""


def build_chain(model: str = config.MODEL):
    llm = ChatAnthropic(model=model, temperature=0, max_tokens=300, max_retries=3)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])
    return prompt | llm.with_structured_output(Verdict)


def to_prompt_input(email: dict) -> dict:
    return {
        "sender": email["from"],
        "to": email.get("to", ""),
        "subject": email.get("subject", ""),
        "date": email.get("date", ""),
        "list_unsubscribe": "yes" if email.get("list_unsubscribe") else "no",
        "auth": email.get("auth") or "unknown",
        "body": email.get("body", "")[:4000],
    }


def classify_many(chain, emails: list[dict], max_concurrency: int = 5) -> list[Verdict | Exception]:
    inputs = [to_prompt_input(e) for e in emails]
    return chain.batch(inputs, config={"max_concurrency": max_concurrency}, return_exceptions=True)
