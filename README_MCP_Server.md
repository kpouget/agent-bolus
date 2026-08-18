# Carelink CSV MCP Server

An MCP server for exploring Carelink CSV files and querying glucose readings by age (days ago).

## Setup

The MCP server is located at: `carelink_csv_mcp_server.py`

## Features

### Tools Available

1. **`list_csv_files`** - List all available Carelink CSV files
2. **`get_bg_readings`** - Get glucose readings for a specific day
   - `age=0` - Today
   - `age=1` - Yesterday  
   - `age=2` - 2 days ago, etc.
3. **`get_bg_readings_range`** - Get readings for a range of days

### Data Types

The server returns both:
- **BG Meter readings** - Traditional fingerstick readings
- **Sensor glucose** - Continuous glucose monitor readings

Most Carelink data contains sensor glucose readings from the CGM.

## Example Usage

### Test the server:
```bash
python3 carelink_csv_mcp_server.py --test
```

### Query yesterday's readings:
- Use the MCP tools to call `get_bg_readings` with `age=1`

### Query last week:
- Use `get_bg_readings_range` with `start_age=0, end_age=7`

## Data Format

The server reads Carelink CSV files from `carelink-python-client/data/` and parses:

- **Date/Time** information
- **BG Reading (mg/dL)** - Meter readings
- **Sensor Glucose (mg/dL)** - CGM readings
- **Metadata** about the device and patient

## CSV File Location

CSV files are automatically discovered in:
`./carelink-python-client/data/*.csv`

Download CSV files using:
```bash
cd carelink-python-client
python3 carelink_client2_cli.py --csv --verbose
```

## Sample Output

```json
{
  "date": "2026/08/17",
  "time": "07:09:24", 
  "sensor_glucose": "114",
  "reading_type": "sensor"
}
```

The `reading_type` can be:
- `"sensor"` - Only sensor glucose available
- `"bg_meter"` - Only BG meter reading available  
- `"both"` - Both sensor and meter readings available