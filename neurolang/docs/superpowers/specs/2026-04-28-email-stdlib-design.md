# Email stdlib — design

**Status:** approved 2026-04-28
**Phase:** 1.9 (post `agent.delegate`)
**Module:** `neurolang/stdlib/email_neuros.py`
**Public namespace:** `neurolang.stdlib.email.*`

## Goal

Ship a minimal, testable, offline-friendly email integration for NeuroLang that lets agentic flows triage and send mail without per-provider client code. Default backend uses Python stdlib `imaplib` + `smtplib` (zero new dependencies). A second backend (Gmail API + OAuth) is explicitly out of scope for v1 but the namespace and call signatures are designed to absorb it without breakage.

## Non-goals

- `email.reply` w/ auto In-Reply-To / References threading
- Attachments (send + read attachment lists)
- Gmail API backend (kept as v1.1; design leaves room)
- IMAP IDLE / push notifications
- Interactive OAuth flows
- HTML rendering — body is plain-text only (HTML stripped on read; `html=True` on send sets MIME subtype)

## Architecture

Single private module `neurolang/stdlib/email_neuros.py`. The filename mirrors the existing `memory_neuros.py` precedent and avoids shadowing Python's stdlib `email` package.

`neurolang/stdlib/__init__.py` re-exports it under the public name `email`:

```python
from . import email_neuros as email
__all__ = ["web", "reason", "memory_neuros", "model", "voice", "agent", "email"]
```

Public catalog names remain `neurolang.stdlib.email.<fn>` exactly like the other namespaces.

Backend selection via `EMAIL_BACKEND` env var:
- `imap` (default) — Python stdlib `imaplib.IMAP4_SSL` + `smtplib.SMTP_SSL`. Per-call connect → close. No connection pool.
- `gmail` (future, not implemented in v1) — `google-api-python-client` + OAuth token at `~/.local/share/neurolang/gmail.json`.

In v1, `EMAIL_BACKEND=gmail` raises `NotImplementedError("gmail backend lands in v1.1")`. This is the seam where the second backend slots in.

## Surface (4 neuros)

```python
@neuro(effect="tool", kind="skill.email", name="neurolang.stdlib.email.send", ...)
def send(to: str | list[str], subject: str, body: str, *,
         cc: list[str] | None = None,
         bcc: list[str] | None = None,
         html: bool = False) -> dict: ...

@neuro(effect="tool", kind="skill.email", name="neurolang.stdlib.email.read", ...)
def read(folder: str = "INBOX", *, n: int = 10, unread_only: bool = False) -> list[dict]: ...

@neuro(effect="tool", kind="skill.email", name="neurolang.stdlib.email.search", ...)
def search(query: str, *, folder: str = "INBOX", n: int = 20) -> list[dict]: ...

@neuro(effect="tool", kind="skill.email", name="neurolang.stdlib.email.mark", ...)
def mark(uid: str, flag: str) -> bool: ...
```

`flag ∈ {"seen", "unseen", "flagged", "unflagged", "deleted"}`.

`search` accepts IMAP SEARCH syntax verbatim (e.g. `'FROM "boss@x.com" SINCE 1-Jan-2026 UNSEEN'`). The string is passed unchanged to the server; malformed syntax surfaces as `EmailError("search", IMAP4.error(...))`. Docstring shows three concrete examples so the planner reproduces correct syntax via the catalog rendering.

## Data shapes

`read` and `search` return `list[dict]`. Each dict:

```python
{
    "uid": "12345",                          # IMAP UID, stable per-folder
    "from": "alice@x.com",
    "to": ["bob@y.com"],
    "cc": [],
    "subject": "...",                        # RFC2047-decoded
    "date": "2026-04-28T14:30:00+00:00",     # ISO 8601, parsed via email.utils.parsedate_to_datetime
    "body": "plain text, HTML stripped",
    "snippet": "first 200 chars of body",
    "unread": True,
    "flagged": False,
}
```

`send` returns `{"sent": True, "to": [...], "subject": "..."}`. Agentic flows downstream of `send` need an explicit confirmation handle.

`mark` returns `bool` — `True` on success, `False` if IMAP STORE rejects the flag for that UID (rare; usually means UID expired).

## Configuration (env vars)

| Var                  | Default              | Notes                                    |
|----------------------|----------------------|------------------------------------------|
| `EMAIL_ADDR`         | (required at use)    | Full address. Used as login + `From:`.   |
| `EMAIL_APP_PASSWORD` | (required at use)    | App-specific password.                   |
| `EMAIL_IMAP_HOST`    | (domain auto-detect) | e.g. `imap.gmail.com`                    |
| `EMAIL_IMAP_PORT`    | `993`                | SSL                                      |
| `EMAIL_SMTP_HOST`    | (domain auto-detect) | e.g. `smtp.gmail.com`                    |
| `EMAIL_SMTP_PORT`    | `465`                | SSL                                      |
| `EMAIL_BACKEND`      | `imap`               | Future: `gmail`                          |

**Domain auto-detect** when hosts unset (single source of truth — a `_DOMAIN_DEFAULTS` dict keyed by suffix):

