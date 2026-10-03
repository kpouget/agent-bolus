#!/usr/bin/env python3
"""
Fetch last 14 days of diabetes data from GlookoXT.
Designed to run via systemd timer.
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "glookoxt"))

from glookoxt_client import AuthError, GlookoXtAuth, GlookoXtData

PROJECT_DIR = Path(__file__).parent.parent
TOKEN_PATH = PROJECT_DIR / "glookoxt" / "logindata.json"
DATA_DIR = PROJECT_DIR / "data"
STATUS_FILE = DATA_DIR / "glookoxt_fetch_status.json"
FETCH_DAYS = 14


def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {
        "last_fetch_timestamp": None,
        "last_fetch_success": False,
        "total_fetches": 0,
        "last_error": None,
    }


def save_status(status):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    status["last_update"] = datetime.now(timezone.utc).isoformat()
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def cleanup_old_files(pattern, keep=1):
    files = sorted(DATA_DIR.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        print(f"  Removing old file: {old.name}")
        old.unlink()


async def fetch_data():
    auth = GlookoXtAuth(TOKEN_PATH)
    try:
        auth.load_token()
    except (AuthError, KeyError, FileNotFoundError) as e:
        return False, f"Cannot load token: {e}. Run glookoxt_poc.py login first."

    if not auth.is_token_valid():
        expiry = auth.token_expiry()
        return False, f"Token expired ({expiry}). Run glookoxt_poc.py login to re-authenticate."

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=FETCH_DAYS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    client = GlookoXtData()
    try:
        print("Connecting to GlookoXT...")
        await client.connect(auth.token)

        print("Fetching user profile...")
        profile = await client.get_user_data()

        print(f"Fetching collected data ({FETCH_DAYS} days)...")
        records = await client.get_collected_data(start, end)
        print(f"  {len(records)} records retrieved.")

        print(f"Fetching export data ({FETCH_DAYS} days)...")
        export_csv = await client.get_export(start, end)
        print(f"  Export: {len(export_csv)} chars.")

    except Exception as e:
        return False, f"Fetch error: {e}"
    finally:
        await client.disconnect()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data_file = DATA_DIR / f"glookoxt_data_{timestamp}.json"
    data_file.write_text(json.dumps({
        "profile": profile,
        "records": records,
        "fetch_info": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": FETCH_DAYS,
            "record_count": len(records),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    }, indent=2, default=str))
    print(f"Data saved to {data_file}")

    if export_csv.strip():
        export_file = DATA_DIR / f"glookoxt_export_{timestamp}.csv"
        export_file.write_text(export_csv)
        print(f"Export saved to {export_file}")

    cleanup_old_files("glookoxt_data_*.json", keep=1)
    cleanup_old_files("glookoxt_export_*.csv", keep=1)

    return True, {
        "data_file": str(data_file),
        "record_count": len(records),
    }


def main():
    if "--status" in sys.argv or "-s" in sys.argv:
        status = load_status()
        print("GlookoXT Fetch Status")
        print(f"  Last fetch: {status.get('last_fetch_timestamp', 'Never')}")
        print(f"  Success: {status.get('last_fetch_success', False)}")
        print(f"  Total fetches: {status.get('total_fetches', 0)}")
        if status.get("last_error"):
            print(f"  Last error: {status['last_error']}")
        if status.get("latest_data_file"):
            print(f"  Latest file: {status['latest_data_file']}")
        return

    status = load_status()
    print(f"GlookoXT data fetch starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success, result = asyncio.run(fetch_data())

    if success:
        status["last_fetch_timestamp"] = datetime.now(timezone.utc).isoformat()
        status["last_fetch_success"] = True
        status["total_fetches"] = status.get("total_fetches", 0) + 1
        status["last_error"] = None
        status["latest_data_file"] = result["data_file"]
        save_status(status)
        print(f"Fetch complete. {result['record_count']} records saved.")
    else:
        status["last_fetch_success"] = False
        status["last_error"] = result
        save_status(status)
        print(f"Fetch failed: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
