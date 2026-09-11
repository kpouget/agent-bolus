# Carelink MCP Servers - CLI Terminal Usage

This guide shows how to invoke the MCP servers directly from the command line terminal.

## 🚀 Quick Start Options

Choose your preferred way to get started:

### 📁 Ready-to-Use Scripts
```bash
# Use pre-built helper functions
source quickstart/helpers.sh
download_csv 14
get_bg_readings 1

# Run complete workflows  
bash quickstart/workflows.sh

# Copy one-liner commands
bash quickstart/oneliners.sh

# Test everything
bash quickstart/testing.sh

# See all raw examples
bash quickstart/basic.sh
```

### 🧪 Test Mode (No setup required)
```bash
# Test the API server (downloads fresh data)
python3 carelink_mcp_server.py --test

# Test the data analysis server (queries existing files)
python3 carelink_data_mcp_server.py --test
```

## 📊 Server 1: `carelink_mcp_server.py` - Download Fresh Data

### CLI Usage via JSON-RPC

The server accepts JSON-RPC requests via stdin. Here are terminal examples:

#### 1. Download CSV Data
```bash
# Download 14 days (default)
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | python3 carelink_mcp_server.py

# Download 30 days
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 30}}}' | python3 carelink_mcp_server.py

# Download 7 days
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 7}}}' | python3 carelink_mcp_server.py
```

#### 2. Get Web Interface Data
```bash
echo '{"method": "tools/call", "params": {"name": "get_web_data", "arguments": {}}}' | python3 carelink_mcp_server.py
```

#### 3. Get Recent Mobile Data
```bash
echo '{"method": "tools/call", "params": {"name": "get_recent_data", "arguments": {}}}' | python3 carelink_mcp_server.py
```

#### 4. Check Authentication Status
```bash
echo '{"method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' | python3 carelink_mcp_server.py
```

#### 5. List Available Tools
```bash
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py
```

## 🔍 Server 2: `carelink_data_mcp_server.py` - Query Existing Data

### CLI Usage Examples

#### 1. List Available CSV Files
```bash
echo '{"method": "tools/call", "params": {"name": "list_csv_files", "arguments": {}}}' | python3 carelink_data_mcp_server.py
```

#### 2. Get Blood Glucose Readings by Day
```bash
# Today's readings (age=0)
echo '{"method": "tools/call", "params": {"name": "get_bg_readings", "arguments": {"filepath": "/home/kpouget/vayrac/git/agent-bolus/data/csv_report_14days-20260818_222356.csv", "age": 0}}}' | python3 carelink_data_mcp_server.py

# Yesterday's readings (age=1)  
echo '{"method": "tools/call", "params": {"name": "get_bg_readings", "arguments": {"filepath": "/home/kpouget/vayrac/git/agent-bolus/data/csv_report_14days-20260818_222356.csv", "age": 1}}}' | python3 carelink_data_mcp_server.py

# Auto-select most recent file (omit filepath)
echo '{"method": "tools/call", "params": {"name": "get_bg_readings", "arguments": {"age": 1}}}' | python3 carelink_data_mcp_server.py
```

#### 3. Get Readings for Date Range
```bash
# Last week (0-7 days ago)
echo '{"method": "tools/call", "params": {"name": "get_bg_readings_range", "arguments": {"filepath": "/home/kpouget/vayrac/git/agent-bolus/data/csv_report_14days-20260818_222356.csv", "start_age": 0, "end_age": 7}}}' | python3 carelink_data_mcp_server.py

# Auto-select most recent file
echo '{"method": "tools/call", "params": {"name": "get_bg_readings_range", "arguments": {"start_age": 3, "end_age": 5}}}' | python3 carelink_data_mcp_server.py
```

#### 4. Query Web Data Aggregations
```bash
# Time-in-Range for today (1-day aggregation, age 0)
echo '{"method": "tools/call", "params": {"name": "query_web_data", "arguments": {"aggreg": 1, "age": 0, "field": "tir"}}}' | python3 carelink_data_mcp_server.py

# Sensor usage for this week (7-day aggregation, age 1)
echo '{"method": "tools/call", "params": {"name": "query_web_data", "arguments": {"aggreg": 7, "age": 1, "field": "sensorUsage"}}}' | python3 carelink_data_mcp_server.py

# 14-day glucose summary
echo '{"method": "tools/call", "params": {"name": "query_web_data", "arguments": {"aggreg": 14, "age": 1, "field": "sg"}}}' | python3 carelink_data_mcp_server.py
```

#### 5. List Available Tools
```bash
echo '{"method": "tools/list", "params": {}}' | python3 carelink_data_mcp_server.py
```

## 📁 Quickstart Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `quickstart/helpers.sh` | Bash functions for easy CLI use | `source quickstart/helpers.sh` |
| `quickstart/basic.sh` | Raw JSON-RPC examples | `bash quickstart/basic.sh` |
| `quickstart/workflows.sh` | Complete monitoring workflows | `bash quickstart/workflows.sh` |  
| `quickstart/oneliners.sh` | Copy-paste command examples | `bash quickstart/oneliners.sh` |
| `quickstart/testing.sh` | Test suite and debugging | `bash quickstart/testing.sh` |

