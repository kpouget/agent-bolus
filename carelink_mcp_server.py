#!/usr/bin/env python3
"""
Carelink MCP Server - Direct interaction with Carelink API

This MCP server allows downloading CSV data directly from Carelink
and returns file paths for programmatic access.
"""
import json
import sys
import os
import datetime
from typing import Dict, Any

# Add the carelink-python-client directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "carelink-python-client"))

try:
    import carelink_client2
except ImportError as e:
    print(f"Error importing carelink_client2: {e}")
    sys.exit(1)


class CarelinkMcpServer:
    def __init__(self):
        self.name = "carelink_api"
        self.version = "1.0.0"

    def download_csv_data(self, days: int = 14) -> Dict[str, Any]:
        """
        Download CSV data from Carelink for the specified number of days

        Args:
            days (int): Number of days to download (default: 14)

        Returns:
            dict: Result with file_path, status, and metadata
        """
        try:
            # Change to carelink-python-client directory where logindata.json is located
            original_cwd = os.getcwd()
            carelink_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client")
            os.chdir(carelink_dir)

            # Create client instance
            client = carelink_client2.CareLinkClient()

            try:
                # Initialize client
                if not client.init():
                    return {
                        "success": False,
                        "error": f"Failed to initialize Carelink client (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Generate and download CSV report
                csv_data = client.generateAndDownloadCsvReport(days_back=days)

                if csv_data is None:
                    return {
                        "success": False,
                        "error": f"Failed to download CSV data (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                if not isinstance(csv_data, str):
                    return {
                        "success": False,
                        "error": "Downloaded data is not in CSV format",
                        "data_type": str(type(csv_data))
                    }

                # Create data directory if it doesn't exist (relative to carelink dir)
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)

                # Generate filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"csv_report_{days}days-{timestamp}.csv"
                filepath = os.path.join(data_dir, filename)

                # Save CSV data
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(csv_data)

                # Get absolute path for return
                abs_filepath = os.path.abspath(filepath)

                # Get file statistics
                file_size = len(csv_data)
                line_count = csv_data.count('\n')

                return {
                    "success": True,
                    "file_path": abs_filepath,
                    "filename": filename,
                    "days_requested": days,
                    "file_size": file_size,
                    "line_count": line_count,
                    "timestamp": timestamp,
                    "data_directory": os.path.abspath(data_dir)
                }

            finally:
                # Always change back to original directory
                os.chdir(original_cwd)

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during CSV download: {str(e)}",
                "exception_type": type(e).__name__
            }

    def get_user_info(self) -> Dict[str, Any]:
        """Get information about the authenticated Carelink user"""
        try:
            # Change to carelink-python-client directory where logindata.json is located
            original_cwd = os.getcwd()
            carelink_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client")
            os.chdir(carelink_dir)

            try:
                # Create client instance
                client = carelink_client2.CareLinkClient()

                # Initialize client
                if not client.init():
                    return {
                        "success": False,
                        "error": f"Failed to initialize Carelink client (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Get user info (this is printed by the client, we need to capture it)
                # For now, just return basic success info
                return {
                    "success": True,
                    "message": "Client initialized successfully",
                    "client_version": client.getClientVersion()
                }

            finally:
                # Always change back to original directory
                os.chdir(original_cwd)

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception getting user info: {str(e)}",
                "exception_type": type(e).__name__
            }

    def get_recent_data(self) -> Dict[str, Any]:
        """Get recent JSON data from Carelink (mobile API)"""
        try:
            # Change to carelink-python-client directory where logindata.json is located
            original_cwd = os.getcwd()
            carelink_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client")
            os.chdir(carelink_dir)

            try:
                # Create client instance
                client = carelink_client2.CareLinkClient()

                # Initialize client
                if not client.init():
                    return {
                        "success": False,
                        "error": f"Failed to initialize Carelink client (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Get recent data
                recent_data = client.getRecentData()

                if recent_data is None:
                    return {
                        "success": False,
                        "error": f"Failed to get recent data (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Save JSON data to file for reference (relative to carelink dir)
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recent_data-{timestamp}.json"
                filepath = os.path.join(data_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(recent_data, f, indent=2)

                # Get absolute path for return
                abs_filepath = os.path.abspath(filepath)

                return {
                    "success": True,
                    "file_path": abs_filepath,
                    "filename": filename,
                    "data": recent_data,
                    "timestamp": timestamp,
                    "data_size": len(str(recent_data))
                }

            finally:
                # Always change back to original directory
                os.chdir(original_cwd)

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception getting recent data: {str(e)}",
                "exception_type": type(e).__name__
            }

    def get_web_data(self) -> Dict[str, Any]:
        """Get summary JSON data from Carelink web interface (personalWebView endpoint)"""
        try:
            # Change to carelink-python-client directory where logindata.json is located
            original_cwd = os.getcwd()
            carelink_dir = os.path.join(os.path.dirname(__file__), "carelink-python-client")
            os.chdir(carelink_dir)

            try:
                # Create client instance
                client = carelink_client2.CareLinkClient()

                # Initialize client
                if not client.init():
                    return {
                        "success": False,
                        "error": f"Failed to initialize Carelink client (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Get web interface data
                web_data = client.getWebData()

                if web_data is None:
                    return {
                        "success": False,
                        "error": f"Failed to get web data (response code {client.getLastResponseCode()})",
                        "response_code": client.getLastResponseCode()
                    }

                # Save JSON data to file for reference (relative to carelink dir)
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"web_data-{timestamp}.json"
                filepath = os.path.join(data_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(web_data, f, indent=2)

                # Get absolute path for return
                abs_filepath = os.path.abspath(filepath)

                # Analyze the data to provide summary info
                summary_info = self._analyze_web_data(web_data)

                return {
                    "success": True,
                    "file_path": abs_filepath,
                    "filename": filename,
                    "data": web_data,
                    "timestamp": timestamp,
                    "data_size": len(str(web_data)),
                    "summary": summary_info
                }

            finally:
                # Always change back to original directory
                os.chdir(original_cwd)

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception getting web data: {str(e)}",
                "exception_type": type(e).__name__
            }

    def _analyze_web_data(self, web_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze web data to provide summary information"""
        summary = {
            "data_keys": list(web_data.keys()) if isinstance(web_data, dict) else [],
            "total_keys": len(web_data) if isinstance(web_data, dict) else 0
        }

        if isinstance(web_data, dict):
            # Look for common data arrays and analyze them
            for key in ['sgs', 'markers', 'readings', 'events', 'data', 'sensorGlucose']:
                if key in web_data and isinstance(web_data[key], list):
                    summary[f"{key}_count"] = len(web_data[key])
                    if web_data[key]:  # If list is not empty
                        # Try to find date range
                        dates = []
                        for entry in web_data[key][:5]:  # Check first 5 entries
                            if isinstance(entry, dict):
                                for date_field in ['datetime', 'timestamp', 'date', 'time']:
                                    if date_field in entry:
                                        dates.append(entry[date_field])
                                        break
                        if dates:
                            summary[f"{key}_sample_dates"] = dates[:3]

            # Check for metadata
            if 'lastSensorTSAsString' in web_data:
                summary['last_sensor_timestamp'] = web_data['lastSensorTSAsString']

        return summary


def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests"""
    server = CarelinkMcpServer()

    method = request.get("method", "")
    params = request.get("params", {})

    try:
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "download_csv",
                        "description": "Download CSV data from Carelink for the specified number of days and return file path",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "days": {
                                    "type": "integer",
                                    "description": "Number of days to download (default: 14)",
                                    "default": 14,
                                    "minimum": 1,
                                    "maximum": 90
                                }
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "get_user_info",
                        "description": "Get information about the authenticated Carelink user",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "get_recent_data",
                        "description": "Get recent JSON data from Carelink mobile API (2-3 days)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "get_web_data",
                        "description": "Get summary JSON data from Carelink web interface (personalWebView endpoint) - may contain more historical data than mobile API",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name == "download_csv":
                days = arguments.get("days", 14)

                # Validate days parameter
                if not isinstance(days, int) or days < 1 or days > 90:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: days must be an integer between 1 and 90, got: {days}"
                            }
                        ]
                    }

                result = server.download_csv_data(days)

                if result["success"]:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"✅ CSV data downloaded successfully!\n\n" +
                                       f"📁 File path: {result['file_path']}\n" +
                                       f"📊 Days: {result['days_requested']}\n" +
                                       f"📏 Size: {result['file_size']} characters\n" +
                                       f"📄 Lines: {result['line_count']}\n" +
                                       f"🕐 Timestamp: {result['timestamp']}\n\n" +
                                       f"File saved to: {result['filename']}"
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Failed to download CSV data:\n{result.get('error', 'Unknown error')}"
                            }
                        ]
                    }

            elif tool_name == "get_user_info":
                result = server.get_user_info()

                if result["success"]:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"✅ Carelink client initialized successfully\n" +
                                       f"📚 Client version: {result.get('client_version', 'Unknown')}\n" +
                                       f"💬 {result.get('message', 'Ready to download data')}"
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Failed to get user info:\n{result.get('error', 'Unknown error')}"
                            }
                        ]
                    }

            elif tool_name == "get_recent_data":
                result = server.get_recent_data()

                if result["success"]:
                    data_preview = str(result.get('data', {}))[:200]
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"✅ Recent data downloaded successfully!\n\n" +
                                       f"📁 File path: {result['file_path']}\n" +
                                       f"📊 Data size: {result['data_size']} characters\n" +
                                       f"🕐 Timestamp: {result['timestamp']}\n\n" +
                                       f"Data preview: {data_preview}..."
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Failed to get recent data:\n{result.get('error', 'Unknown error')}"
                            }
                        ]
                    }

            elif tool_name == "get_web_data":
                result = server.get_web_data()

                if result["success"]:
                    summary = result.get('summary', {})
                    data_preview = str(result.get('data', {}))[:200]

                    # Build summary text
                    summary_text = ""
                    if summary.get('data_keys'):
                        summary_text += f"📋 Data keys: {', '.join(summary['data_keys'][:5])}\n"

                    for key in ['sgs', 'markers', 'readings', 'events', 'sensorGlucose']:
                        count_key = f"{key}_count"
                        if count_key in summary:
                            summary_text += f"📊 {key}: {summary[count_key]} entries\n"
                            dates_key = f"{key}_sample_dates"
                            if dates_key in summary:
                                summary_text += f"   Sample dates: {summary[dates_key]}\n"

                    if summary.get('last_sensor_timestamp'):
                        summary_text += f"⏰ Last sensor: {summary['last_sensor_timestamp']}\n"

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"✅ Web interface data downloaded successfully!\n\n" +
                                       f"📁 File path: {result['file_path']}\n" +
                                       f"📊 Data size: {result['data_size']} characters\n" +
                                       f"🕐 Timestamp: {result['timestamp']}\n\n" +
                                       f"📈 Data Summary:\n{summary_text}\n" +
                                       f"Data preview: {data_preview}..."
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Failed to get web data:\n{result.get('error', 'Unknown error')}"
                            }
                        ]
                    }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        else:
            return {"error": f"Unknown method: {method}"}

    except Exception as e:
        return {"error": f"Server error: {str(e)}"}


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
        server = CarelinkMcpServer()

        print("Testing Carelink MCP Server...")

        # Test user info
        print("\n1. Testing user info...")
        result = server.get_user_info()
        print(f"User info result: {result}")

        if result.get("success"):
            # Test web data
            print("\n2. Testing web data...")
            result = server.get_web_data()
            print(f"Web data result: {result}")

            if result.get("success"):
                print(f"✅ Web data test successful! File saved to: {result['file_path']}")
                summary = result.get('summary', {})
                print(f"Data summary: {summary}")

                # Test CSV download
                print("\n3. Testing CSV download (7 days)...")
                result = server.download_csv_data(7)
                print(f"CSV download result: {result}")

                if result.get("success"):
                    print(f"✅ CSV test successful! File saved to: {result['file_path']}")
                else:
                    print(f"❌ CSV download failed: {result.get('error')}")
            else:
                print(f"❌ Web data failed: {result.get('error')}")
        else:
            print(f"❌ User info failed: {result.get('error')}")
    else:
        main()