#!/usr/bin/env python3
"""
Carelink Data MCP Server - Explore Carelink CSV files and web data

This MCP server allows querying BG readings from Carelink CSV files by age (days ago)
and querying aggregated data from web interface JSON files.
"""
import csv
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import glob
import os


class CarelinkDataServer:
    def __init__(self):
        self.name = "carelink_data"
        self.version = "1.0.0"

    def find_csv_files(self) -> List[str]:
        """Find all CSV files in the main project data directory"""
        # Look in main project data directory first
        main_data_dir = os.path.join(os.path.dirname(__file__), "data")
        csv_files = []

        if os.path.exists(main_data_dir):
            csv_files.extend(glob.glob(os.path.join(main_data_dir, "*.csv")))

        # Also check the old location for backward compatibility
        old_data_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client", "data")
        if os.path.exists(old_data_dir):
            csv_files.extend(glob.glob(os.path.join(old_data_dir, "*.csv")))

        return csv_files

    def find_web_data_files(self) -> List[str]:
        """Find all web data JSON files in the data directory"""
        main_data_dir = os.path.join(os.path.dirname(__file__), "data")
        web_files = []

        if os.path.exists(main_data_dir):
            web_files.extend(glob.glob(os.path.join(main_data_dir, "web_data-*.json")))
            web_files.extend(glob.glob(os.path.join(main_data_dir, "webdata-*.json")))

        # Also check the old location for backward compatibility
        old_data_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client", "data")
        if os.path.exists(old_data_dir):
            web_files.extend(glob.glob(os.path.join(old_data_dir, "webdata-*.json")))
            web_files.extend(glob.glob(os.path.join(old_data_dir, "web_data-*.json")))

        return sorted(web_files, key=os.path.getmtime, reverse=True)  # Most recent first

    def query_web_aggregated_data(self, aggreg: int, age: int, field: str, filepath: str = None) -> Dict[str, Any]:
        """
        Query aggregated data from web interface JSON files

        Args:
            aggreg: Aggregation period (1, 7, 14, or 30 days)
            age: Age in days (0 = today, 1 = yesterday, etc.)
            field: Data field ('tir', 'sensorUsage', or 'sg')
            filepath: Optional specific file path, otherwise uses most recent

        Returns:
            dict: Query result with data or error
        """
        try:
            # Validate parameters
            if aggreg not in [1, 7, 14, 30]:
                return {"success": False, "error": f"Invalid aggreg value: {aggreg}. Must be 1, 7, 14, or 30"}

            if field not in ['tir', 'sensorUsage', 'sg']:
                return {"success": False, "error": f"Invalid field: {field}. Must be 'tir', 'sensorUsage', or 'sg'"}

            if age < 0:
                return {"success": False, "error": f"Invalid age: {age}. Must be >= 0"}

            # Find web data file
            if filepath is None:
                web_files = self.find_web_data_files()
                if not web_files:
                    return {"success": False, "error": "No web data files found"}
                filepath = web_files[0]  # Most recent

            if not os.path.exists(filepath):
                return {"success": False, "error": f"File not found: {filepath}"}

            # Load JSON data
            with open(filepath, 'r', encoding='utf-8') as f:
                web_data = json.load(f)

            # Navigate to the requested data path: .ResponsePayload.mgdl.Agg{aggreg}d[{age}].{field}
            try:
                # Start with the base path
                if 'ResponsePayload' not in web_data:
                    return {"success": False, "error": "ResponsePayload not found in web data"}

                payload = web_data['ResponsePayload']

                if 'mgdl' not in payload:
                    return {"success": False, "error": "mgdl not found in ResponsePayload"}

                mgdl_data = payload['mgdl']

                # Build aggregation key (e.g., "Agg1d", "Agg7d", etc.)
                agg_key = f"Agg{aggreg}d"
                if agg_key not in mgdl_data:
                    available_keys = list(mgdl_data.keys())
                    return {"success": False, "error": f"{agg_key} not found in mgdl data. Available keys: {available_keys}"}

                agg_data = mgdl_data[agg_key]

                # Check if it's an array and access by age index
                if isinstance(agg_data, list):
                    if age >= len(agg_data):
                        return {"success": False, "error": f"Age index {age} out of range. Array has {len(agg_data)} elements"}

                    age_data = agg_data[age]
                else:
                    return {"success": False, "error": f"{agg_key} is not an array, found: {type(agg_data)}"}

                # Access the requested field
                if not isinstance(age_data, dict) or field not in age_data:
                    available_fields = list(age_data.keys()) if isinstance(age_data, dict) else []
                    return {"success": False, "error": f"Field '{field}' not found in age data. Available fields: {available_fields}"}

                result_data = age_data[field]

                return {
                    "success": True,
                    "data": result_data,
                    "query_path": f"ResponsePayload.mgdl.{agg_key}[{age}].{field}",
                    "aggreg": aggreg,
                    "age": age,
                    "field": field,
                    "filepath": filepath,
                    "filename": os.path.basename(filepath)
                }

            except (KeyError, TypeError, IndexError) as e:
                return {"success": False, "error": f"Failed to navigate data path: {str(e)}"}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in file {filepath}: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def parse_carelink_csv(self, filepath: str) -> Dict[str, Any]:
        """Parse a Carelink CSV file and extract metadata and data"""
        result = {
            "metadata": {},
            "data": [],
            "columns": []
        }

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Find the data header line (starts with "Index;Date;Time;...")
            data_start_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("Index;Date;Time;"):
                    data_start_idx = i
                    result["columns"] = [col.strip() for col in line.strip().split(';')]
                    break

            if data_start_idx == -1:
                raise ValueError("Could not find data header in CSV file")

            # Extract metadata from header lines
            for i in range(min(5, data_start_idx)):
                line = lines[i].strip()
                if line and not line.startswith('-'):
                    # Parse metadata lines
                    parts = [p.strip('"').strip() for p in line.split(';')]
                    if len(parts) >= 2:
                        result["metadata"][f"line_{i}"] = parts

            # Parse data rows
            for line in lines[data_start_idx + 1:]:
                line = line.strip()
                if line and not line.startswith('-'):
                    row_data = [col.strip('"').strip() for col in line.split(';')]
                    if len(row_data) >= len(result["columns"]):
                        # Create a dictionary mapping column names to values
                        row_dict = {}
                        for j, col_name in enumerate(result["columns"]):
                            if j < len(row_data):
                                row_dict[col_name] = row_data[j]
                        result["data"].append(row_dict)

            return result

        except Exception as e:
            raise Exception(f"Error parsing CSV file {filepath}: {str(e)}")

    def get_bg_readings_by_age(self, filepath: str, age_days: int = 0) -> List[Dict[str, Any]]:
        """Get BG readings and sensor glucose for a specific age (days ago)"""
        csv_data = self.parse_carelink_csv(filepath)

        # Calculate target date
        target_date = datetime.now() - timedelta(days=age_days)
        target_date_str = target_date.strftime("%Y/%m/%d")

        # Filter readings for the target date
        readings = []
        for row in csv_data["data"]:
            row_date = row.get("Date", "")
            bg_reading = row.get("BG Reading (mg/dL)", "").strip()
            sensor_glucose = row.get("Sensor Glucose (mg/dL)", "").strip()

            # Check if this row matches our target date and has either BG reading or sensor glucose
            if row_date == target_date_str and (bg_reading or sensor_glucose):
                reading_data = {
                    "date": row_date,
                    "time": row.get("Time", ""),
                    "index": row.get("Index", ""),
                    "bg_source": row.get("BG Source", "")
                }

                # Add BG reading if available
                if bg_reading:
                    reading_data["bg_reading"] = bg_reading
                    reading_data["reading_type"] = "bg_meter"

                # Add sensor glucose if available
                if sensor_glucose:
                    reading_data["sensor_glucose"] = sensor_glucose
                    if not bg_reading:
                        reading_data["reading_type"] = "sensor"

                # If both are available
                if bg_reading and sensor_glucose:
                    reading_data["reading_type"] = "both"

                readings.append(reading_data)

        return readings

    def get_bg_readings_range(self, filepath: str, start_age: int = 0, end_age: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get BG readings for a range of days"""
        result = {}
        for age in range(start_age, end_age + 1):
            date_key = f"age_{age}"
            if age == 0:
                date_key += "_today"
            elif age == 1:
                date_key += "_yesterday"

            readings = self.get_bg_readings_by_age(filepath, age)
            if readings:
                result[date_key] = readings

        return result

    def list_available_files(self) -> List[Dict[str, Any]]:
        """List available CSV files with metadata"""
        files = self.find_csv_files()
        result = []

        for filepath in files:
            try:
                csv_data = self.parse_carelink_csv(filepath)

                # Extract basic metadata
                metadata = csv_data["metadata"]
                file_info = {
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "size": os.path.getsize(filepath),
                    "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    "data_rows": len(csv_data["data"]),
                    "columns": len(csv_data["columns"])
                }

                # Try to extract patient info and date range
                for line_key, line_data in metadata.items():
                    if len(line_data) >= 6:
                        if "Start Date" in line_data and "End Date" in line_data:
                            start_idx = line_data.index("Start Date")
                            end_idx = line_data.index("End Date")
                            if start_idx + 1 < len(line_data):
                                file_info["start_date"] = line_data[start_idx + 1]
                            if end_idx + 1 < len(line_data):
                                file_info["end_date"] = line_data[end_idx + 1]

                result.append(file_info)

            except Exception as e:
                result.append({
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "error": str(e)
                })

        return result


def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests"""
    server = CarelinkDataServer()

    method = request.get("method", "")
    params = request.get("params", {})

    try:
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "list_csv_files",
                        "description": "List available Carelink CSV files",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "get_bg_readings",
                        "description": "Get BG readings and sensor glucose values for specific age (days ago). age=0 is today, age=1 is yesterday, etc. Returns both meter BG readings and continuous glucose sensor readings.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "filepath": {
                                    "type": "string",
                                    "description": "Path to the CSV file"
                                },
                                "age": {
                                    "type": "integer",
                                    "description": "Age in days (0=today, 1=yesterday, etc)",
                                    "default": 0
                                }
                            },
                            "required": ["filepath"]
                        }
                    },
                    {
                        "name": "get_bg_readings_range",
                        "description": "Get BG readings and sensor glucose values for a range of days",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "filepath": {
                                    "type": "string",
                                    "description": "Path to the CSV file"
                                },
                                "start_age": {
                                    "type": "integer",
                                    "description": "Start age in days (default 0=today)",
                                    "default": 0
                                },
                                "end_age": {
                                    "type": "integer",
                                    "description": "End age in days (default 7=week ago)",
                                    "default": 7
                                }
                            },
                            "required": ["filepath"]
                        }
                    },
                    {
                        "name": "query_web_data",
                        "description": "Query aggregated data from web interface JSON files using path: ResponsePayload.mgdl.Agg{aggreg}d[{age}].{field}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "aggreg": {
                                    "type": "integer",
                                    "description": "Aggregation period in days",
                                    "enum": [1, 7, 14, 30]
                                },
                                "age": {
                                    "type": "integer",
                                    "description": "Age in days (0=today, 1=yesterday, etc)",
                                    "minimum": 0
                                },
                                "field": {
                                    "type": "string",
                                    "description": "Data field to query",
                                    "enum": ["tir", "sensorUsage", "sg"]
                                },
                                "filepath": {
                                    "type": "string",
                                    "description": "Optional specific file path, otherwise uses most recent web data file"
                                }
                            },
                            "required": ["aggreg", "age", "field"]
                        }
                    }
                ]
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name == "list_csv_files":
                files = server.list_available_files()
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(files)} CSV files:\n" + json.dumps(files, indent=2)
                        }
                    ]
                }

            elif tool_name == "get_bg_readings":
                filepath = arguments.get("filepath", "")
                age = arguments.get("age", 0)

                if not filepath:
                    # Try to find the most recent CSV file
                    files = server.find_csv_files()
                    if files:
                        filepath = max(files, key=os.path.getmtime)
                    else:
                        return {"error": "No CSV files found and no filepath provided"}

                readings = server.get_bg_readings_by_age(filepath, age)

                age_desc = "today" if age == 0 else f"{age} day{'s' if age > 1 else ''} ago"

                # Count different types of readings
                bg_count = len([r for r in readings if r.get("bg_reading")])
                sensor_count = len([r for r in readings if r.get("sensor_glucose")])

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Glucose readings for {age_desc} (age={age}):\n" +
                                   f"Total readings: {len(readings)}\n" +
                                   f"BG meter readings: {bg_count}\n" +
                                   f"Sensor glucose readings: {sensor_count}\n\n" +
                                   json.dumps(readings, indent=2)
                        }
                    ]
                }

            elif tool_name == "get_bg_readings_range":
                filepath = arguments.get("filepath", "")
                start_age = arguments.get("start_age", 0)
                end_age = arguments.get("end_age", 7)

                if not filepath:
                    # Try to find the most recent CSV file
                    files = server.find_csv_files()
                    if files:
                        filepath = max(files, key=os.path.getmtime)
                    else:
                        return {"error": "No CSV files found and no filepath provided"}

                readings = server.get_bg_readings_range(filepath, start_age, end_age)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"BG readings from {start_age} to {end_age} days ago:\n" +
                                   json.dumps(readings, indent=2)
                        }
                    ]
                }

            elif tool_name == "query_web_data":
                aggreg = arguments.get("aggreg")
                age = arguments.get("age")
                field = arguments.get("field")
                filepath = arguments.get("filepath")

                result = server.query_web_aggregated_data(aggreg, age, field, filepath)

                if result["success"]:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"✅ Web data query successful!\n\n" +
                                       f"📊 Query: {result['query_path']}\n" +
                                       f"📁 File: {result['filename']}\n" +
                                       f"🔢 Aggregation: {result['aggreg']} days\n" +
                                       f"📅 Age: {result['age']} days ago\n" +
                                       f"🏷️ Field: {result['field']}\n\n" +
                                       f"📈 Result: {json.dumps(result['data'], indent=2)}"
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Web data query failed:\n{result.get('error', 'Unknown error')}"
                            }
                        ]
                    }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        else:
            return {"error": f"Unknown method: {method}"}

    except Exception as e:
        return {"error": str(e)}


