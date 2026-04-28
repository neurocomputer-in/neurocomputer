"""Tests for the email_neuros stdlib (send / read / search / mark).

All offline. Patches imaplib.IMAP4_SSL and smtplib.SMTP_SSL via monkeypatch
to inject fake clients that record calls and return canned RFC822 fixtures.
"""
from __future__ import annotations

import email as _stdemail
import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest


# ---- Fixtures: env + fake transports ---------------------------------------

@pytest.fixture
def email_env(monkeypatch):
    """Set up minimal valid env for email_neuros."""
    monkeypatch.setenv("EMAIL_ADDR", "alice@gmail.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "app-password-123")
    # Hosts auto-detect for @gmail.com — leave unset to exercise that path
    monkeypatch.delenv("EMAIL_IMAP_HOST", raising=False)
    monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)
    monkeypatch.delenv("EMAIL_BACKEND", raising=False)


@pytest.fixture
def fake_smtp(monkeypatch):
    """Patch smtplib.SMTP_SSL — returns a MagicMock recording calls."""
    import smtplib
    instance = MagicMock()
    instance.__enter__ = lambda self: self
    instance.__exit__ = lambda self, *a: None
    cls_mock = MagicMock(return_value=instance)
    monkeypatch.setattr(smtplib, "SMTP_SSL", cls_mock)
    return {"cls": cls_mock, "instance": instance}


def _build_rfc822(*, frm="alice@x.com", to="bob@y.com",
                  subject="Hello", body="Plain body.",
                  date="Tue, 28 Apr 2026 14:30:00 +0000",
                  html_body=None, encoded_subject=None) -> bytes:
    """Build an RFC822 message as bytes for IMAP fixtures."""
    msg = EmailMessage()
    msg["From"] = frm
    msg["To"] = to
    msg["Date"] = date
    if encoded_subject is not None:
        msg["Subject"] = encoded_subject
    else:
        msg["Subject"] = subject
    if html_body is None:
        msg.set_content(body)
    else:
        msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
    return bytes(msg)


def _make_fake_imap(*, fetched: list[bytes] | None = None,
                    search_uids: list[bytes] | None = None,
                    store_ok: bool = True):
    """Build a MagicMock that mimics imaplib.IMAP4_SSL just enough."""
    inst = MagicMock()
    inst.login.return_value = ("OK", [b"Logged in"])
    inst.select.return_value = ("OK", [b"1"])
    inst.logout.return_value = ("BYE", [b"bye"])

    uids = search_uids if search_uids is not None else [b"100 101 102"]
    inst.uid.side_effect = lambda *args, **kwargs: _imap_uid_dispatch(
        args, fetched or [], uids, store_ok
    )
    return inst


def _imap_uid_dispatch(args, fetched, search_uids, store_ok):
    """Route inst.uid('SEARCH'|'FETCH'|'STORE', ...) calls to canned responses."""
    op = args[0].upper()
    if op == "SEARCH":
        return ("OK", search_uids)
    if op == "FETCH":
        # Build a fake fetch response: list of (uid_meta, raw_bytes) tuples
        # imaplib returns: ("OK", [(b"100 (UID 100 RFC822 {N}", raw_bytes), b")"])
        responses: list = []
        for i, raw in enumerate(fetched):
            uid = 100 + i
            responses.append((f"{uid} (UID {uid} RFC822 {{{len(raw)}}}".encode(), raw))
            responses.append(b")")
        return ("OK", responses)
    if op == "STORE":
        return (("OK" if store_ok else "NO"), [b""])
    return ("OK", [b""])


# ---- Cycle 1: send tests ---------------------------------------------------

