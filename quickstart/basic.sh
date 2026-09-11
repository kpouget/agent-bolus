#!/bin/bash
# Basic JSON-RPC Examples for Carelink MCP Servers
# Raw commands using echo and pipes

echo "=== Carelink API Server (Fresh Data Downloads) ==="

echo "1. Download CSV Data"
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | python3 carelink_mcp_server.py

echo -e "\n2. Download 30 days"
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 30}}}' | python3 carelink_mcp_server.py

echo -e "\n3. Get Web Interface Data"
echo '{"method": "tools/call", "params": {"name": "get_web_data", "arguments": {}}}' | python3 carelink_mcp_server.py

echo -e "\n4. Get Recent Mobile Data"
echo '{"method": "tools/call", "params": {"name": "get_recent_data", "arguments": {}}}' | python3 carelink_mcp_server.py

echo -e "\n5. Check Authentication Status"
echo '{"method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' | python3 carelink_mcp_server.py

echo -e "\n6. List Available Tools (API Server)"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py

echo -e "\n\n=== Carelink Data Server (Query Existing Files) ==="

echo "1. List Available CSV Files"
echo '{"method": "tools/call", "params": {"name": "list_csv_files", "arguments": {}}}' | python3 carelink_data_mcp_server.py

echo -e "\n2. Get Today's Readings (age=0)"
echo '{"method": "tools/call", "params": {"name": "get_bg_readings", "arguments": {"age": 0}}}' | python3 carelink_data_mcp_server.py

echo -e "\n3. Get Yesterday's Readings (age=1)"
echo '{"method": "tools/call", "params": {"name": "get_bg_readings", "arguments": {"age": 1}}}' | python3 carelink_data_mcp_server.py

echo -e "\n4. Get Last Week Range (0-7 days ago)"
echo '{"method": "tools/call", "params": {"name": "get_bg_readings_range", "arguments": {"start_age": 0, "end_age": 7}}}' | python3 carelink_data_mcp_server.py

echo -e "\n5. Query Time-in-Range for Today"
echo '{"method": "tools/call", "params": {"name": "query_web_data", "arguments": {"aggreg": 1, "age": 0, "field": "tir"}}}' | python3 carelink_data_mcp_server.py

echo -e "\n6. Query Weekly Sensor Usage"
echo '{"method": "tools/call", "params": {"name": "query_web_data", "arguments": {"aggreg": 7, "age": 1, "field": "sensorUsage"}}}' | python3 carelink_data_mcp_server.py

echo -e "\n7. List Available Tools (Data Server)"
echo '{"method": "tools/list", "params": {}}' | python3 carelink_data_mcp_server.py

echo -e "\n\n=== With JSON Pretty Printing (requires jq) ==="

echo "Pretty print download result:"
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 7}}}' | python3 carelink_mcp_server.py | jq '.'

echo -e "\nExtract file path from download:"
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | python3 carelink_mcp_server.py | jq -r '.content[0].text' | grep "File path:" | cut -d' ' -f3