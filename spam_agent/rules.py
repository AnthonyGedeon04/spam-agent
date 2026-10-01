"""Deterministic rules that run before the LLM."""

from email.utils import parseaddr

from . import config


def sender_address(from_header: str) -> str:
    return parseaddr(from_header)[1].lower()


def matches(address: str, patterns: list[str]) -> bool:
    if "@" not in address:
        return False
    local, domain = address.rsplit("@", 1)
    for p in patterns:
        p = p.lower()
        if p.startswith("@"):
            d = p[1:]
            if domain == d or domain.endswith("." + d):
                return True
        elif p.endswith("@"):
            if local + "@" == p:
                return True
        elif address == p:
            return True
    return False


def rule_category(email: dict) -> str | None:
    """Return a category if a rule decides it, else None (ask the LLM)."""
    address = sender_address(email["from"])

    if matches(address, config.ALWAYS_KEEP):
        return "keep"
    if matches(address, config.JOB_ALERT_SENDERS):
        return "job_alert"
    if matches(address, config.KNOWN_COLD_PITCH_SENDERS):
        return "cold_pitch"
    if matches(address, config.KNOWN_PROMO_SENDERS):
        return "newsletter_promo"
    return None


def looks_like_security_mail(email: dict) -> bool:
    subject = email.get("subject", "").lower()
    return any(h in subject for h in config.SECURITY_SUBJECT_HINTS)
