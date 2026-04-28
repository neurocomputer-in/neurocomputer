"""Demo: send a self-test email and read it back.

Skipped (not failed) when EMAIL_ADDR / EMAIL_APP_PASSWORD are unset, mirroring
the pattern in examples/research_flow.py.

Configure (Gmail example):
    export EMAIL_ADDR="you@gmail.com"
    export EMAIL_APP_PASSWORD="abcd efgh ijkl mnop"   # Gmail app password
    # hosts auto-detect for @gmail.com / @outlook.com / @yahoo.com

Run:
    python examples/email_demo.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, "/home/ubuntu/neurolang")

import neurolang  # noqa: F401 — registers stdlib
from neurolang.stdlib import email


def main() -> int:
    if not os.getenv("EMAIL_ADDR") or not os.getenv("EMAIL_APP_PASSWORD"):
        print("[skip] set EMAIL_ADDR + EMAIL_APP_PASSWORD to run the live demo")
        return 0

    addr = os.environ["EMAIL_ADDR"]
    subject = f"NeuroLang self-test {int(time.time())}"

    print(f"-> sending self-test to {addr} ...")
    sent = email.send(
        addr,
        subject,
        "Hello from NeuroLang's email_neuros stdlib.\n\nThis is a self-test.",
    )
    print(f"   {sent}")

    print("-> waiting 5s for IMAP delivery, then reading INBOX ...")
    time.sleep(5)
    msgs = email.read(n=5)
    print(f"   got {len(msgs)} message(s)")
    for m in msgs:
        marker = " <-- self-test" if m["subject"] == subject else ""
        print(f"   [{m['uid']}] {m['from']} | {m['subject']}{marker}")

    matches = [m for m in msgs if m["subject"] == subject]
    if matches:
        print(f"-> success: located self-test by subject")
        print(f"-> marking as seen ...")
        email.mark(matches[0]["uid"], "seen")
        print("   done")
    else:
        print("-> note: self-test not found in last 5 — may still be in transit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
