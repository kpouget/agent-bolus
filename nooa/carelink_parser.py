#!/usr/bin/env python3
"""
Carelink CSV Data Parser
Parse real Carelink CSV files and extract glucose readings
"""
import csv
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from diabetes_agent import GlucoseReading

def parse_carelink_csv(filepath: str, days_back: int = 7) -> List[GlucoseReading]:
    """
    Parse Carelink CSV file and extract glucose readings from the last N days.

    Args:
        filepath: Path to the CSV file
        days_back: Number of days to look back from today

    Returns:
        List of GlucoseReading objects
    """
    readings = []

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days_back)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the data start line (contains "Index;Date;Time;...")
        data_start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Index;Date;Time;"):
                data_start_idx = i
                # Get column headers
                headers = [col.strip() for col in line.strip().split(';')]
                break

        if data_start_idx == -1:
            raise ValueError("Could not find data header in CSV file")

        # Find column indices
        date_idx = headers.index("Date") if "Date" in headers else 1
        time_idx = headers.index("Time") if "Time" in headers else 2
        bg_reading_idx = headers.index("BG Reading (mg/dL)") if "BG Reading (mg/dL)" in headers else 5
        sensor_glucose_idx = headers.index("Sensor Glucose (mg/dL)") if "Sensor Glucose (mg/dL)" in headers else 33

        print(f"📊 Parsing CSV: Date col={date_idx}, Time col={time_idx}, BG col={bg_reading_idx}, Sensor col={sensor_glucose_idx}")

        # Parse data rows
        for line in lines[data_start_idx + 1:]:
            line = line.strip()
            if not line or line.startswith('-'):
                continue

            # Split by semicolon and clean up values
            row_data = [col.strip().strip('"') for col in line.split(';')]

            if len(row_data) <= max(date_idx, time_idx, bg_reading_idx, sensor_glucose_idx):
                continue

            # Extract date and time
            date_str = row_data[date_idx]
            time_str = row_data[time_idx]

            if not date_str or not time_str:
                continue

            try:
                # Parse date (format: 2026/09/11)
                entry_date = datetime.strptime(date_str, "%Y/%m/%d")

                # Skip if too old
                if entry_date < cutoff_date:
                    continue

                # Create timestamp string
                timestamp = f"{date_str} {time_str}"

                # Extract BG reading
                bg_value = row_data[bg_reading_idx] if bg_reading_idx < len(row_data) else ""
                if bg_value and bg_value.replace(',', '.').replace('.', '').isdigit():
                    # Convert comma decimal to dot and parse
                    bg_float = float(bg_value.replace(',', '.'))
                    if bg_float > 0:  # Valid reading
                        readings.append(GlucoseReading(
                            timestamp=timestamp,
                            value=int(bg_float),
                            type="bg_meter"
                        ))

                # Extract sensor glucose
                sensor_value = row_data[sensor_glucose_idx] if sensor_glucose_idx < len(row_data) else ""
                if sensor_value and sensor_value.replace(',', '.').replace('.', '').isdigit():
                    # Convert comma decimal to dot and parse
                    sensor_float = float(sensor_value.replace(',', '.'))
                    if sensor_float > 0:  # Valid reading
                        readings.append(GlucoseReading(
                            timestamp=timestamp,
                            value=int(sensor_float),
                            type="sensor"
                        ))

            except ValueError as e:
                # Skip rows with parsing errors
                continue

    except Exception as e:
        print(f"❌ Error parsing CSV file: {e}")
        return []

    # Sort by timestamp (oldest first, so most recent end up at end of agent.readings list)
    readings.sort(key=lambda x: datetime.strptime(x.timestamp.split()[0], "%Y/%m/%d"), reverse=False)

    print(f"✅ Parsed {len(readings)} glucose readings from last {days_back} days")

    return readings

def load_latest_csv_file(data_dir: str = "data") -> Optional[str]:
    """Find the most recent CSV file in the data directory."""
    import glob

    csv_files = glob.glob(os.path.join(data_dir, "csv_report_*.csv"))
    if not csv_files:
        return None

    # Sort by modification time, most recent first
    csv_files.sort(key=os.path.getmtime, reverse=True)
    return csv_files[0]

def get_date_range_from_readings(readings: List[GlucoseReading]) -> Tuple[str, str]:
    """Get date range from readings list."""
    if not readings:
        return "No data", "No data"

    dates = [r.timestamp.split()[0] for r in readings]
    return min(dates), max(dates)

def summarize_readings(readings: List[GlucoseReading]) -> dict:
    """Create summary statistics from readings."""
    if not readings:
        return {"error": "No readings found"}

    values = [r.value for r in readings]
    sensor_readings = [r for r in readings if r.type == "sensor"]
    meter_readings = [r for r in readings if r.type == "bg_meter"]

    start_date, end_date = get_date_range_from_readings(readings)

    return {
        "total_readings": len(readings),
        "sensor_readings": len(sensor_readings),
        "meter_readings": len(meter_readings),
        "date_range": f"{end_date} to {start_date}",
        "avg_glucose": sum(values) / len(values),
        "min_glucose": min(values),
        "max_glucose": max(values),
        "readings_per_day": len(readings) / 7.0  # Assuming 7 days
    }

# Test function
def test_parser():
    """Test the CSV parser with hardcoded file."""
    filepath = "data/csv_report_30days-20260911_102845.csv"

    print(f"🧪 Testing parser with {filepath}")

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    readings = parse_carelink_csv(filepath, days_back=7)
    summary = summarize_readings(readings)

    print("\n📊 Parsing Results:")
    for key, value in summary.items():
        print(f"   {key}: {value}")

    if readings:
        print(f"\n📋 Sample readings:")
        for i, reading in enumerate(readings[:5]):
            print(f"   {i+1}. {reading.timestamp} - {reading.value} mg/dL ({reading.type})")

    return readings

if __name__ == "__main__":
    test_parser()