| Suffix                | IMAP host                 | SMTP host                  |
|-----------------------|---------------------------|----------------------------|
| `@gmail.com`          | `imap.gmail.com`          | `smtp.gmail.com`           |
| `@outlook.com`        | `outlook.office365.com`   | `smtp.office365.com`       |
| `@hotmail.com`        | `outlook.office365.com`   | `smtp.office365.com`       |
| `@yahoo.com`          | `imap.mail.yahoo.com`     | `smtp.mail.yahoo.com`      |

Unknown domain w/o explicit hosts → `RuntimeError("EMAIL_IMAP_HOST not set and domain '<x>' not auto-detected; set EMAIL_IMAP_HOST/EMAIL_SMTP_HOST explicitly")`.

Missing `EMAIL_ADDR` or `EMAIL_APP_PASSWORD` → `RuntimeError` raised on first call (not at import time).

## Effect / kind / budget

| Neuro    | effect | kind          | latency_ms | cost_usd |
|----------|--------|---------------|------------|----------|
| `send`   | `tool` | `skill.email` | 1500       | 0.0      |
| `read`   | `tool` | `skill.email` | 2000       | 0.0      |
| `search` | `tool` | `skill.email` | 2000       | 0.0      |
| `mark`   | `tool` | `skill.email` | 800        | 0.0      |

(IMAP TLS handshake dominates `read`/`search` latency budget.)

## Error handling

Custom exception:

```python
class EmailError(RuntimeError):
    def __init__(self, operation: str, cause: Exception):
        self.operation = operation
        self.cause = cause
        super().__init__(f"{operation} failed: {cause}")
```

Wraps any `imaplib.IMAP4.error`, `smtplib.SMTPException`, `socket.gaierror`, or `OSError` raised inside a connect/operate block. Re-raised so the planner sees a single, named failure mode.

Connection lifecycle: every call uses `try / finally` to close IMAP/SMTP cleanly even when the inner op raises. No leaked sockets.

HTML stripping: when reading a message whose only available body is `text/html`, strip via a stdlib-only `html.parser.HTMLParser` subclass that drops `<script>` / `<style>` content and emits text. No `bs4` dep introduced. multipart/alternative prefers `text/plain`; falls back to stripped HTML.

## Testing

All tests offline. Path: `tests/stdlib/test_email.py`.

Strategy: `unittest.mock.patch` on `imaplib.IMAP4_SSL` and `smtplib.SMTP_SSL` constructors injects fake clients that record calls and return canned responses. Canned RFC822 fixtures built via `email.message.EmailMessage` (real MIME, no string templating) so parsing is exercised against well-formed input.

Test list (~14 tests):

1. `send` — plain text builds correct MIME (`text/plain`, `From`, `To`, `Subject`)
2. `send` — `html=True` produces `text/html` MIME subtype
3. `send` — `cc` and `bcc` route correctly (BCC absent from headers, present in SMTP envelope)
4. `read` — From/To/Subject/Date parsed correctly
5. `read` — RFC2047 encoded subject (`=?UTF-8?B?...?=`) decoded
6. `read` — multipart/alternative prefers `text/plain` part
7. `read` — HTML-only message falls back to stripped text body
8. `read` — `unread_only=True` adds IMAP `UNSEEN` filter
9. `search` — IMAP SEARCH syntax passed through unchanged
10. `mark` — each flag (`seen`/`unseen`/`flagged`/`unflagged`/`deleted`) maps to correct IMAP STORE command
11. Missing `EMAIL_ADDR` → `RuntimeError` at first use
12. Unknown domain w/o explicit hosts → `RuntimeError` w/ helpful message
13. Domain auto-detect — `@gmail.com`, `@outlook.com`, `@yahoo.com` resolve correct hosts
14. `EmailError` wraps SMTP auth failure (`SMTPAuthenticationError`)

Target: <0.3s offline. Combined suite: 147 → 161 passing.

## Live demo

`examples/email_demo.py` — sends a self-test email to `EMAIL_ADDR` and reads it back via `email.read(folder="INBOX", n=1)`. Mirrors the "skip cleanly if creds missing" pattern from `examples/research_flow.py`:

```python
if not os.getenv("EMAIL_ADDR") or not os.getenv("EMAIL_APP_PASSWORD"):
    print("[skip] set EMAIL_ADDR + EMAIL_APP_PASSWORD to run the live demo")
    sys.exit(0)
```

## Files touched

- **New:** `neurolang/stdlib/email_neuros.py` (~250 lines)
- **New:** `tests/stdlib/test_email.py` (~300 lines)
- **New:** `examples/email_demo.py` (~40 lines)
- **Edit:** `neurolang/stdlib/__init__.py` (add `email_neuros as email` import)
- **Edit:** `neurolang/repl.py` — add `email` to `STDLIB_NAMESPACES` so the REPL banner picks it up
- **Edit:** `docs/STATUS.md` — flip "email stdlib" from "Next up" to "Just shipped"
- **Edit:** `docs/CHANGELOG.md` — Phase 1.9 entry

## Out of scope (v1.1+ candidates)

- `email.reply(uid, body)` — auto In-Reply-To / References header threading
- `email.send(..., attachments=[...])` — file attachments
- `email.read(..., include_attachments=True)` — return attachment list per message
- Gmail API backend (slot via `EMAIL_BACKEND=gmail` already wired)
- IDLE / push notifications
- OAuth flow scaffolding (token refresh, browser launch)