def test_send_plain_builds_correct_mime(email_env, fake_smtp):
    from neurolang.stdlib import email as email_mod
    result = email_mod.send("bob@y.com", "Hi", "Plain body text.")
    assert result == {"sent": True, "to": ["bob@y.com"], "subject": "Hi"}

    # SMTP_SSL constructed with auto-detected gmail host + port 465
    cls = fake_smtp["cls"]
    args, kwargs = cls.call_args
    assert args[0] == "smtp.gmail.com" or kwargs.get("host") == "smtp.gmail.com"
    assert args[1] == 465 or kwargs.get("port") == 465

    inst = fake_smtp["instance"]
    inst.login.assert_called_once_with("alice@gmail.com", "app-password-123")

    # send_message called with an EmailMessage
    inst.send_message.assert_called_once()
    msg = inst.send_message.call_args.args[0]
    assert isinstance(msg, EmailMessage)
    assert msg["From"] == "alice@gmail.com"
    assert msg["To"] == "bob@y.com"
    assert msg["Subject"] == "Hi"
    # Body has plain content
    assert "Plain body text." in msg.get_content()
    assert msg.get_content_type() == "text/plain"


def test_send_html_sets_html_subtype(email_env, fake_smtp):
    from neurolang.stdlib import email as email_mod
    email_mod.send("bob@y.com", "Hi", "<b>bold</b>", html=True)

    inst = fake_smtp["instance"]
    msg = inst.send_message.call_args.args[0]
    assert msg.get_content_type() == "text/html"
    assert "<b>bold</b>" in msg.get_content()


@pytest.fixture
def fake_imap(monkeypatch):
    """Patch imaplib.IMAP4_SSL — caller mutates `holder['inst']` to set canned data."""
    import imaplib
    holder: dict = {"inst": MagicMock()}

    def factory(*args, **kwargs):
        holder["host"] = args[0] if args else kwargs.get("host")
        holder["port"] = args[1] if len(args) > 1 else kwargs.get("port", 993)
        return holder["inst"]

    monkeypatch.setattr(imaplib, "IMAP4_SSL", factory)
    return holder


# ---- Cycle 2: read tests ---------------------------------------------------

def test_read_parses_basic_fields(email_env, fake_imap):
    raw = _build_rfc822(
        frm="alice@x.com",
        to="bob@y.com",
        subject="Hello world",
        body="Plain body.",
        date="Tue, 28 Apr 2026 14:30:00 +0000",
    )
    fake_imap["inst"] = _make_fake_imap(fetched=[raw], search_uids=[b"100"])

    from neurolang.stdlib import email as email_mod
    msgs = email_mod.read(n=1)
    assert len(msgs) == 1
    m = msgs[0]
    assert m["uid"] == "100"
    assert m["from"] == "alice@x.com"
    assert m["to"] == ["bob@y.com"]
    assert m["subject"] == "Hello world"
    assert m["date"].startswith("2026-04-28T14:30")
    assert "Plain body." in m["body"]
    assert m["snippet"].startswith("Plain body.")


def test_read_decodes_rfc2047_subject(email_env, fake_imap):
    # "héllo" base64-encoded UTF-8 in RFC2047 form
    raw = _build_rfc822(encoded_subject="=?UTF-8?B?aMOpbGxv?=")
    fake_imap["inst"] = _make_fake_imap(fetched=[raw], search_uids=[b"100"])

    from neurolang.stdlib import email as email_mod
    msgs = email_mod.read(n=1)
    assert msgs[0]["subject"] == "héllo"


def test_read_multipart_prefers_text_plain(email_env, fake_imap):
    raw = _build_rfc822(
        body="PLAIN PART",
        html_body="<p>HTML PART</p>",
    )
    fake_imap["inst"] = _make_fake_imap(fetched=[raw], search_uids=[b"100"])

    from neurolang.stdlib import email as email_mod
    msgs = email_mod.read(n=1)
    body = msgs[0]["body"]
    assert "PLAIN PART" in body
    assert "HTML PART" not in body


def test_read_html_only_falls_back_to_stripped_text(email_env, fake_imap):
    msg = EmailMessage()
    msg["From"] = "alice@x.com"
    msg["To"] = "bob@y.com"
    msg["Subject"] = "HTML only"
    msg["Date"] = "Tue, 28 Apr 2026 14:30:00 +0000"
    msg.set_content("<html><body><p>Hello <b>world</b></p>"
                    "<script>alert(1)</script></body></html>",
                    subtype="html")
    raw = bytes(msg)
    fake_imap["inst"] = _make_fake_imap(fetched=[raw], search_uids=[b"100"])

    from neurolang.stdlib import email as email_mod
    msgs = email_mod.read(n=1)
    body = msgs[0]["body"]
    assert "Hello" in body
    assert "world" in body
    # script content stripped
    assert "alert(1)" not in body
    # tags stripped
    assert "<b>" not in body
    assert "<script>" not in body


