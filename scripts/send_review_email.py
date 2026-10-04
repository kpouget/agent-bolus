#!/usr/bin/env python3
"""
Check if the latest bolus review report has been emailed.
If not, send index.html as an HTML email via sendmail and touch .email_sent marker.

Requires EMAIL_TO and EMAIL_FROM in .env (EMAIL_TO is comma-separated for multiple recipients).
"""
import re
import subprocess
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv
import os

GEN_ROOT = Path(__file__).parent.parent / "generated"


def find_latest_generated_dir():
    if not GEN_ROOT.exists():
        return None
    dirs = sorted(
        [d for d in GEN_ROOT.iterdir() if d.is_dir() and re.match(r"\d{6}_\d{4}$", d.name)],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def main():
    load_dotenv(Path(__file__).parent.parent / ".env")

    email_to = os.getenv("EMAIL_TO")
    email_from = os.getenv("EMAIL_FROM")
    if not email_to or not email_from:
        print("EMAIL_TO and EMAIL_FROM must be set in .env", file=sys.stderr)
        sys.exit(1)

    recipients = [a.strip() for a in email_to.split(",")]

    gen_dir = find_latest_generated_dir()
    if gen_dir is None:
        print("No generated report found", file=sys.stderr)
        sys.exit(1)

    marker = gen_dir / ".email_sent"
    if marker.exists():
        sys.exit(0)

    index_html = gen_dir / "index.html"
    if not index_html.exists():
        print(f"No index.html in {gen_dir.name}", file=sys.stderr)
        sys.exit(1)

    html_body = index_html.read_text()
    html_body = re.sub(r'<a\s+href="[^"]*\.html"', '<a href="#"', html_body)

    msg = MIMEMultipart("alternative")
    msg["From"] = email_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Analyse I:C — {gen_dir.name}"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    result = subprocess.run(
        ["/usr/sbin/sendmail", "-t"],
        input=msg.as_string(),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"sendmail failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    marker.touch()
    print(f"Sent to {', '.join(recipients)} ({gen_dir.name})")


if __name__ == "__main__":
    main()
