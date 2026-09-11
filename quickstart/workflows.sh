#!/bin/bash
# Complete Workflows for Diabetes Data Monitoring
# Source the helpers first: source quickstart/helpers.sh

# Make sure to source helpers
if ! command -v download_csv &> /dev/null; then
    echo "Loading helper functions..."
    source "$(dirname "$0")/helpers.sh"
fi

echo "=== Daily Monitoring Workflow ==="
echo "Checking authentication and downloading today's data..."

# Check auth and download today's data
check_auth
if [ $? -eq 0 ]; then
    echo "✅ Authentication successful"
    download_csv 1
    echo "📊 Getting today's readings..."
    get_bg_readings 0
else
    echo "❌ Authentication failed"
    exit 1
fi

echo -e "\n=== Weekly Review Workflow ==="
echo "Downloading weekly data and generating summary..."

# Download weekly data
download_csv 7

# Get weekly readings range
echo "📈 Getting weekly readings..."
get_bg_range 0 7

# Check weekly Time-in-Range
echo "🎯 Getting weekly Time-in-Range..."
query_web_data 7 0 tir

echo -e "\n=== Monthly Analysis Workflow ==="
echo "Downloading monthly data and generating comprehensive analysis..."

# Download 30 days
download_csv 30

# Monthly glucose summary
echo "📊 Getting monthly glucose summary..."
query_web_data 30 0 sg

# Monthly sensor usage
echo "🔋 Getting monthly sensor usage..."
query_web_data 30 0 sensorUsage

# Monthly TIR
echo "🎯 Getting monthly Time-in-Range..."
query_web_data 30 0 tir

echo -e "\n=== File Management Workflow ==="
echo "Checking available files and recent data..."

# See what files we have
echo "📂 Available CSV files:"
list_csv_files

# Get latest readings from auto-selected file
echo "📊 Latest readings:"
get_bg_readings 1

# Check most recent web data
echo "🌐 Recent glucose data:"
query_web_data 1 0 sg

echo -e "\n=== Comparative Analysis Workflow ==="
echo "Comparing different time periods..."

# Compare different time periods
echo "📈 Today's TIR:"
query_web_data 1 0 tir

echo "📈 This week's TIR:"
query_web_data 7 0 tir

echo "📈 This month's TIR:"
query_web_data 30 0 tir

echo -e "\n=== Error Recovery Workflow ==="
echo "Testing error handling and recovery..."

# Check auth first
echo "🔐 Checking authentication..."
check_auth

# List available files first
echo "📂 Checking available files..."
list_csv_files

# Test with invalid parameters (this should fail gracefully)
echo "❌ Testing error handling (invalid days)..."
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 999}}}' | python3 carelink_mcp/carelink_mcp_server.py

echo -e "\n=== Data Extraction Workflow ==="
echo "Extracting specific data points with jq..."

# Extract file path from download
echo "📁 Downloading and extracting file path..."
FILE_PATH=$(download_csv 7 | extract_file_path)
echo "Downloaded to: $FILE_PATH"

# Extract readings count
echo "🔢 Getting readings count..."
READINGS_COUNT=$(get_bg_readings 1 | extract_readings_count)
echo "Yesterday's readings count: $READINGS_COUNT"

# Pretty print glucose data
echo "✨ Pretty printing glucose data..."
query_web_data 1 0 sg | pretty_json

echo -e "\n=== Continuous Monitoring Workflow ==="
echo "Setting up for continuous monitoring..."

# Function to run continuous monitoring
continuous_monitor() {
    local interval=${1:-300}  # Default 5 minutes
    echo "🔄 Starting continuous monitoring (${interval}s intervals)..."

    while true; do
        echo "$(date): Checking glucose data..."
        get_bg_readings 0 | jq -r '.content[0].text' | head -5
        sleep $interval
    done
}

# Uncomment to run continuous monitoring
# continuous_monitor 300

echo -e "\n✅ All workflows completed!"
echo "💡 To run continuous monitoring: continuous_monitor 300"