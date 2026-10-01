"""Everything you are likely to tweak lives here."""

import os

MODEL = os.environ.get("SPAM_AGENT_MODEL", "claude-haiku-4-5-20251001")

# Below this confidence the LLM's junk verdict is ignored and the mail is kept.
MIN_CONFIDENCE = 0.75

# Which inbox mail to look at on each run.
DEFAULT_QUERY = "in:inbox newer_than:2d"

# Category -> what to do with it. "archive" removes the INBOX label; nothing is ever deleted.
ACTIONS = {
    "keep": {"label": None, "archive": False},
    "job_alert": {"label": "jobs/internships", "archive": False},
    "newsletter_promo": {"label": "spam-agent/promo", "archive": True},
    "cold_pitch": {"label": "spam-agent/cold-pitch", "archive": True},
    "phishing": {"label": "spam-agent/phishing", "archive": True},
}

# Rules run before the LLM. A match here decides the category without an API call.
# Patterns match the lowercased sender address: "@domain" matches the domain and its
# subdomains, "prefix@" matches a mailbox at any domain, anything else must match exactly.

ALWAYS_KEEP = [
    # Recruiters and application acknowledgements
    "inmail-hit-reply@linkedin.com", "hit-reply@linkedin.com",
    "messaging-digest-noreply@linkedin.com",  # "X just messaged you": real people
    "@lvmh.com", "@louisvuitton.com",
    "@3ds.com", "@dior.com", "@engie.com", "safran@profils.org",
    "@myworkday.com", "@teamtailor.com", "@talent-feedback.com",
    # Security codes, receipts, tickets
    "@github.com", "@ameli.fr", "@caf.fr", "@adp.com", "@hellowork.com",
    "@flyingblue.com", "@accounts.google.com", "@google.com",
    "@anthropic.com", "noreply@connect.sncf", "@flixbus.com", "@blablacar.com",
    "@booking.com", "@thy.com", "@turkishairlines.com",
]

JOB_ALERT_SENDERS = [
    "jobalerts-noreply@linkedin.com", "jobs-noreply@linkedin.com",
    "noreply@jobright.ai", "notify@mg.flexjobs.com",
    "donotreply@match.indeed.com", "donotreply@jobalert.indeed.com",
    "support@builtin.com", "@noreply12.jobs2web.com", "info@mail.joinleland.com",
]

KNOWN_PROMO_SENDERS = [
    "message@prive.zalando.fr", "microsoftstore@microsoftstore.microsoft.com",
    "microsoft365@infoemail.microsoft.com", "hello@students.udemy.com",
    "no-reply@mail.suyool.com", "noreply@news.paypal.com", "info@mail.sncf-connect.com",
    "calhl@e-ca-loirehauteloire.fr", "info@mag.mercipourlinfo.fr", "uber@uber.com",
    "survey@shotguntheapp.com", "bolbol@flypgs.com", "newsletters-noreply@linkedin.com",
]

KNOWN_COLD_PITCH_SENDERS = [
    "team@ethos.expert",
]

# Subject keywords that look like security mail (OTP codes, password resets). Phishing copies these,
# so they still go to the LLM, but a junk verdict on them only labels the mail and never archives it.
SECURITY_SUBJECT_HINTS = [
    "verification code", "security code", "one-time", "otp", "code de vérification",
    "code de sécurité", "password reset", "réinitialisation", "sign-in", "connexion",
]
