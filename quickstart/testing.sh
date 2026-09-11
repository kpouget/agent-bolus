#!/bin/bash
# Testing and Debugging Scripts for Carelink MCP Servers

echo "=== MCP Server Testing Suite ==="

echo "1. Testing API Server (carelink_mcp_server.py)..."
python3 carelink_mcp_server.py --test

echo -e "\n2. Testing Data Server (carelink_data_mcp_server.py)..."
python3 carelink_data_mcp_server.py --test

echo -e "\n3. Checking server responsiveness..."
echo "Testing API server response:"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py | head -1

echo "Testing Data server response:"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_data_mcp_server.py | head -1

echo -e "\n4. Listing available tools for each server..."
echo "API Server tools:"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py | jq '.tools[].name' 2>/dev/null || echo "jq not available"

echo "Data Server tools:"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_data_mcp_server.py | jq '.tools[].name' 2>/dev/null || echo "jq not available"

echo -e "\n5. Testing JSON validation..."
echo "Valid JSON test:"
echo '{"method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' | jq '.' > /dev/null 2>&1 && echo "✅ JSON is valid" || echo "❌ JSON is invalid"

echo "Invalid JSON test (should fail):"
echo '{"method": "tools/call", "params": {"name": "get_user_info", "arguments":}' | python3 carelink_mcp_server.py

echo -e "\n6. Testing error handling..."
echo "Testing invalid tool name:"
echo '{"method": "tools/call", "params": {"name": "invalid_tool", "arguments": {}}}' | python3 carelink_mcp_server.py

echo "Testing invalid parameters:"
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": -1}}}' | python3 carelink_mcp_server.py

echo -e "\n7. File system checks..."
echo "Checking data directory:"
ls -la data/ 2>/dev/null || echo "No data directory found"

echo "Checking carelink-python-client directory:"
ls -la carelink-python-client/ 2>/dev/null || echo "No carelink-python-client directory found"

echo "Checking for logindata.json:"
ls -la carelink-python-client/logindata.json 2>/dev/null && echo "✅ logindata.json found" || echo "❌ logindata.json not found"

echo -e "\n8. Dependencies check..."
echo "Checking Python version:"
python3 --version

echo "Checking if jq is available:"
command -v jq >/dev/null 2>&1 && echo "✅ jq is available" || echo "❌ jq not found (install with: sudo dnf install jq)"

echo "Checking required Python modules:"
python3 -c "import json, sys, os, datetime; print('✅ Basic Python modules available')" 2>/dev/null || echo "❌ Missing basic Python modules"

echo -e "\n9. Permission checks..."
echo "Checking file permissions:"
[ -x carelink_mcp_server.py ] && echo "✅ carelink_mcp_server.py is executable" || echo "❌ carelink_mcp_server.py not executable"
[ -x carelink_data_mcp_server.py ] && echo "✅ carelink_data_mcp_server.py is executable" || echo "❌ carelink_data_mcp_server.py not executable"

echo "Checking data directory permissions:"
[ -w data/ ] && echo "✅ data/ directory is writable" || echo "❌ data/ directory not writable"

echo -e "\n10. Quick functional test..."
echo "Testing authentication (if credentials available):"
timeout 10 bash -c 'echo '"'"'{"method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}'"'"' | python3 carelink_mcp_server.py' | head -3

echo -e "\n✅ Testing completed!"
echo "💡 If any tests failed, check the error messages above."
echo "💡 For authentication issues, ensure logindata.json is properly configured."