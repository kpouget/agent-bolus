#!/usr/bin/env python3
"""
Automated diabetes data fetching from Carelink
Runs at 6am and 6pm to fetch fresh CSV data (last 7 days)
"""
import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add nooa to path
sys.path.append(str(Path(__file__).parent.parent / "nooa"))
sys.path.append(str(Path(__file__).parent.parent / "carelink-python-client"))

def load_status():
    """Load the fetch status metadata."""
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    status_file = data_dir / "fetch_status.json"
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
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    status_file = data_dir / "fetch_status.json"
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

def generate_html_report(status, new_file, result):
    """Generate HTML report about the data fetch."""
    try:
        # Create generated directory if needed
        generated_dir = Path("generated")
        generated_dir.mkdir(exist_ok=True)

        # Calculate token expiration info
        token_expires_at = "Unknown"
        token_expires_str = "Unknown"
        token_status_class = ""

        if status.get("token_expires_timestamp"):
            try:
                token_expires = datetime.fromisoformat(status["token_expires_timestamp"])
                now = datetime.now()
                time_until_expiry = token_expires - now

                # Format expiration date
                token_expires_at = token_expires.strftime("%Y-%m-%d at %H:%M:%S")

                # Calculate time remaining
                if time_until_expiry.total_seconds() > 0:
                    expire_days = time_until_expiry.days
                    expire_hours = time_until_expiry.seconds // 3600

                    if expire_days > 1:
                        token_expires_str = f"in {expire_days} days, {expire_hours} hours"
                        token_status_class = "status-success"
                    elif expire_days == 1:
                        token_expires_str = f"in 1 day, {expire_hours} hours"
                        token_status_class = "token-warning"
                    elif expire_hours > 1:
                        token_expires_str = f"in {expire_hours} hours"
                        token_status_class = "token-warning"
                    else:
                        token_expires_str = f"in {time_until_expiry.seconds // 60} minutes"
                        token_status_class = "status-error"
                else:
                    expire_days = -time_until_expiry.days
                    token_expires_str = f"EXPIRED {expire_days} days ago"
                    token_status_class = "status-error"

            except Exception:
                pass

        # Get file info
        file_size_mb = result.get("file_size", 0) / 1024  # Convert to KB
        last_fetch_time = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diabetes Data Fetch Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #007acc;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .status-success {{
            color: #28a745;
            font-size: 18px;
            font-weight: 600;
        }}
        .status-error {{
            color: #dc3545;
            font-size: 18px;
            font-weight: 600;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .info-item {{
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #007acc;
        }}
        .label {{
            font-weight: 600;
            color: #555;
            margin-bottom: 4px;
        }}
        .value {{
            font-size: 16px;
            color: #333;
        }}
        .token-warning {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 12px;
            border-radius: 6px;
            margin: 16px 0;
        }}
        .status-success.value {{
            color: #28a745;
            font-weight: 600;
        }}
        .status-error.value {{
            color: #dc3545;
            font-weight: 600;
        }}
        .token-warning.value {{
            color: #856404;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 24px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>🩺 Diabetes Data Fetch Report</h1>
            <div class="status-success">✅ Data Successfully Fetched</div>
        </div>

        <div class="info-grid">
            <div class="info-item">
                <div class="label">📅 Last Fetch</div>
                <div class="value">{last_fetch_time}</div>
            </div>

            <div class="info-item">
                <div class="label">📁 Data File</div>
                <div class="value">{new_file.name}</div>
            </div>

            <div class="info-item">
                <div class="label">📊 File Size</div>
                <div class="value">{file_size_mb:.1f} KB ({result.get('file_size', 0):,} chars)</div>
            </div>

            <div class="info-item">
                <div class="label">📄 Data Lines</div>
                <div class="value">{result.get('line_count', 0):,} lines</div>
            </div>

            <div class="info-item">
                <div class="label">📈 Days Requested</div>
                <div class="value">{result.get('days_requested', 7)} days</div>
            </div>

            <div class="info-item">
                <div class="label">🔢 Total Fetches</div>
                <div class="value">{status.get('total_fetches', 0)}</div>
            </div>
        </div>

        <div class="card" style="margin-top: 20px;">
            <h3>🔑 Token Information</h3>
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">📅 Token Expires At</div>
                    <div class="value">{token_expires_at}</div>
                </div>

                <div class="info-item">
                    <div class="label">⏳ Time Remaining</div>
                    <div class="value {token_status_class}">{token_expires_str}</div>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated by diabetes-fetch script • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

        # Save HTML report
        report_file = generated_dir / "data_update.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"📄 HTML report generated: {report_file}")
        return True

    except Exception as e:
        print(f"⚠️  Failed to generate HTML report: {e}")
        return False

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

def fetch_data():
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

        # Import MCP server for data fetching
        sys.path.append('carelink_mcp')
        from carelink_mcp_server import CarelinkMcpServer

        print(f"📥 Fetching fresh data from Carelink (last 7 days)...")

        # Create MCP server instance and download CSV data
        server = CarelinkMcpServer()
        result = server.download_csv_data(days=7)

        if not result.get("success"):
            error_msg = f"Failed to fetch data from Carelink: {result.get('error', 'Unknown error')}"
            status["last_error"] = error_msg
            save_status(status)
            print(f"❌ {error_msg}")
            return False

        # Get the file path from the result
        downloaded_file = Path(result["file_path"])

        if not downloaded_file.exists():
            error_msg = f"Downloaded file not found: {downloaded_file}"
            status["last_error"] = error_msg
            save_status(status)
            print(f"❌ {error_msg}")
            return False

        print(f"📁 Data fetched and saved: {downloaded_file}")
        print(f"   📊 Size: {result['file_size']} characters")
        print(f"   📄 Lines: {result['line_count']}")

        # Use the downloaded file as our new data file
        new_file = downloaded_file

        # Cleanup old CSV files after successful fetch
        data_dir = new_file.parent
        cleanup_old_csv_files(data_dir, keep_latest=1)

        # Update status first
        status["last_fetch_timestamp"] = datetime.now().isoformat()
        status["last_fetch_success"] = True
        status["total_fetches"] = status.get("total_fetches", 0) + 1
        status["last_error"] = None
        status["latest_data_file"] = str(new_file)

        # Generate HTML report
        generate_html_report(status, new_file, result)

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
        success = fetch_data()
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
