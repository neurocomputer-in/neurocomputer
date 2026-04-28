"""Email stdlib neuros — send / read / search / mark.

Default backend uses Python stdlib `imaplib` + `smtplib` (zero new deps).
A future Gmail-API backend slots in via `EMAIL_BACKEND=gmail`.

Filename `email_neuros.py` mirrors the `memory_neuros.py` precedent and
avoids shadowing Python's stdlib `email` package.
"""
from __future__ import annotations

import imaplib
import os
import smtplib
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, getaddresses
from html.parser import HTMLParser
from typing import Optional, Union

from ..neuro import neuro
from ..budget import Budget


class EmailError(RuntimeError):
    """Wraps IMAP / SMTP failures with operation context."""

    def __init__(self, operation: str, cause: Exception):
        self.operation = operation
        self.cause = cause
        super().__init__(f"{operation} failed: {cause}")


# ---- Config / domain auto-detect -------------------------------------------

# Single source of truth for domain → (imap_host, smtp_host) defaults.
_DOMAIN_DEFAULTS: dict[str, tuple[str, str]] = {
    "gmail.com": ("imap.gmail.com", "smtp.gmail.com"),
    "outlook.com": ("outlook.office365.com", "smtp.office365.com"),
    "hotmail.com": ("outlook.office365.com", "smtp.office365.com"),
    "yahoo.com": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com"),
}


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"{name} not set; configure with EMAIL_ADDR / EMAIL_APP_PASSWORD"
        )
    return val


def _resolve_hosts() -> tuple[str, int, str, int]:
    """Return (imap_host, imap_port, smtp_host, smtp_port).

    Hosts auto-detect from the EMAIL_ADDR domain if env unset; unknown
    domains require explicit EMAIL_IMAP_HOST/EMAIL_SMTP_HOST.
    """
    addr = _require_env("EMAIL_ADDR")
    domain = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""

    imap_host = os.getenv("EMAIL_IMAP_HOST")
    smtp_host = os.getenv("EMAIL_SMTP_HOST")

    if not imap_host or not smtp_host:
        defaults = _DOMAIN_DEFAULTS.get(domain)
        if defaults is None:
            raise RuntimeError(
                f"EMAIL_IMAP_HOST not set and domain '{domain}' not auto-detected; "
                f"set EMAIL_IMAP_HOST/EMAIL_SMTP_HOST explicitly"
            )
        imap_host = imap_host or defaults[0]
        smtp_host = smtp_host or defaults[1]

    imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "465"))
    return imap_host, imap_port, smtp_host, smtp_port


# ---- send -------------------------------------------------------------------

@neuro(
    effect="tool",
    kind="skill.email",
    name="neurolang.stdlib.email.send",
    budget=Budget(latency_ms=1500, cost_usd=0.0),
)
def send(
    to: Union[str, list[str]],
    subject: str,
    body: str,
    *,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    html: bool = False,
) -> dict:
    """Send an email via SMTP.

    Args:
        to: Single address or list of addresses (To: header).
        subject: Subject line.
        body: Plain text body (or HTML if html=True).
        cc: Carbon copy recipients (visible in headers).
        bcc: Blind carbon copy recipients (NOT in headers; in envelope).
        html: If True, body is treated as text/html.

    Returns:
        {"sent": True, "to": [...], "subject": "..."} on success.
    """
    addr = _require_env("EMAIL_ADDR")
    password = _require_env("EMAIL_APP_PASSWORD")
    _, _, smtp_host, smtp_port = _resolve_hosts()

    to_list = [to] if isinstance(to, str) else list(to)
    cc_list = list(cc or [])
    bcc_list = list(bcc or [])

    msg = EmailMessage()
    msg["From"] = addr
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    if html:
        msg.set_content(body, subtype="html")
    else:
        msg.set_content(body)

    envelope = to_list + cc_list + bcc_list

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(addr, password)
            smtp.send_message(msg, to_addrs=envelope)
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError("send", e) from e

    return {"sent": True, "to": to_list, "subject": subject}


# ---- HTML → text stripper (stdlib only) ------------------------------------

class _HTMLTextExtractor(HTMLParser):
    """Strip tags + script/style content; keep visible text."""

    _SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks).strip()


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text()


# ---- IMAP helpers + read ----------------------------------------------------

def _connect_imap() -> imaplib.IMAP4_SSL:
    addr = _require_env("EMAIL_ADDR")
    password = _require_env("EMAIL_APP_PASSWORD")
    imap_host, imap_port, _, _ = _resolve_hosts()
    try:
        client = imaplib.IMAP4_SSL(imap_host, imap_port)
        client.login(addr, password)
        return client
    except (imaplib.IMAP4.error, OSError) as e:
        raise EmailError("connect", e) from e


def _addr_list(header_val) -> list[str]:
    """Header value → list of bare addresses."""
    if header_val is None:
        return []
    pairs = getaddresses([str(header_val)])
    return [addr for _name, addr in pairs if addr]


def _extract_body(msg) -> str:
    """Pick best body: prefer text/plain; fall back to stripped HTML."""
    plain = msg.get_body(preferencelist=("plain",))
    if plain is not None:
        return plain.get_content().strip()
    html = msg.get_body(preferencelist=("html",))
    if html is not None:
        return _html_to_text(html.get_content())
    return ""


