#!/bin/bash
# One-liner Commands for Quick Diabetes Data Access

echo "=== Quick One-liner Commands ==="
echo "Copy and paste these into your terminal for immediate use"
echo ""

echo "📊 DOWNLOAD DATA:"
echo "# Download 7 days CSV:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 7}}}' | python3 carelink_mcp_server.py"
echo ""

echo "# Download 30 days CSV:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 30}}}' | python3 carelink_mcp_server.py"
echo ""

echo "# Get web interface data:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_web_data\", \"arguments\": {}}}' | python3 carelink_mcp_server.py"
echo ""

echo "🔍 QUERY READINGS:"
echo "# Today's readings:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": 0}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Yesterday's readings:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": 1}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Last week range:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings_range\", \"arguments\": {\"start_age\": 0, \"end_age\": 7}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "📈 TIME-IN-RANGE:"
echo "# Today's TIR:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 1, \"age\": 0, \"field\": \"tir\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Weekly TIR:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 7, \"age\": 0, \"field\": \"tir\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Monthly TIR:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 30, \"age\": 0, \"field\": \"tir\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "🔋 SENSOR USAGE:"
echo "# Daily sensor usage:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 1, \"age\": 0, \"field\": \"sensorUsage\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Weekly sensor usage:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 7, \"age\": 0, \"field\": \"sensorUsage\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "📂 FILE MANAGEMENT:"
echo "# List CSV files:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"list_csv_files\", \"arguments\": {}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Check authentication:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_user_info\", \"arguments\": {}}}' | python3 carelink_mcp_server.py"
echo ""

echo "🎨 WITH JSON FORMATTING (requires jq):"
echo "# Pretty print download:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 14}}}' | python3 carelink_mcp_server.py | jq '.'"
echo ""

echo "# Extract file path:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 14}}}' | python3 carelink_mcp_server.py | jq -r '.content[0].text' | grep 'File path:' | cut -d' ' -f3"
echo ""

echo "# Extract readings count:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": 1}}}' | python3 carelink_data_mcp_server.py | jq -r '.content[0].text' | grep 'Total readings:' | cut -d':' -f2 | xargs"
echo ""

echo "🚀 QUICK COMBOS:"
echo "# Download and check today:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 1}}}' | python3 carelink_mcp_server.py && echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": 0}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Quick TIR comparison:"
echo "echo 'Today:' && echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 1, \"age\": 0, \"field\": \"tir\"}}}' | python3 carelink_data_mcp_server.py && echo 'Week:' && echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": 7, \"age\": 0, \"field\": \"tir\"}}}' | python3 carelink_data_mcp_server.py"
echo ""

echo "# Auth check and download:"
echo "echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"get_user_info\", \"arguments\": {}}}' | python3 carelink_mcp_server.py && echo '{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": 7}}}' | python3 carelink_mcp_server.py"
echo ""

echo "💡 Pro tip: Add 'alias glucose=' before any command to make it shorter!"
echo "💡 Example: alias glucose_today=\"echo '{\\\"method\\\": \\\"tools/call\\\", \\\"params\\\": {\\\"name\\\": \\\"get_bg_readings\\\", \\\"arguments\\\": {\\\"age\\\": 0}}}' | python3 carelink_data_mcp_server.py\""