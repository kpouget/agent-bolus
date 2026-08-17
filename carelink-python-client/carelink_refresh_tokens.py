#!/usr/bin/env python3
"""
Carelink Token Refresh - Manually refresh access tokens using refresh token
"""
import argparse
import json
import requests
import time
from datetime import datetime


def resolve_endpoint_config(discovery_url, is_us_region=False):
    """Get token endpoint from discovery service"""
    discover_resp = json.loads(requests.get(discovery_url).text)
    sso_url = None
    is_auth0 = False

    for c in discover_resp["CP"]:
        if c['region'].lower() == "us" and is_us_region:
            key = c['UseSSOConfiguration']
            sso_url = c[key]
            if "Auth0" in key:
                is_auth0 = True
        elif c['region'].lower() == "eu" and not is_us_region:
            key = c['UseSSOConfiguration']
            sso_url = c[key]
            if "Auth0" in key:
                is_auth0 = True

    if sso_url is None:
        raise Exception("Could not get SSO config url")

    sso_config = json.loads(requests.get(sso_url).text)

    if is_auth0:
        api_base_url = f"https://{sso_config['server']['hostname']}:{sso_config['server']['port']}/{sso_config['server']['prefix']}"
        if api_base_url.endswith('/'):
            api_base_url = api_base_url[:-1]
        token_url = api_base_url + sso_config["system_endpoints"]["token_endpoint_path"]
    else:
        # Handle non-auth0 case
        api_base_url = f"https://{sso_config['server']['hostname']}:{sso_config['server']['port']}/{sso_config['server']['prefix']}"
        if api_base_url.endswith('/'):
            api_base_url = api_base_url[:-1]
        token_url = api_base_url + sso_config["oauth"]["system_endpoints"]["token_endpoint_path"]

    return token_url, is_auth0


def refresh_tokens(filename='logindata.json', is_us_region=False):
    """Refresh access token using refresh token"""

    print("🔄 Carelink Token Refresh")
    print("=" * 50)

    # Read current token data
    try:
        with open(filename, 'r') as f:
            token_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading token file: {e}")
        return False

    # Check required fields
    required_fields = ["refresh_token", "client_id"]
    for field in required_fields:
        if field not in token_data or token_data[field] == "UNKNOWN":
            print(f"❌ Missing or invalid {field}")
            return False

    print(f"📁 Token file: {filename}")
    print(f"🆔 Client ID: {token_data['client_id']}")

    # Get token endpoint
    discovery_url = 'https://clcloud.minimed.eu/connect/carepartner/v13/discover/android/3.6'

    try:
        print("🔍 Discovering token endpoint...")
        token_url, is_auth0 = resolve_endpoint_config(discovery_url, is_us_region)
        print(f"🌐 Token URL: {token_url}")
        print(f"🔐 Auth method: {'Auth0' if is_auth0 else 'Standard OAuth'}")
    except Exception as e:
        print(f"❌ Error getting token endpoint: {e}")
        return False

    # Prepare refresh request
    refresh_data = {
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": token_data["client_id"]
    }

    # Add client_secret if available
    if "client_secret" in token_data and token_data["client_secret"] != "UNKNOWN":
        refresh_data["client_secret"] = token_data["client_secret"]

    headers = {}
    if "mag-identifier" in token_data and token_data["mag-identifier"] != "UNKNOWN":
        headers["mag-identifier"] = token_data["mag-identifier"]

    print("🔄 Refreshing tokens...")

    try:
        response = requests.post(token_url, data=refresh_data, headers=headers)
        print(f"📊 Response status: {response.status_code}")

        if response.status_code == 200:
            new_tokens = response.json()

            # Update token data
            old_access_token = token_data.get("access_token", "")[:20]

            token_data["access_token"] = new_tokens["access_token"]
            if "refresh_token" in new_tokens:
                token_data["refresh_token"] = new_tokens["refresh_token"]

            # Add refresh metadata
            token_data["_last_refresh"] = time.time()
            token_data["_refresh_count"] = token_data.get("_refresh_count", 0) + 1

            # Save updated tokens
            with open(filename, 'w') as f:
                json.dump(token_data, f, indent=4)

            print("✅ SUCCESS: Tokens refreshed!")
            print(f"🔑 Old access token: {old_access_token}...")
            print(f"🔑 New access token: {token_data['access_token'][:20]}...")
            print(f"📊 Refresh count: {token_data['_refresh_count']}")
            print(f"⏰ Last refresh: {datetime.fromtimestamp(token_data['_last_refresh']).strftime('%Y-%m-%d %H:%M:%S')}")

            return True

        else:
            print(f"❌ Refresh failed: {response.status_code}")
            print(f"📄 Response: {response.text}")

            if response.status_code == 400:
                print("💡 This usually means:")
                print("   - Refresh token has expired")
                print("   - Invalid client credentials")
                print("   - Need to re-authenticate")

            return False

    except Exception as e:
        print(f"❌ Error during refresh: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Manually refresh Carelink access tokens')
    parser.add_argument('--file', default='logindata.json', help='Token file path')
    parser.add_argument('--us', action='store_true', help='Use US region')
    args = parser.parse_args()

    success = refresh_tokens(args.file, args.us)

    if success:
        print("\n🎉 Token refresh completed successfully!")
        print("💡 You can now use the updated tokens for API calls")
    else:
        print("\n💔 Token refresh failed")
        print("💡 You may need to re-authenticate using the console method")


if __name__ == "__main__":
    main()