# ---- Cycle 3: search + unread_only -----------------------------------------

def test_read_unread_only_passes_unseen_filter(email_env, fake_imap):
    raw = _build_rfc822()
    inst = _make_fake_imap(fetched=[raw], search_uids=[b"100"])
    fake_imap["inst"] = inst

    from neurolang.stdlib import email as email_mod
    email_mod.read(n=1, unread_only=True)

    # Check that UID SEARCH was called with UNSEEN criterion
    search_calls = [c for c in inst.uid.call_args_list if c.args[0].upper() == "SEARCH"]
    assert len(search_calls) == 1
    # imaplib idiom: client.uid("SEARCH", None, "UNSEEN")
    assert search_calls[0].args[2] == "UNSEEN"


def test_search_passes_imap_syntax_through(email_env, fake_imap):
    raw = _build_rfc822(subject="From boss")
    inst = _make_fake_imap(fetched=[raw], search_uids=[b"100"])
    fake_imap["inst"] = inst

    from neurolang.stdlib import email as email_mod
    query = 'FROM "boss@x.com" SINCE 1-Jan-2026 UNSEEN'
    msgs = email_mod.search(query, n=5)
    assert len(msgs) == 1
    assert msgs[0]["subject"] == "From boss"

    # Search query passed through verbatim
    search_calls = [c for c in inst.uid.call_args_list if c.args[0].upper() == "SEARCH"]
    assert len(search_calls) == 1
    # imaplib accepts SEARCH criteria as splat positional args; we pass the
    # query as a single string so the server gets it verbatim
    assert query in [a for a in search_calls[0].args if isinstance(a, str)]


# ---- Cycle 4: mark tests ---------------------------------------------------

@pytest.mark.parametrize("flag,expected_op,expected_arg", [
    ("seen",      "+FLAGS", r"\Seen"),
    ("unseen",    "-FLAGS", r"\Seen"),
    ("flagged",   "+FLAGS", r"\Flagged"),
    ("unflagged", "-FLAGS", r"\Flagged"),
    ("deleted",   "+FLAGS", r"\Deleted"),
])
def test_mark_each_flag_maps_to_correct_store(email_env, fake_imap,
                                                flag, expected_op, expected_arg):
    inst = _make_fake_imap(search_uids=[])
    fake_imap["inst"] = inst

    from neurolang.stdlib import email as email_mod
    ok = email_mod.mark("100", flag)
    assert ok is True

    store_calls = [c for c in inst.uid.call_args_list if c.args[0].upper() == "STORE"]
    assert len(store_calls) == 1
    args = store_calls[0].args
    # imaplib idiom: client.uid("STORE", uid, "+FLAGS", "(\\Seen)")
    assert args[1] == "100"
    assert args[2] == expected_op
    assert expected_arg in args[3]


def test_mark_returns_false_on_imap_no(email_env, fake_imap):
    inst = _make_fake_imap(search_uids=[], store_ok=False)
    fake_imap["inst"] = inst

    from neurolang.stdlib import email as email_mod
    ok = email_mod.mark("100", "seen")
    assert ok is False


def test_mark_unknown_flag_raises(email_env, fake_imap):
    inst = _make_fake_imap()
    fake_imap["inst"] = inst

    from neurolang.stdlib import email as email_mod
    with pytest.raises(ValueError, match="Unknown flag"):
        email_mod.mark("100", "starred")


# ---- Cycle 5: config / errors / domain auto-detect -------------------------

def test_missing_email_addr_raises_at_first_use(monkeypatch, fake_smtp):
    monkeypatch.delenv("EMAIL_ADDR", raising=False)
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "x")

    from neurolang.stdlib import email as email_mod
    with pytest.raises(RuntimeError, match="EMAIL_ADDR not set"):
        email_mod.send("bob@y.com", "Hi", "body")


