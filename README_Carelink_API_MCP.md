# Carelink API MCP Server

Direct interaction MCP server for downloading data from Carelink API and returning file paths.

## Overview

The Carelink API MCP server (`carelink_mcp/carelink_mcp_server.py`) provides programmatic access to Carelink diabetes data through an MCP interface. It downloads data and returns file paths for further processing.

## Available Tools

### 1. `download_csv` 
Download historical CSV data for specified number of days
- **Parameters**: `days` (1-90, default: 14)
- **Returns**: File path and metadata
- **Example**: Download 30 days of data

### 2. `get_web_data`
Get summary JSON data from Carelink web interface
- **Parameters**: None
- **Returns**: File path and data summary
- **Features**: May contain more historical data than mobile API

### 3. `get_recent_data`
Get recent JSON data from mobile API
- **Parameters**: None  
- **Returns**: File path and recent data (2-3 days)
- **Use**: Quick access to latest readings

### 4. `get_user_info`
Check authentication status and client info
- **Parameters**: None
- **Returns**: Client version and status
- **Use**: Verify tokens are working

## Data Types Returned

### CSV Downloads
- **Historical pump and sensor data**
- **Date range**: Configurable (1-90 days)
- **Format**: Standard Carelink CSV with all fields
- **File location**: `data/` (main project directory)

### Web Interface Data
- **Summary JSON** from personalWebView endpoint
- **Content**: Sensor glucose, markers, events, settings
- **Advantage**: May include more historical data than mobile API
- **Analysis**: Automatic data summary with counts and date ranges

### Recent Mobile Data
- **JSON format** from mobile carepartner API
- **Timespan**: Last 2-3 days typically
- **Content**: Latest readings and device status

## Setup Requirements

### Authentication
- Requires `logindata.json` in `carelink-python-client/` directory
- Downloaded data saved to main project `data/` directory
- Tokens can be generated using the OAuth scripts
- Automatic token refresh handled by client

### Dependencies
- Carelink Python client library
- Valid Carelink account credentials
- Network access to Carelink servers

## Usage Examples

### Download 14 days of CSV data:
```python
# MCP call to download_csv tool with days=14
# Returns: {"file_path": "/path/to/csv_report_14days-20260818_223045.csv", ...}
```

### Get web interface summary:
```python  
# MCP call to get_web_data tool
# Returns data analysis including:
# - sgs_count: 1440 entries
# - markers_count: 25 entries  
# - Sample dates for each data type
```

### Check authentication:
```python
# MCP call to get_user_info tool
# Returns: {"success": true, "client_version": "1.4", ...}
```

## File Paths

All downloaded files are saved to:
```
data/
├── csv_report_14days-20260818_223045.csv
├── web_data-20260818_223045.json
└── recent_data-20260818_223045.json
```

Project structure:
```
agent-bolus/
├── carelink-python-client/
│   ├── logindata.json          (authentication)
│   └── *.py                    (client library)
└── data/                       (all downloads)
    ├── *.csv                   (CSV reports)
    └── *.json                  (JSON data files)
```

**Absolute paths returned** for programmatic access.

## Error Handling

Common error scenarios:
- **Authentication failure**: Check `logindata.json` exists
- **Token expired**: Client handles automatic refresh  
- **Network issues**: Clear error messages returned
- **Invalid parameters**: Input validation with helpful messages

## Benefits

- ✅ **Programmatic access** to Carelink data
- ✅ **File path returns** for integration with other tools
- ✅ **Multiple data sources** (CSV, web, mobile APIs)
- ✅ **Automatic authentication** handling
- ✅ **Error recovery** with token refresh
- ✅ **Data analysis** and summaries included

Perfect for building diabetes data analysis pipelines! 📊💉