def main():
    """Main MCP server loop"""
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line.strip())
                response = handle_mcp_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError:
                print(json.dumps({"error": "Invalid JSON"}))
                sys.stdout.flush()
            except Exception as e:
                print(json.dumps({"error": str(e)}))
                sys.stdout.flush()

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - run a quick test
        server = CarelinkDataServer()

        # Test CSV files
        files = server.find_csv_files()
        print(f"Found {len(files)} CSV files:")
        for f in files:
            print(f"  {f}")

        # Test web data files
        web_files = server.find_web_data_files()
        print(f"\nFound {len(web_files)} web data files:")
        for f in web_files:
            print(f"  {f}")

        if files:
            print(f"\nTesting CSV with most recent file: {files[-1]}")
            try:
                # Test yesterday (age=1)
                readings_yesterday = server.get_bg_readings_by_age(files[-1], 1)
                print(f"Glucose readings for yesterday (age=1): {len(readings_yesterday)}")
                if readings_yesterday:
                    print("Sample reading:", readings_yesterday[0])

            except Exception as e:
                print(f"CSV Error: {e}")

        if web_files:
            print(f"\nTesting web data query with most recent file: {web_files[0]}")
            try:
                # Test some common queries
                test_queries = [
                    (1, 1, "tir"),      # 1-day TIR for today
                    (7, 1, "sensorUsage"),  # 7-day sensor usage for this week
                    (14, 1, "sg"),      # 14-day glucose for last period
                ]

                for aggreg, age, field in test_queries:
                    result = server.query_web_aggregated_data(aggreg, age, field, web_files[0])
                    if result["success"]:
                        print(f"  Query {result['query_path']}: {result['data']}")
                    else:
                        print(f"  Query Agg{aggreg}d[{age}].{field}: {result['error']}")

            except Exception as e:
                print(f"Web data Error: {e}")
    else:
        main()