### Helper Functions Quick Reference
After sourcing `quickstart/helpers.sh`:
```bash
download_csv 30          # Download 30 days
get_web_data            # Get web interface data
list_csv_files          # See available files
get_bg_readings 1       # Yesterday's readings
get_bg_range 0 7        # Last week
query_web_data 7 0 tir  # Weekly Time-in-Range
```

## 📄 JSON Output Processing

Pipe the output through `jq` for better formatting:

```bash
# Pretty print JSON output
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | python3 carelink_mcp_server.py | jq '.'

# Extract just the file path from download
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | python3 carelink_mcp_server.py | jq -r '.content[0].text' | grep "File path:" | cut -d' ' -f3

# Extract readings count
get_bg_readings 1 | jq -r '.content[0].text' | grep "Total readings:" | cut -d':' -f2 | xargs
```

## 🏃‍♂️ Common CLI Workflows

### Daily Monitoring
```bash
# Check auth and download today's data
check_auth
download_csv 1

# Get today's readings
get_bg_readings 0
```

### Weekly Review  
```bash
# Download weekly data
download_csv 7

# Get weekly readings range
get_bg_range 0 7

# Check weekly Time-in-Range
query_web_data 7 0 tir
```

### File Management
```bash
# See what files we have
list_csv_files

# Get latest readings from auto-selected file
get_bg_readings 1

# Check most recent web data
query_web_data 1 0 sg
```

## 🧪 Testing & Debugging

```bash
# Run built-in tests
python3 carelink_mcp_server.py --test
python3 carelink_data_mcp_server.py --test

# List available tools for each server
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py | jq '.'
echo '{"method": "tools/list", "params": {}}' | python3 carelink_data_mcp_server.py | jq '.'

# Check if servers are responding
echo '{"method": "tools/list", "params": {}}' | python3 carelink_mcp_server.py | head -1
```

## 📁 File Paths

Downloaded files go to:
```bash
ls -la data/
# csv_report_14days-20260818_222356.csv
# web_data-20260818_223045.json  
# recent_data-20260818_223045.json
```

Use absolute paths when specifying filepaths:
```bash
PWD_DATA="$(pwd)/data"
echo "{\"method\": \"tools/call\", \"params\": {\"name\": \"get_bg_readings\", \"arguments\": {\"age\": 1, \"filepath\": \"$PWD_DATA/csv_report_14days-20260818_222356.csv\"}}}" | python3 carelink_data_mcp_server.py
```

## ⚠️ Error Handling

Common issues and solutions:

```bash
# Authentication errors
check_auth  # Verify tokens are working

# File not found - list available files first
list_csv_files

# Invalid JSON - validate with jq
echo '{"method": "tools/call", "params": {"name": "download_csv", "arguments": {"days": 14}}}' | jq '.'
```

## 💡 Pro Tips

1. **Use jq**: Always pipe output through `jq` for readable JSON
2. **Helper functions**: Add the bash functions to your `.bashrc` 
3. **Auto-select files**: Omit filepath to use most recent file automatically
4. **Batch operations**: Download once, then query multiple times
5. **Error checking**: Check `echo $?` after commands for error status
6. **File validation**: Use `list_csv_files` to see available data before querying

## 📋 Parameters Reference

### Download CSV (`download_csv`)
- `days`: Integer 1-90 (default: 14)

### BG Readings (`get_bg_readings`) 
- `age`: Integer ≥ 0 (0=today, 1=yesterday, etc.)
- `filepath`: Optional absolute path (auto-selects if omitted)

### BG Range (`get_bg_readings_range`)
- `start_age`: Integer ≥ 0 (default: 0)  
- `end_age`: Integer ≥ 0 (default: 7)
- `filepath`: Optional absolute path

### Web Data Query (`query_web_data`)
- `aggreg`: 1, 7, 14, or 30 (aggregation period in days)
- `age`: Integer ≥ 0 (which period: 0=current, 1=previous, etc.)
- `field`: "tir", "sensorUsage", or "sg"
- `filepath`: Optional absolute path to web data JSON

## 🎯 Real Examples

### Download and analyze today's data:
```bash
download_csv 1
get_bg_readings 0 | jq -r '.content[0].text' | grep -A 20 "Total readings"
```

### Weekly diabetes review:
```bash
download_csv 7
query_web_data 7 0 tir | jq -r '.content[0].text'
get_bg_range 0 7 | jq -r '.content[0].text' | head -20
```

### Check multiple time periods:
```bash
query_web_data 1 0 tir    # Today's TIR
query_web_data 7 0 tir    # This week's TIR  
query_web_data 14 0 tir   # This 14-day period TIR
```

## 🎯 Complete Example Session

```bash
# 1. Load helper functions
source quickstart/helpers.sh

# 2. Test everything is working
bash quickstart/testing.sh

# 3. Download fresh data
download_csv 14

# 4. Get yesterday's readings
get_bg_readings 1

# 5. Check weekly Time-in-Range  
query_web_data 7 0 tir

# 6. Run a complete workflow
bash quickstart/workflows.sh
```

## 📚 Further Reading

- **`quickstart/README.md`** - Detailed script documentation
- **`quickstart/basic.sh`** - Raw JSON-RPC examples for learning
- **`quickstart/oneliners.sh`** - Copy-paste commands and alias ideas
- **`README_Carelink_API_MCP.md`** - API server details
- **`README_MCP_Server.md`** - Data server details

Happy CLI glucose monitoring! 📊💉