def _parse_message(uid: str, raw: bytes) -> dict:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    subject = msg["Subject"]
    subject_str = str(subject) if subject is not None else ""
    date_hdr = msg["Date"]
    try:
        dt = parsedate_to_datetime(str(date_hdr)) if date_hdr else None
        date_str = dt.isoformat() if dt is not None else ""
    except (TypeError, ValueError):
        date_str = str(date_hdr) if date_hdr else ""
    body = _extract_body(msg)
    snippet = body[:200]
    flags_hdr = msg.get("X-Flags", "")
    return {
        "uid": uid,
        "from": (_addr_list(msg["From"]) or [""])[0],
        "to": _addr_list(msg["To"]),
        "cc": _addr_list(msg["Cc"]),
        "subject": subject_str,
        "date": date_str,
        "body": body,
        "snippet": snippet,
        "unread": True,  # placeholder; refined when STORE flags wired
        "flagged": False,
    }


def _fetch_raw_messages(client: imaplib.IMAP4_SSL, uids: list[str]) -> list[tuple[str, bytes]]:
    """Fetch RFC822 for each UID; return list of (uid, raw_bytes)."""
    out: list[tuple[str, bytes]] = []
    for uid in uids:
        typ, data = client.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data:
            continue
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                out.append((uid, bytes(item[1])))
                break
    return out


@neuro(
    effect="tool",
    kind="skill.email",
    name="neurolang.stdlib.email.read",
    budget=Budget(latency_ms=2000, cost_usd=0.0),
)
def read(folder: str = "INBOX", *, n: int = 10, unread_only: bool = False) -> list[dict]:
    """Read up to `n` recent messages from `folder`.

    Args:
        folder: IMAP folder name (default "INBOX").
        n: Max messages to return.
        unread_only: If True, only fetch UNSEEN messages.

    Returns:
        List of dicts with keys: uid, from, to, cc, subject, date, body,
        snippet, unread, flagged.
    """
    client = _connect_imap()
    try:
        try:
            client.select(folder)
            criterion = "UNSEEN" if unread_only else "ALL"
            typ, data = client.uid("SEARCH", None, criterion)
            if typ != "OK":
                raise EmailError("read", RuntimeError(f"SEARCH returned {typ}"))
            raw_ids = (data[0] or b"").split() if data else []
            uids = [u.decode() for u in raw_ids][-n:]
            raw_messages = _fetch_raw_messages(client, uids)
            return [_parse_message(uid, raw) for uid, raw in raw_messages]
        except (imaplib.IMAP4.error, OSError) as e:
            raise EmailError("read", e) from e
    finally:
        try:
            client.logout()
        except Exception:
            pass


_FLAG_MAP: dict[str, tuple[str, str]] = {
    "seen":      ("+FLAGS", r"\Seen"),
    "unseen":    ("-FLAGS", r"\Seen"),
    "flagged":   ("+FLAGS", r"\Flagged"),
    "unflagged": ("-FLAGS", r"\Flagged"),
    "deleted":   ("+FLAGS", r"\Deleted"),
}


@neuro(
    effect="tool",
    kind="skill.email",
    name="neurolang.stdlib.email.mark",
    budget=Budget(latency_ms=800, cost_usd=0.0),
)
def mark(uid: str, flag: str, *, folder: str = "INBOX") -> bool:
    """Toggle an IMAP flag on a message.

    Args:
        uid: IMAP UID (as returned by `read` / `search`).
        flag: One of "seen", "unseen", "flagged", "unflagged", "deleted".
        folder: IMAP folder containing the UID.

    Returns:
        True on success, False if the server rejects the STORE.
    """
    if flag not in _FLAG_MAP:
        raise ValueError(
            f"Unknown flag {flag!r}; expected one of {list(_FLAG_MAP)}"
        )
    op, imap_flag = _FLAG_MAP[flag]
    client = _connect_imap()
    try:
        try:
            client.select(folder)
            typ, _ = client.uid("STORE", uid, op, f"({imap_flag})")
            return typ == "OK"
        except (imaplib.IMAP4.error, OSError) as e:
            raise EmailError("mark", e) from e
    finally:
        try:
            client.logout()
        except Exception:
            pass


@neuro(
    effect="tool",
    kind="skill.email",
    name="neurolang.stdlib.email.search",
    budget=Budget(latency_ms=2000, cost_usd=0.0),
)
def search(query: str, *, folder: str = "INBOX", n: int = 20) -> list[dict]:
    """Search messages with IMAP SEARCH syntax.

    The query string is passed verbatim to the IMAP server. Examples:
        search('FROM "boss@x.com" SINCE 1-Jan-2026')
        search('UNSEEN SUBJECT "invoice"')
        search('SINCE 1-Jan-2026 BEFORE 30-Apr-2026')

    Args:
        query: Raw IMAP SEARCH criterion (https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4).
        folder: IMAP folder name (default "INBOX").
        n: Max messages to return.

    Returns:
        List of message dicts (same shape as `read`).
    """
    client = _connect_imap()
    try:
        try:
            client.select(folder)
            typ, data = client.uid("SEARCH", None, query)
            if typ != "OK":
                raise EmailError("search", RuntimeError(f"SEARCH returned {typ}"))
            raw_ids = (data[0] or b"").split() if data else []
            uids = [u.decode() for u in raw_ids][-n:]
            raw_messages = _fetch_raw_messages(client, uids)
            return [_parse_message(uid, raw) for uid, raw in raw_messages]
        except (imaplib.IMAP4.error, OSError) as e:
            raise EmailError("search", e) from e
    finally:
        try:
            client.logout()
        except Exception:
            pass
