#!/usr/bin/env python3
"""
Carelink Token Status - Check access and refresh token validity
"""
import argparse
import json
import base64
import time
from datetime import datetime, timedelta
import os

def decode_jwt_payload(token):
    """Decode JWT token payload without verification"""
    try:
        # JWT has 3 parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode the payload (middle part)
        payload = parts[1]
        # Add padding if needed for base64 decoding
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded.decode('utf-8'))
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None

def format_timestamp(timestamp):
    """Format Unix timestamp to human readable"""
    try:
        dt = datetime.utcfromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return "Invalid timestamp"

def format_duration(seconds):
    """Format seconds to human readable duration"""
    if seconds < 0:
        return f"expired {abs(seconds)//3600}h {(abs(seconds)%3600)//60}m ago"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds%60}s"
    else:
        return f"{seconds}s"

def analyze_token_file(filename='logindata.json'):
    """Analyze token file and show status"""
    print("=" * 60)
    print(f"CARELINK TOKEN STATUS")
    print("=" * 60)

    if not os.path.isfile(filename):
        print(f"❌ Token file '{filename}' not found")
        return False

    try:
        with open(filename, 'r') as f:
            token_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading token file: {e}")
        return False

    print(f"📁 File: {filename}")
    print(f"📅 File modified: {datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d %H:%M:%S')}")

    # Check required fields
    required_fields = ["access_token", "refresh_token", "scope", "client_id"]
    missing_fields = []
    for field in required_fields:
        if field not in token_data:
            missing_fields.append(field)

    if missing_fields:
        print(f"❌ Missing required fields: {', '.join(missing_fields)}")
        return False

    current_time = time.time()

    print("\n" + "-" * 60)
    print("ACCESS TOKEN")
    print("-" * 60)

    access_token = token_data["access_token"]
    if access_token == "UNKNOWN":
        print("❌ Access token is UNKNOWN - need to re-extract tokens")
    else:
        # Try to decode JWT access token
        access_payload = decode_jwt_payload(access_token)
        if access_payload:
            if 'exp' in access_payload:
                exp_time = access_payload['exp']
                time_until_expiry = exp_time - current_time

                if time_until_expiry > 0:
                    print(f"✅ Valid for: {format_duration(int(time_until_expiry))}")
                    print(f"📅 Expires: {format_timestamp(exp_time)}")

                    if time_until_expiry < 600:  # Less than 10 minutes
                        print("⚠️  WARNING: Token expires soon - will be auto-refreshed")
                else:
                    print(f"❌ EXPIRED: {format_duration(int(time_until_expiry))}")
                    print(f"📅 Expired: {format_timestamp(exp_time)}")
            else:
                print("⚠️  No expiration info in token")

            # Show other token details
            if 'iat' in access_payload:
                print(f"🕐 Issued: {format_timestamp(access_payload['iat'])}")
            if 'aud' in access_payload:
                print(f"👥 Audience: {access_payload['aud']}")
            if 'iss' in access_payload:
                print(f"🏢 Issuer: {access_payload['iss']}")

        else:
            print("⚠️  Cannot decode access token (not JWT format)")
            print(f"📏 Length: {len(access_token)} characters")
            print(f"🔍 Preview: {access_token[:50]}...")

    print("\n" + "-" * 60)
    print("REFRESH TOKEN")
    print("-" * 60)

    refresh_token = token_data["refresh_token"]
    if refresh_token == "UNKNOWN":
        print("❌ Refresh token is UNKNOWN - need to re-extract tokens")
    else:
        # Try to decode JWT refresh token
        refresh_payload = decode_jwt_payload(refresh_token)
        if refresh_payload:
            if 'exp' in refresh_payload:
                exp_time = refresh_payload['exp']
                time_until_expiry = exp_time - current_time

                if time_until_expiry > 0:
                    print(f"✅ Valid for: {format_duration(int(time_until_expiry))}")
                    print(f"📅 Expires: {format_timestamp(exp_time)}")

                    days_left = time_until_expiry / 86400
                    if days_left < 7:
                        print("⚠️  WARNING: Refresh token expires in less than 7 days")
                else:
                    print(f"❌ EXPIRED: {format_duration(int(time_until_expiry))}")
                    print(f"📅 Expired: {format_timestamp(exp_time)}")
                    print("🔄 Need to re-authenticate")
            else:
                print("⚠️  No expiration info in refresh token")
        else:
            print("ℹ️  Refresh token (not JWT format)")
            print(f"📏 Length: {len(refresh_token)} characters")
            print(f"🔍 Preview: {refresh_token[:50]}...")

    print("\n" + "-" * 60)
    print("OTHER INFO")
    print("-" * 60)
    print(f"🆔 Client ID: {token_data.get('client_id', 'Unknown')}")
    print(f"🔐 Scope: {token_data.get('scope', 'Unknown')}")

    if 'mag-identifier' in token_data:
        print(f"🏷️  MAG Identifier: {token_data['mag-identifier'][:20]}...")

    # Show extraction method if available
    if '_extraction_method' in token_data:
        print(f"🛠️  Extracted via: {token_data['_extraction_method']}")

    if '_extraction_timestamp' in token_data:
        extract_time = datetime.fromtimestamp(token_data['_extraction_timestamp'])
        print(f"⏰ Extracted: {extract_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    # Check if client library will auto-refresh
    access_payload = decode_jwt_payload(access_token) if access_token != "UNKNOWN" else None
    if access_payload and 'exp' in access_payload:
        time_until_expiry = access_payload['exp'] - current_time
        if 0 < time_until_expiry < 600:
            print("🔄 carelink_client2.py will automatically refresh this token on next API call")
        elif time_until_expiry <= 0:
            print("🔄 carelink_client2.py will refresh this expired token on next API call")
        else:
            print("✅ Token is valid - no immediate action needed")

    if refresh_token == "UNKNOWN" or access_token == "UNKNOWN":
        print("❗ Re-run the token extraction process to get valid tokens")

    return True

def test_token_refresh(filename='logindata.json'):
    """Test if token refresh works with current tokens"""
    print("\n" + "=" * 60)
    print("TESTING TOKEN REFRESH")
    print("=" * 60)

    try:
        # Import and test the client
        import sys
        import os
        # Add current directory to path to import carelink_client2
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from carelink_client2 import CareLinkClient

        print("🧪 Testing CareLinkClient initialization...")
        client = CareLinkClient(filename)

        print("🔄 Testing data retrieval (will trigger refresh if needed)...")
        data = client.getRecentData()

        if data:
            print("✅ SUCCESS: Token refresh working properly")
            print(f"📊 Retrieved data for: {len(data)} recent entries")
        else:
            print("❌ FAILED: Unable to retrieve data (check tokens)")

    except ImportError:
        print("⚠️  Cannot test - carelink_client2.py not found in current directory")
    except Exception as e:
        print(f"❌ Error during test: {e}")

def main():
    parser = argparse.ArgumentParser(description='Check Carelink token status')
    parser.add_argument('--file', default='logindata.json', help='Token file path')
    parser.add_argument('--test-refresh', action='store_true', help='Test token refresh functionality')
    args = parser.parse_args()

    if analyze_token_file(args.file):
        if args.test_refresh:
            test_token_refresh(args.file)

if __name__ == "__main__":
    main()