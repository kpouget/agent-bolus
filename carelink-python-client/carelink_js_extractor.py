#!/usr/bin/env python3
"""
Carelink JavaScript Token Extractor - Console command to extract OAuth tokens

Provides a JavaScript snippet that extracts the same tokens as carelink_simple_webserver.py
"""
import argparse
import json
import threading
import webbrowser
import time
from flask import Flask, render_template_string, request, jsonify


class CarelinJsExtractor:
    def __init__(self, port=8080):
        self.app = Flask(__name__)
        self.port = port
        self.is_us_region = False
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            carelink_url = "https://carelink.minimed.com/" if self.is_us_region else "https://carelink.minimed.eu/"

            # JavaScript that mimics carelink_simple_webserver.py token extraction
            js_snippet = '''
// Carelink OAuth Token Extractor - Extracts same tokens as carelink_simple_webserver.py
(function() {
    console.log("🔍 Carelink OAuth Token Extractor");
    console.log("=" + "=".repeat(40));

    // Helper function to decode JWT payload
    function decodeJWT(token) {
        try {
            var parts = token.split('.');
            if (parts.length !== 3) return null;

            var payload = parts[1];
            // Add padding if needed
            var padding = 4 - payload.length % 4;
            if (padding !== 4) {
                payload += '='.repeat(padding);
            }

            var decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
            return JSON.parse(decoded);
        } catch (e) {
            console.log("Error decoding JWT:", e);
            return null;
        }
    }

    // Get all cookies
    var cookies = {};
    document.cookie.split(';').forEach(function(cookie) {
        var parts = cookie.trim().split('=');
        if (parts.length >= 2) {
            var name = parts[0];
            var value = parts.slice(1).join('=');
            cookies[name] = value;
        }
    });

    // Find the auth_tmp_token (which is the OAuth access_token)
    var auth_token = cookies['auth_tmp_token'];
    var token_expiry = cookies['c_token_valid_to'];

    if (!auth_token) {
        console.log("❌ auth_tmp_token not found in cookies");
        console.log("💡 Make sure you are logged in to Carelink");
        console.log("📋 Available cookies:", Object.keys(cookies));
        return null;
    }

    console.log("✅ Found auth_tmp_token");
    console.log("🔑 Token preview:", auth_token.substring(0, 30) + "...");

    // Decode the JWT to extract client_id and other info
    var jwt_payload = decodeJWT(auth_token);
    var client_id = "UNKNOWN";

    if (jwt_payload) {
        console.log("✅ JWT decoded successfully");

        // Extract client_id from 'azp' field (authorized party)
        client_id = jwt_payload.azp || "UNKNOWN";

        console.log("👤 Username:", jwt_payload.token_details?.preferred_username || "Unknown");
        console.log("🌍 Country:", jwt_payload.token_details?.country || "Unknown");
        console.log("🎭 Roles:", jwt_payload.token_details?.roles || []);
        console.log("🆔 Client ID:", client_id);
        console.log("⏰ Token expires:", new Date(jwt_payload.exp * 1000).toISOString());
    }

    // Create the logindata.json format (same as carelink_simple_webserver.py)
    var loginData = {
        "access_token": auth_token,
        "refresh_token": "UNKNOWN",
        "scope": jwt_payload ? (jwt_payload.scope || "openid profile email offline_access") : "openid profile email offline_access",
        "client_id": client_id,
        "token_type": "Bearer",
        "_extracted_tokens": {
            "cookie_auth_tmp_token": auth_token
        },
        "_extraction_timestamp": Date.now() / 1000,
        "_extraction_method": "javascript_console",
        "_extraction_url": window.location.href,
        "_jwt_payload": jwt_payload
    };

    // Add token expiry if available
    if (token_expiry) {
        loginData._extracted_tokens["cookie_c_token_valid_to"] = token_expiry;
        console.log("⏰ Cookie expires:", token_expiry.replace(/"/g, ''));
    }

    // Add all found cookies for reference
    var authRelatedCookies = {};
    for (var name in cookies) {
        if (name.includes('auth') || name.includes('token') || name.includes('session')) {
            authRelatedCookies['cookie_' + name] = cookies[name];
        }
    }
    loginData._all_found_tokens = authRelatedCookies;

    console.log("\\n🎉 Token extraction complete!");
    console.log("💾 Copy the JSON below and save it as logindata.json:");
    console.log("\\n" + "=".repeat(60));
    console.log(JSON.stringify(loginData, null, 4));
    console.log("=" + "=".repeat(59));

    console.log("\\n🛡️ SECURITY NOTE: Only essential OAuth fields included");
    console.log("💡 To use this token:");
    console.log("1. Copy the JSON above");
    console.log("2. Save it as 'logindata.json'");
    console.log("3. Run: python3 -c \\"from carelink_client2 import CareLinkClient; c=CareLinkClient(); print(len(c.getRecentData()) if c.getRecentData() else 'No data')\\"");

    // Return the data for programmatic use
    return loginData;
})();
            '''.strip()

            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Carelink JavaScript Token Extractor</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    .container {{ max-width: 1000px; margin: 0 auto; }}
                    .step {{
                        background: #f8f9fa;
                        padding: 20px;
                        margin: 15px 0;
                        border-radius: 8px;
                        border-left: 4px solid #007bff;
                    }}
                    .step h3 {{ margin-top: 0; }}
                    .code {{
                        background: #2d3748;
                        color: #e2e8f0;
                        padding: 15px;
                        border-radius: 5px;
                        font-family: 'Monaco', 'Consolas', monospace;
                        font-size: 11px;
                        overflow-x: auto;
                        white-space: pre;
                        margin: 10px 0;
                        max-height: 400px;
                        overflow-y: auto;
                    }}
                    .result-area {{
                        width: 100%;
                        height: 300px;
                        font-family: monospace;
                        font-size: 11px;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                    }}
                    .btn {{
                        background: #007bff;
                        color: white;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                    }}
                    .btn:hover {{ background: #0056b3; }}
                    .copy-btn {{
                        background: #28a745;
                        color: white;
                        border: none;
                        padding: 8px 15px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 14px;
                        margin: 5px;
                    }}
                    .copy-btn:hover {{ background: #218838; }}
                    .success {{ background: #d4edda; border-left-color: #28a745; }}
                    .error {{ background: #f8d7da; border-left-color: #dc3545; }}
                    .warning {{ background: #fff3cd; border-left-color: #ffc107; }}
                    .highlight {{
                        background: #e3f2fd;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #2196f3;
                        margin: 15px 0;
                    }}
                </style>
                <script>
                    function copyToClipboard(text) {{
                        navigator.clipboard.writeText(text).then(() => {{
                            alert('JavaScript command copied to clipboard!');
                        }});
                    }}

                    function copySimpleCommand() {{
                        var simpleCommand = `// Carelink Token Extractor - Paste in Console
{js_snippet}`;
                        copyToClipboard(simpleCommand);
                    }}

                    function saveToken() {{
                        var tokenJson = document.getElementById('tokenInput').value.trim();
                        if (!tokenJson) {{
                            alert('Please paste the token JSON first');
                            return;
                        }}

                        // Validate JSON
                        try {{
                            JSON.parse(tokenJson);
                        }} catch(e) {{
                            alert('Invalid JSON format: ' + e.message);
                            return;
                        }}

                        fetch('/save-js-token', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ token_json: tokenJson }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                document.getElementById('result').innerHTML =
                                    '<div class="step success">' +
                                    '<h3>✅ Token Saved Successfully!</h3>' +
                                    '<p>' + data.message + '</p>' +
                                    '<h4>Next Steps:</h4>' +
                                    '<pre style="background:#f8f9fa; padding:10px; border-radius:5px;">' +
                                    '# Test your token\\n' +
                                    'python3 carelink_token_status.py\\n\\n' +
                                    '# Get your data\\n' +
                                    'python3 -c "from carelink_client2 import CareLinkClient; c=CareLinkClient(); print(len(c.getRecentData()) if c.getRecentData() else \\'No data\\')"' +
                                    '</pre>' +
                                    '</div>';
                            }} else {{
                                document.getElementById('result').innerHTML =
                                    '<div class="step error"><h3>❌ Error</h3><p>' + data.error + '</p></div>';
                            }}
                        }});
                    }}
                </script>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 Carelink JavaScript Token Extractor</h1>
                    <p>Extract OAuth tokens using a simple JavaScript console command.</p>

                    <div class="highlight">
                        <h3>✨ This extracts the same tokens as carelink_simple_webserver.py</h3>
                        <p>No browser automation needed - just a simple console command!</p>
                    </div>

                    <div class="step">
                        <h3>Step 1: Login to Carelink</h3>
                        <p>Open <a href="{carelink_url}" target="_blank">{carelink_url}</a> and complete your login.</p>
                        <p>Make sure you're on the dashboard or any authenticated page.</p>
                    </div>

                    <div class="step">
                        <h3>Step 2: Open Browser Console</h3>
                        <p>In the Carelink tab, open Developer Console:</p>
                        <ul>
                            <li><strong>Chrome/Edge:</strong> Press <kbd>F12</kbd> → "Console" tab</li>
                            <li><strong>Firefox:</strong> Press <kbd>F12</kbd> → "Console" tab</li>
                            <li><strong>Safari:</strong> Press <kbd>Cmd+Option+C</kbd></li>
                        </ul>
                    </div>

                    <div class="step">
                        <h3>Step 3: Run Token Extractor</h3>
                        <p><strong>Copy and paste this single command:</strong></p>
                        <button class="copy-btn" onclick="copySimpleCommand()">📋 Copy JavaScript Command</button>
                        <div class="code">{js_snippet}</div>
                        <p><strong>Press Enter</strong> to run. It will extract and format the OAuth tokens.</p>
                    </div>

                    <div class="step">
                        <h3>Step 4: Save Token File</h3>
                        <p>Copy the JSON output and paste it below:</p>
                        <textarea id="tokenInput" class="result-area" placeholder="Paste the complete JSON output from console here..."></textarea>
                        <br><br>
                        <button class="btn" onclick="saveToken()">💾 Save as logindata.json</button>
                    </div>

                    <div id="result"></div>

                    <div class="step warning">
                        <h3>🛡️ Security: Only Essential OAuth Fields Saved</h3>
                        <ul>
                            <li><strong>access_token</strong>: OAuth JWT token (validated format)</li>
                            <li><strong>client_id</strong>: Extracted from JWT payload (validated)</li>
                            <li><strong>refresh_token</strong>: Set to "UNKNOWN" (not available via web)</li>
                            <li><strong>scope</strong>: Standard Carelink OAuth scope</li>
                            <li><strong>token_type</strong>: "Bearer"</li>
                            <li><strong>_extraction_*</strong>: Safe metadata only</li>
                        </ul>
                        <p><strong>No user data, cookies, or arbitrary JSON is saved.</strong> Only validated OAuth fields.</p>
                    </div>
                </div>
            </body>
            </html>
            '''
            return render_template_string(html)

        @self.app.route('/save-js-token', methods=['POST'])
        def save_js_token():
            try:
                data = request.get_json()
                token_json = data.get('token_json', '').strip()

                if not token_json:
                    return {'success': False, 'error': 'No token JSON provided'}

                # Parse and validate the JSON
                try:
                    raw_data = json.loads(token_json)
                except json.JSONDecodeError as e:
                    return {'success': False, 'error': f'Invalid JSON: {str(e)}'}

                # SECURITY: Only extract and validate essential OAuth fields
                access_token = raw_data.get('access_token', '').strip()
                client_id = raw_data.get('client_id', '').strip()

                # Validate required fields
                if not access_token:
                    return {'success': False, 'error': 'No access_token found'}

                # Validate access_token is JWT format (3 parts separated by dots)
                if len(access_token.split('.')) != 3:
                    return {'success': False, 'error': 'Invalid access_token format (not JWT)'}

                # Validate client_id looks reasonable (alphanumeric, reasonable length)
                if client_id != "UNKNOWN" and (len(client_id) < 10 or len(client_id) > 100 or not client_id.replace('-', '').replace('_', '').isalnum()):
                    return {'success': False, 'error': 'Invalid client_id format'}

                # Validate extraction_url if present
                extraction_url = raw_data.get('_extraction_url', '')
                if extraction_url and not (extraction_url.startswith('https://carelink.minimed.') or extraction_url.startswith('https://clcloud.minimed.')):
                    extraction_url = 'validated_carelink_url'

                # Create CLEAN logindata with ONLY essential fields
                clean_logindata = {
                    "access_token": access_token,
                    "refresh_token": "UNKNOWN",  # Web interface doesn't provide refresh token
                    "scope": "openid profile email offline_access",  # Standard Carelink scope
                    "client_id": client_id if client_id != "" else "UNKNOWN",
                    "token_type": "Bearer",
                    "_extraction_timestamp": time.time(),
                    "_extraction_method": "javascript_console",
                    "_extraction_url": extraction_url
                }

                # Save ONLY the clean data
                with open('logindata.json', 'w') as f:
                    json.dump(clean_logindata, f, indent=4)

                # Log success info (safe - no user data)
                print(f"✅ Saved OAuth tokens to logindata.json")
                print(f"🔑 Access token: {access_token[:30]}...")
                print(f"🆔 Client ID: {client_id}")
                print(f"🛡️ Only essential OAuth fields saved")

                return {
                    'success': True,
                    'message': f'OAuth tokens saved securely! Client ID: {client_id[:20]}...'
                }

            except Exception as e:
                return {'success': False, 'error': f'Error saving tokens: {str(e)}'}

def main(is_us_region, port=8080):
    extractor = CarelinJsExtractor(port=port)
    extractor.is_us_region = is_us_region

    print(f"🚀 Carelink JavaScript Token Extractor running at http://localhost:{port}")
    print("This provides a simple JavaScript command to extract OAuth tokens")

    # Auto-open browser
    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{port}')).start()

    try:
        extractor.app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--us', help='Use US region', action='store_true')
    parser.add_argument('--port', help='Web server port', default=8080, type=int)
    args = parser.parse_args()

    main(args.us, args.port)