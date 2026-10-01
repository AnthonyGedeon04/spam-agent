"""Run the spam agent: fetch inbox mail, classify it, then label/archive (or just report in dry-run)."""

import argparse
import json
import os
from collections import Counter

from . import config, rules
from .classifier import build_chain, classify_many

STATE_FILE = "state.json"


def load_state() -> set[str]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_state(seen: set[str]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen), f)


def decide(email: dict, verdict) -> dict:
    """Turn a category (from a rule or the LLM) into the action to take."""
    if isinstance(verdict, str):
        category, confidence, reason, source = verdict, 1.0, "matched a sender rule", "rule"
    elif isinstance(verdict, Exception):
        category, confidence, reason, source = "keep", 0.0, f"LLM error, kept: {verdict}", "error"
    else:
        category, confidence, reason, source = verdict.category, verdict.confidence, verdict.reason, "llm"
        if category != "keep" and confidence < config.MIN_CONFIDENCE:
            reason = f"low confidence ({confidence:.2f}) {category}, kept: {reason}"
            category = "keep"

    action = dict(config.ACTIONS[category])
    if source == "llm" and action["archive"] and rules.looks_like_security_mail(email):
        action["archive"] = False
        reason += " (security-looking subject, labeled but left in inbox)"
    return {"category": category, "confidence": confidence, "reason": reason, "source": source, **action}


def run(query: str, limit: int, apply: bool, reprocess: bool) -> list[dict]:
    from . import gmail  # imported here so tests don't need Google libraries configured

    service = gmail.get_service()
    seen = set() if reprocess else load_state()
    ids = [i for i in gmail.list_message_ids(service, query, limit) if i not in seen]
    emails = [gmail.get_email(service, i) for i in ids]
    print(f"{len(emails)} new message(s) matching {query!r}")
    if not emails:
        return []

    verdicts: list = [rules.rule_category(e) for e in emails]
    need_llm = [i for i, v in enumerate(verdicts) if v is None]
    if need_llm:
        llm_results = classify_many(build_chain(), [emails[i] for i in need_llm])
        for i, r in zip(need_llm, llm_results):
            verdicts[i] = r

    decisions = [decide(e, v) | {"email": e} for e, v in zip(emails, verdicts)]

    if apply:
        label_names = sorted({d["label"] for d in decisions if d["label"]})
        label_ids = gmail.ensure_labels(service, label_names) if label_names else {}
        # Gmail labels whole threads; never move a thread that also holds a message we want to keep.
        keep_threads = {d["email"]["thread_id"] for d in decisions if d["category"] == "keep"}
        done_threads = set()
        for d in decisions:
            tid = d["email"]["thread_id"]
            if tid in done_threads or tid in keep_threads or (not d["label"] and not d["archive"]):
                continue
            add = [label_ids[d["label"]]] if d["label"] else []
            remove = ["INBOX"] if d["archive"] else []
            gmail.modify_thread(service, tid, add, remove)
            done_threads.add(tid)

    # Only remember messages once acted on, so a dry run never hides mail from a later --apply.
    # LLM errors are retried next run.
    if apply:
        save_state(seen | {d["email"]["id"] for d in decisions if d["source"] != "error"})
    report(decisions, apply)
    return decisions


def report(decisions: list[dict], applied: bool) -> None:
    print("\nAPPLIED" if applied else "\nDRY RUN (nothing changed in Gmail; add --apply to act)")
    for d in decisions:
        e = d["email"]
        what = []
        if d["label"]:
            what.append(f"label {d['label']}")
        if d["archive"]:
            what.append("archive")
        print(f"- [{d['category']:<16}] {e['from'][:40]:<40} | {e['subject'][:60]}")
        print(f"    {', '.join(what) or 'leave as is'} ({d['source']}): {d['reason']}")
    counts = Counter(d["category"] for d in decisions)
    print("\nSummary:", ", ".join(f"{k}={v}" for k, v in counts.most_common()))


def load_dotenv(path: str = ".env") -> None:
    """Read KEY=value lines from .env into the environment (no extra dependency needed)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:  # utf-8-sig tolerates a Windows BOM
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def cli() -> None:
    p = argparse.ArgumentParser(description="Classify and sort Gmail junk with LangChain + Claude.")
    p.add_argument("--query", default=config.DEFAULT_QUERY, help="Gmail search query to process.")
    p.add_argument("--limit", type=int, default=50, help="Max messages per run.")
    p.add_argument("--apply", action="store_true", help="Actually label/archive. Default is a dry run.")
    p.add_argument("--reprocess", action="store_true", help="Ignore state.json and look at everything again.")
    args = p.parse_args()
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is missing. Put it in a .env file in this folder (README step 4).")
    if not os.path.exists("credentials.json") and not os.path.exists("token.json"):
        raise SystemExit("credentials.json is missing. Download it from Google Cloud into this folder (README step 5).")
    run(args.query, args.limit, args.apply, args.reprocess)


if __name__ == "__main__":
    cli()
