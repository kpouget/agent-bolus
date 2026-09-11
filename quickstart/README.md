# Quickstart Scripts for Carelink MCP Servers

This directory contains ready-to-use scripts for the Carelink MCP servers.

## 📁 Scripts Overview

### `helpers.sh` - Function Library
**Purpose:** Bash functions that wrap the JSON-RPC calls for easy CLI usage  
**Usage:** `source quickstart/helpers.sh` then use functions like `download_csv 30`  
**Best for:** Daily use, adding to your `.bashrc`

**Functions included:**
- `download_csv()` - Download CSV data
- `get_web_data()` - Get web interface data  
- `get_bg_readings()` - Get glucose readings by day
- `get_bg_range()` - Get readings for date range
- `query_web_data()` - Query aggregated web data
- `list_csv_files()` - List available files
- `check_auth()` - Check authentication

### `basic.sh` - Raw Examples
**Purpose:** Demonstrates raw JSON-RPC commands  
**Usage:** `bash quickstart/basic.sh`  
**Best for:** Learning the protocol, troubleshooting, copy-paste commands

### `workflows.sh` - Complete Workflows
**Purpose:** End-to-end workflows for common diabetes monitoring tasks  
**Usage:** `bash quickstart/workflows.sh`  
**Best for:** Automated monitoring, comprehensive analysis

**Workflows included:**
- Daily monitoring
- Weekly review
- Monthly analysis
- File management
- Comparative analysis
- Error recovery
- Data extraction

### `oneliners.sh` - Command Examples
**Purpose:** Displays copy-paste ready one-liner commands  
**Usage:** `bash quickstart/oneliners.sh`  
**Best for:** Quick reference, creating custom aliases

### `testing.sh` - Test Suite
**Purpose:** Comprehensive testing and debugging  
**Usage:** `bash quickstart/testing.sh`  
**Best for:** Troubleshooting, verifying setup, continuous integration

**Tests included:**
- Server responsiveness
- Tool listing
- JSON validation
- Error handling
- File system checks
- Dependencies
- Permissions
- Authentication

## 🚀 Quick Start

1. **Easy way** (recommended):
   ```bash
   source quickstart/helpers.sh
   download_csv 14
   get_bg_readings 1
   ```

2. **Test everything first**:
   ```bash
   bash quickstart/testing.sh
   ```

3. **See all examples**:
   ```bash
   bash quickstart/basic.sh
   ```

4. **Run complete workflow**:
   ```bash
   bash quickstart/workflows.sh
   ```

## 💡 Pro Tips

- **Add to .bashrc**: Add `source /path/to/quickstart/helpers.sh` to your `.bashrc` for permanent access
- **Create aliases**: Use `oneliners.sh` output to create custom aliases
- **Pipe through jq**: Add `| jq '.'` to any command for pretty JSON output
- **File auto-selection**: Omit filepath parameters to auto-select most recent files
- **Error checking**: All scripts include error handling and status checks

## 🔧 Requirements

- Python 3.x
- Valid Carelink authentication (`logindata.json`)
- Optional: `jq` for JSON formatting
- Optional: `timeout` command for testing

## 📊 Example Session

```bash
# Load functions
source quickstart/helpers.sh

# Check setup
check_auth

# Download fresh data  
download_csv 7

# Get yesterday's readings
get_bg_readings 1

# Check weekly Time-in-Range
query_web_data 7 0 tir
```

Happy glucose monitoring! 📊💉