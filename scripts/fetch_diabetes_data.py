#!/usr/bin/env python3
"""
Automated diabetes data fetching from Carelink
Runs at 6am and 6pm to fetch fresh CSV data (last 7 days)
"""
import os
import sys
import json
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add nooa to path
sys.path.append(str(Path(__file__).parent.parent / "nooa"))

def load_status():
    """Load the fetch status metadata."""
    status_file = Path("fetch_status.json")
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {
        "last_fetch_timestamp": None,
        "last_fetch_success": False,
        "token_created_timestamp": None,
        "token_expires_timestamp": None,
        "total_fetches": 0,
        "last_error": None
    }

def save_status(status):
    """Save the fetch status metadata."""
    status_file = Path("fetch_status.json")
    status["last_update"] = datetime.now().isoformat()

    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def check_token_expiry(status):
    """Check if token is expired or will expire soon."""
    if not status.get("token_expires_timestamp"):
        return True, "No token expiry information"

    try:
        expires_at = datetime.fromisoformat(status["token_expires_timestamp"])
        now = datetime.now()

        if expires_at <= now:
            return True, f"Token expired at {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

        # Warn if expires within 24 hours
        time_left = expires_at - now
        if time_left.total_seconds() < 86400:  # 24 hours
            hours_left = time_left.total_seconds() / 3600
            return False, f"Token expires in {hours_left:.1f} hours at {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

        return False, f"Token valid until {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

    except Exception as e:
        return True, f"Error checking token: {e}"

def cleanup_old_csv_files(data_dir, keep_latest=1):
    """Remove old CSV files, keeping only the most recent ones."""
    csv_files = list(data_dir.glob("csv_report_*.csv"))

    if len(csv_files) <= keep_latest:
        return

    # Sort by modification time, newest first
    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # Remove old files
    for old_file in csv_files[keep_latest:]:
        print(f"🧹 Removing old data file: {old_file.name}")
        old_file.unlink()

    print(f"   ✅ Kept {keep_latest} most recent CSV file(s)")

def update_token_info(status):
    """Update token creation/expiry information from environment."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Check if we have token info in env
        access_key = os.getenv('ACCESS_KEY')
        if access_key:
            # For now, assume token was just created (you'd replace this with actual token inspection)
            now = datetime.now()
            status["token_created_timestamp"] = now.isoformat()
            status["token_expires_timestamp"] = (now + timedelta(days=7)).isoformat()
            return True, "Token info updated from environment"
        else:
            return False, "No ACCESS_KEY found in environment"

    except Exception as e:
        return False, f"Error updating token info: {e}"

async def fetch_data():
    """Fetch fresh diabetes data from Carelink."""
    print(f"🔄 Starting diabetes data fetch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load current status
    status = load_status()
    print(f"📊 Last successful fetch: {status.get('last_fetch_timestamp', 'Never')}")
    print(f"📊 Total fetches: {status.get('total_fetches', 0)}")

    # Check token status
    token_expired, token_msg = check_token_expiry(status)
    print(f"🔑 Token status: {token_msg}")

    if token_expired:
        print("⚠️  Token expired or missing - attempting to update from environment")
        updated, update_msg = update_token_info(status)
        if not updated:
            error_msg = f"Token expired and could not update: {update_msg}"
            status["last_error"] = error_msg
            save_status(status)
            print(f"❌ {error_msg}")
            return False
        print(f"✅ {update_msg}")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Change to parent directory to access mcp_servers
        parent_dir = Path(__file__).parent.parent
        os.chdir(parent_dir)

        # Import MCP server functions for data fetching
        sys.path.append('carelink_mcp')
        from carelink_mcp_server import download_csv_data

        print(f"📥 Fetching fresh data from Carelink (last 7 days)...")

        # Fetch new CSV data (last 7 days)
        csv_content = await download_csv_data(days=7)

        if not csv_content:
            error_msg = "Failed to fetch data from Carelink - no content returned"
            status["last_error"] = error_msg
            save_status(status)
            print(f"❌ {error_msg}")
            return False

        # Create data directory if needed
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_file = data_dir / f"csv_report_7days-{timestamp}.csv"

        # Save new data
        with open(new_file, 'w') as f:
            f.write(csv_content)

        print(f"📁 New data saved: {new_file}")

        # Cleanup old CSV files after successful fetch
        cleanup_old_csv_files(data_dir, keep_latest=1)

        # Update status
        status["last_fetch_timestamp"] = datetime.now().isoformat()
        status["last_fetch_success"] = True
        status["total_fetches"] = status.get("total_fetches", 0) + 1
        status["last_error"] = None
        status["latest_data_file"] = str(new_file)

        save_status(status)
        print(f"📊 Status updated - Total fetches: {status['total_fetches']}")
        print(f"✅ Data fetch successful!")
        return True

    except Exception as e:
        error_msg = f"Error during data fetch: {str(e)}"
        status["last_error"] = error_msg
        status["last_fetch_success"] = False
        save_status(status)
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    # Load status to show current state
    status = load_status()

    if "--status" in sys.argv or "-s" in sys.argv:
        print(f"📊 Diabetes Data Fetch Status")
        print(f"=" * 40)
        print(f"Last fetch: {status.get('last_fetch_timestamp', 'Never')}")
        print(f"Last success: {status.get('last_fetch_success', False)}")
        print(f"Total fetches: {status.get('total_fetches', 0)}")

        token_expired, token_msg = check_token_expiry(status)
        print(f"Token status: {token_msg}")

        if status.get('latest_data_file'):
            print(f"Latest data file: {status['latest_data_file']}")

        if status.get('last_error'):
            print(f"Last error: {status['last_error']}")

        return

    # Run the data fetch
    try:
        success = asyncio.run(fetch_data())
        if success:
            print(f"🎉 Data fetch completed successfully")
            sys.exit(0)
        else:
            print(f"❌ Data fetch failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Data fetch interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