def test_missing_app_password_raises(monkeypatch, fake_smtp):
    monkeypatch.setenv("EMAIL_ADDR", "alice@gmail.com")
    monkeypatch.delenv("EMAIL_APP_PASSWORD", raising=False)

    from neurolang.stdlib import email as email_mod
    with pytest.raises(RuntimeError, match="EMAIL_APP_PASSWORD not set"):
        email_mod.send("bob@y.com", "Hi", "body")


@pytest.mark.parametrize("addr,imap_host,smtp_host", [
    ("alice@gmail.com",   "imap.gmail.com",        "smtp.gmail.com"),
    ("alice@outlook.com", "outlook.office365.com", "smtp.office365.com"),
    ("alice@hotmail.com", "outlook.office365.com", "smtp.office365.com"),
    ("alice@yahoo.com",   "imap.mail.yahoo.com",   "smtp.mail.yahoo.com"),
])
def test_domain_auto_detect(monkeypatch, fake_smtp, addr, imap_host, smtp_host):
    monkeypatch.setenv("EMAIL_ADDR", addr)
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "x")
    monkeypatch.delenv("EMAIL_IMAP_HOST", raising=False)
    monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)

    from neurolang.stdlib import email as email_mod
    email_mod.send("bob@y.com", "Hi", "body")

    cls = fake_smtp["cls"]
    args, kwargs = cls.call_args
    actual_host = args[0] if args else kwargs.get("host")
    assert actual_host == smtp_host


def test_unknown_domain_without_explicit_hosts_raises(monkeypatch, fake_smtp):
    monkeypatch.setenv("EMAIL_ADDR", "alice@some-corp.example")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "x")
    monkeypatch.delenv("EMAIL_IMAP_HOST", raising=False)
    monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)

    from neurolang.stdlib import email as email_mod
    with pytest.raises(RuntimeError, match="not auto-detected"):
        email_mod.send("bob@y.com", "Hi", "body")


def test_explicit_hosts_override_auto_detect(monkeypatch, fake_smtp):
    monkeypatch.setenv("EMAIL_ADDR", "alice@gmail.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "x")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.custom.example")
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.custom.example")
    monkeypatch.setenv("EMAIL_SMTP_PORT", "587")

    from neurolang.stdlib import email as email_mod
    email_mod.send("bob@y.com", "Hi", "body")

    cls = fake_smtp["cls"]
    args, kwargs = cls.call_args
    actual_host = args[0] if args else kwargs.get("host")
    actual_port = args[1] if len(args) > 1 else kwargs.get("port")
    assert actual_host == "smtp.custom.example"
    assert actual_port == 587


def test_email_error_wraps_smtp_auth_failure(email_env, fake_smtp):
    inst = fake_smtp["instance"]
    inst.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")

    from neurolang.stdlib import email as email_mod
    from neurolang.stdlib.email_neuros import EmailError
    with pytest.raises(EmailError) as exc_info:
        email_mod.send("bob@y.com", "Hi", "body")
    assert exc_info.value.operation == "send"
    assert isinstance(exc_info.value.cause, smtplib.SMTPAuthenticationError)


def test_send_cc_and_bcc_route_correctly(email_env, fake_smtp):
    from neurolang.stdlib import email as email_mod
    email_mod.send(
        "bob@y.com", "Hi", "body",
        cc=["c1@x.com", "c2@x.com"],
        bcc=["secret@x.com"],
    )

    inst = fake_smtp["instance"]
    msg = inst.send_message.call_args.args[0]
    # CC is a header
    assert msg["Cc"] == "c1@x.com, c2@x.com"
    # BCC is NOT a header (privacy) — but envelope must include it
    assert msg["Bcc"] is None
    # send_message accepts to_addrs kwarg with full envelope
    to_addrs = inst.send_message.call_args.kwargs.get("to_addrs")
    assert to_addrs is not None
    assert "bob@y.com" in to_addrs
    assert "c1@x.com" in to_addrs
    assert "secret@x.com" in to_addrs
