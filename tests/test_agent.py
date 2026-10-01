from types import SimpleNamespace

from spam_agent import classifier, main, rules
from spam_agent.classifier import Verdict


def email(sender, subject="hi", thread="t1", id="m1"):
    return {"id": id, "thread_id": thread, "from": sender, "subject": subject, "body": "..."}


def test_rules_from_inbox_survey():
    assert rules.rule_category(email("LinkedIn <jobalerts-noreply@linkedin.com>")) == "job_alert"
    assert rules.rule_category(email("LinkedIn <inmail-hit-reply@linkedin.com>")) == "keep"
    assert rules.rule_category(email("Workday <noreply@dassault.myworkday.com>")) == "keep"
    assert rules.rule_category(email("x <alerts@noreply12.jobs2web.com>")) == "job_alert"
    assert rules.rule_category(email("Zalando <message@prive.zalando.fr>")) == "newsletter_promo"
    assert rules.rule_category(email("Ethos <team@ethos.expert>")) == "cold_pitch"
    assert rules.rule_category(email("Random <someone@example.com>")) is None
    # lookalike domains must not match the allowlist
    assert rules.rule_category(email("GitHub <noreply@github.com.evil.io>")) is None
    assert rules.rule_category(email("GitHub <noreply@notgithub.com>")) is None


def test_low_confidence_junk_is_kept():
    d = main.decide(email("a@b.com"), Verdict(category="cold_pitch", confidence=0.5, reason="x"))
    assert d["category"] == "keep" and not d["archive"]


def test_llm_error_is_kept():
    d = main.decide(email("a@b.com"), RuntimeError("boom"))
    assert d["category"] == "keep" and d["source"] == "error"


def test_security_subject_never_archived():
    e = email("x@weird.io", subject="Your verification code")
    d = main.decide(e, Verdict(category="phishing", confidence=0.95, reason="x"))
    assert d["label"] == "spam-agent/phishing" and not d["archive"]


def test_prompt_renders():
    from langchain_core.prompts import ChatPromptTemplate
    p = ChatPromptTemplate.from_messages([("system", classifier.SYSTEM), ("human", classifier.HUMAN)])
    out = p.invoke(classifier.to_prompt_input(email("a@b.com") | {"list_unsubscribe": True}))
    assert "Has List-Unsubscribe header: yes" in out.messages[1].content


def test_run_dry_and_apply(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    inbox = [
        email("LinkedIn <jobalerts-noreply@linkedin.com>", thread="t1", id="m1"),
        email("Shop <deals@shop.example>", "50% off", thread="t2", id="m2"),
        email("Friend <friend@example.com>", "dinner?", thread="t3", id="m3"),
        email("Shop <deals@shop.example>", "re: dinner", thread="t3", id="m4"),  # same thread as a keep
    ]
    calls = []
    fake_gmail = SimpleNamespace(
        get_service=lambda: None,
        list_message_ids=lambda s, q, n: [e["id"] for e in inbox],
        get_email=lambda s, i: next(e for e in inbox if e["id"] == i),
        ensure_labels=lambda s, names: {n: "L_" + n for n in names},
        modify_thread=lambda s, tid, add, remove: calls.append((tid, add, remove)),
    )
    monkeypatch.setitem(__import__("sys").modules, "spam_agent.gmail", fake_gmail)
    import spam_agent
    monkeypatch.setattr(spam_agent, "gmail", fake_gmail, raising=False)

    def fake_classify(chain, emails, **kw):
        return [Verdict(category="keep", confidence=0.9, reason="personal") if "Friend" in e["from"]
                else Verdict(category="newsletter_promo", confidence=0.9, reason="sale") for e in emails]

    monkeypatch.setattr(main, "build_chain", lambda: None)
    monkeypatch.setattr(main, "classify_many", fake_classify)

    main.run("q", 10, apply=False, reprocess=False)
    assert calls == [] and not (tmp_path / "state.json").exists()

    main.run("q", 10, apply=True, reprocess=False)
    assert ("t1", ["L_jobs/internships"], []) in calls
    assert ("t2", ["L_spam-agent/promo"], ["INBOX"]) in calls
    assert all(c[0] != "t3" for c in calls)

    calls.clear()
    assert main.run("q", 10, apply=True, reprocess=False) == [] and calls == []
