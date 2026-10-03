#!/usr/bin/env python3
"""GlookoXT POC — fetch historical diabetes data and pump settings.

Usage:
  python glookoxt/glookoxt_poc.py login              # interactive email-code login
  python glookoxt/glookoxt_poc.py fetch [--days 14]   # fetch data with saved token
  python glookoxt/glookoxt_poc.py status              # show token validity
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv

from glookoxt_client import AuthError, GlookoXtAuth, GlookoXtData

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

TOKEN_PATH = Path(__file__).parent / "logindata.json"
DATA_DIR = Path(__file__).parent.parent / "data"


def cmd_login(args):
    auth = GlookoXtAuth(TOKEN_PATH)

    email = os.environ.get("GLOOKOXT_EMAIL") or input("Email: ").strip()
    password = os.environ.get("GLOOKOXT_PASSWORD") or getpass("Password: ")
    print(f"Using email: {email}")

    print("Requesting email code...")
    try:
        result = auth.request_code(email, password)
        print(f"Code sent. Server response: {result}")
    except AuthError as e:
        print(f"Login failed: {e}", file=sys.stderr)
        return 1

    code = input("Enter the code from your email: ").strip()

    print("Redeeming code...")
    try:
        result = auth.redeem_code(email, code)
        print(f"Login successful. Role: {result.get('role', 'unknown')}")
    except AuthError as e:
        print(f"Code redemption failed: {e}", file=sys.stderr)
        return 1

    auth.save_token()
    expiry = auth.token_expiry()
    print(f"Token saved to {TOKEN_PATH}")
    if expiry:
        print(f"Token expires: {expiry.strftime('%Y-%m-%d %H:%M UTC')}")
    return 0


def cmd_status(args):
    auth = GlookoXtAuth(TOKEN_PATH)
    try:
        data = auth.load_token()
    except (AuthError, KeyError) as e:
        print(f"Cannot load token: {e}", file=sys.stderr)
        return 1

    print(f"Token file: {TOKEN_PATH}")
    print(f"Saved at: {data.get('saved_at', 'unknown')}")
    expiry = auth.token_expiry()
    if expiry:
        remaining = expiry - datetime.now(timezone.utc)
        print(f"Expires: {expiry.strftime('%Y-%m-%d %H:%M UTC')} ({remaining.days} days remaining)")
    else:
        print("Expires: unknown (no exp claim)")
    print(f"Valid: {'yes' if auth.is_token_valid() else 'NO — re-login required'}")
    return 0


def cmd_fetch(args):
    auth = GlookoXtAuth(TOKEN_PATH)
    try:
        auth.load_token()
    except (AuthError, KeyError) as e:
        print(f"Cannot load token: {e}. Run 'login' first.", file=sys.stderr)
        return 1

    if not auth.is_token_valid():
        print("Token expired. Run 'login' to re-authenticate.", file=sys.stderr)
        return 1

    return asyncio.run(_fetch_data(auth.token, args.days, debug=args.debug))


async def _fetch_data(token, days, debug=False):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    client = GlookoXtData()
    try:
        print("Connecting to GlookoXT...")
        await client.connect(token, debug=debug)
        print("Connected.")

        print("Fetching user profile...")
        profile = await client.get_user_data()
        print(f"  Profile: {json.dumps(profile, indent=2)}")

        print(f"Fetching collected data ({days} days)...")
        records = await client.get_collected_data(start, end)
        print(f"  Retrieved {len(records)} records.")

        print(f"Fetching export data ({days} days)...")
        export_csv = await client.get_export(start, end)
        print(f"  Export size: {len(export_csv)} chars.")

    except Exception as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        raise
    finally:
        await client.disconnect()
        print("Disconnected.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data_file = DATA_DIR / f"glookoxt_data_{timestamp}.json"
    data_file.write_text(json.dumps({
        "profile": profile,
        "records": records,
        "fetch_info": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
            "record_count": len(records),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    }, indent=2, default=str))
    print(f"Data saved to {data_file}")

    if export_csv.strip():
        export_file = DATA_DIR / f"glookoxt_export_{timestamp}.csv"
        export_file.write_text(export_csv)
        print(f"Export saved to {export_file}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="GlookoXT POC")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("login", help="Interactive email-code login")
    sub.add_parser("status", help="Show token status")

    fetch_parser = sub.add_parser("fetch", help="Fetch historical data")
    fetch_parser.add_argument("--days", type=int, default=14, help="Days of history (default: 14)")
    fetch_parser.add_argument("--debug", action="store_true", help="Enable Socket.IO debug logging")

    args = parser.parse_args()

    if args.command == "login":
        sys.exit(cmd_login(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    elif args.command == "fetch":
        sys.exit(cmd_fetch(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
