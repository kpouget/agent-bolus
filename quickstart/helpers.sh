#!/bin/bash
# Carelink MCP Server Helper Functions
# Add these to your .bashrc or source this file: source quickstart/helpers.sh

# Download CSV data
download_csv() {
    local days=${1:-14}
    echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"download_csv\", \"arguments\": {\"days\": $days}}}" | python3 carelink_mcp/carelink_mcp_server.py
}

# Get web data
get_web_data() {
    echo '{"method": "tools/call", "params": {"name": "get_web_data", "arguments": {}}}' | python3 carelink_mcp/carelink_mcp_server.py
}

# Get recent data
get_recent_data() {
    echo '{"method": "tools/call", "params": {"name": "get_recent_data", "arguments": {}}}' | python3 carelink_mcp/carelink_mcp_server.py
}

# Check auth status
check_auth() {
    echo '{"method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' | python3 carelink_mcp/carelink_mcp_server.py
}

# List CSV files
list_csv_files() {
    echo '{"method": "tools/call", "params": {"name": "list_csv_files", "arguments": {}}}' | python3 carelink_mcp/carelink_data_mcp_server.py
}

# Get BG readings by age
get_bg_readings() {
    local age=${1:-0}
    local filepath=${2:-""}
    if [ -z "$filepath" ]; then
        echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": $age}}}" | python3 carelink_mcp/carelink_data_mcp_server.py
    else
        echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": $age, \"filepath\": \"$filepath\"}}}" | python3 carelink_mcp/carelink_data_mcp_server.py
    fi
}

# Get BG readings range
get_bg_range() {
    local start_age=${1:-0}
    local end_age=${2:-7}
    echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings_range\", \"arguments\": {\"start_age\": $start_age, \"end_age\": $end_age}}}" | python3 carelink_mcp/carelink_data_mcp_server.py
}

# Query web aggregated data
query_web_data() {
    local aggreg=$1
    local age=$2
    local field=$3
    echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"query_web_data\", \"arguments\": {\"aggreg\": $aggreg, \"age\": $age, \"field\": \"$field\"}}}" | python3 carelink_mcp/carelink_data_mcp_server.py
}

# Utility functions for JSON processing
pretty_json() {
    jq '.'
}

extract_file_path() {
    jq -r '.content[0].text' | grep "File path:" | cut -d' ' -f3
}

extract_readings_count() {
    jq -r '.content[0].text' | grep "Total readings:" | cut -d':' -f2 | xargs
}

# Usage examples:
# download_csv 30          # Download 30 days
# get_web_data            # Get web interface data
# list_csv_files          # See available files
# get_bg_readings 1       # Yesterday's readings
# get_bg_range 0 7        # Last week
# query_web_data 7 0 tir  # Weekly Time-in-Range