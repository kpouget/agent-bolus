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
from dataclasses import dataclass
from typing import Dict

@dataclass
class BolusEvent:
    """A bolus event with carbs and insulin delivery."""
    timestamp: str
    carb_input: float  # grams
    insulin_delivered: float  # units
    date: str
    time: str

    # Bolus Wizard (BWZ) calculation data
    carb_ratio: Optional[float] = None  # BWZ Carb Ratio (g/U) - grams carb per unit insulin
    food_estimate: Optional[float] = None  # BWZ Food Estimate (U) - insulin for carbs
    correction_estimate: Optional[float] = None  # BWZ Correction Estimate (U) - insulin for BG correction
    bg_input: Optional[int] = None  # BWZ BG/SG Input (mg/dL) - BG reading used
    active_insulin: Optional[float] = None  # BWZ Active Insulin (U) - insulin on board
    final_estimate: Optional[float] = None  # Final Bolus Estimate - total calculated


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

def parse_bolus_events(filepath: str, days_back: int = 7) -> List[BolusEvent]:
    """
    Parse Carelink CSV file and extract bolus events with carb input from the last N days.
    Note: Carelink logs carbs and insulin in separate rows, so we need to match them.

    Args:
        filepath: Path to the CSV file
        days_back: Number of days to look back from today

    Returns:
        List of BolusEvent objects
    """
    bolus_events = []
    carb_entries = {}  # Store carb entries with BWZ data by timestamp
    insulin_entries = {}  # Store insulin entries by timestamp

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days_back)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the data start line
        data_start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Index;Date;Time;"):
                data_start_idx = i
                headers = [col.strip() for col in line.strip().split(';')]
                break

        if data_start_idx == -1:
            raise ValueError("Could not find data header in CSV file")

        # Find column indices
        date_idx = headers.index("Date") if "Date" in headers else 1
        time_idx = headers.index("Time") if "Time" in headers else 2
        carb_input_idx = headers.index("BWZ Carb Input (grams)") if "BWZ Carb Input (grams)" in headers else -1
        bolus_delivered_idx = headers.index("Bolus Volume Delivered (U)") if "Bolus Volume Delivered (U)" in headers else -1

        # BWZ calculation fields
        carb_ratio_idx = headers.index("BWZ Carb Ratio (g/U)") if "BWZ Carb Ratio (g/U)" in headers else -1
        food_estimate_idx = headers.index("BWZ Food Estimate (U)") if "BWZ Food Estimate (U)" in headers else -1
        correction_estimate_idx = headers.index("BWZ Correction Estimate (U)") if "BWZ Correction Estimate (U)" in headers else -1
        bg_input_idx = headers.index("BWZ BG/SG Input (mg/dL)") if "BWZ BG/SG Input (mg/dL)" in headers else -1
        active_insulin_idx = headers.index("BWZ Active Insulin (U)") if "BWZ Active Insulin (U)" in headers else -1
        final_estimate_idx = headers.index("Final Bolus Estimate") if "Final Bolus Estimate" in headers else -1

        if carb_input_idx == -1 or bolus_delivered_idx == -1:
            print(f"❌ Could not find bolus columns in CSV")
            return []

        print(f"📊 Parsing Bolus: Date col={date_idx}, Time col={time_idx}, Carbs col={carb_input_idx}, Insulin col={bolus_delivered_idx}")
        print(f"📊 BWZ Columns: Ratio col={carb_ratio_idx}, Food col={food_estimate_idx}, Correction col={correction_estimate_idx}")

        # First pass: collect carb and insulin entries separately
        for line in lines[data_start_idx + 1:]:
            line = line.strip()
            if not line or line.startswith('-'):
                continue

            row_data = [col.strip().strip('"') for col in line.split(';')]

            if len(row_data) <= max(date_idx, time_idx, carb_input_idx, bolus_delivered_idx):
                continue

            date_str = row_data[date_idx]
            time_str = row_data[time_idx]

            if not date_str or not time_str:
                continue

            try:
                entry_date = datetime.strptime(date_str, "%Y/%m/%d")
                if entry_date < cutoff_date:
                    continue

                timestamp = f"{date_str} {time_str}"

                # Check for carb input and collect BWZ data
                carb_value = row_data[carb_input_idx] if carb_input_idx < len(row_data) else ""
                if carb_value:
                    try:
                        carb_float = float(carb_value.replace(',', '.'))
                        if carb_float > 0:
                            # Create carb entry with BWZ calculation data
                            carb_data = {
                                'carb_amount': carb_float,
                                'carb_ratio': None,
                                'food_estimate': None,
                                'correction_estimate': None,
                                'bg_input': None,
                                'active_insulin': None,
                                'final_estimate': None
                            }

                            # Extract BWZ fields if available
                            if carb_ratio_idx != -1 and carb_ratio_idx < len(row_data):
                                ratio_val = row_data[carb_ratio_idx].strip()
                                if ratio_val:
                                    try:
                                        carb_data['carb_ratio'] = float(ratio_val.replace(',', '.'))
                                    except ValueError:
                                        pass

                            if food_estimate_idx != -1 and food_estimate_idx < len(row_data):
                                food_val = row_data[food_estimate_idx].strip()
                                if food_val:
                                    try:
                                        carb_data['food_estimate'] = float(food_val.replace(',', '.'))
                                    except ValueError:
                                        pass

                            if correction_estimate_idx != -1 and correction_estimate_idx < len(row_data):
                                corr_val = row_data[correction_estimate_idx].strip()
                                if corr_val:
                                    try:
                                        carb_data['correction_estimate'] = float(corr_val.replace(',', '.'))
                                    except ValueError:
                                        pass

                            if bg_input_idx != -1 and bg_input_idx < len(row_data):
                                bg_val = row_data[bg_input_idx].strip()
                                if bg_val:
                                    try:
                                        carb_data['bg_input'] = int(float(bg_val.replace(',', '.')))
                                    except ValueError:
                                        pass

                            if active_insulin_idx != -1 and active_insulin_idx < len(row_data):
                                active_val = row_data[active_insulin_idx].strip()
                                if active_val:
                                    try:
                                        carb_data['active_insulin'] = float(active_val.replace(',', '.'))
                                    except ValueError:
                                        pass

                            if final_estimate_idx != -1 and final_estimate_idx < len(row_data):
                                final_val = row_data[final_estimate_idx].strip()
                                if final_val:
                                    try:
                                        carb_data['final_estimate'] = float(final_val.replace(',', '.'))
                                    except ValueError:
                                        pass

                            carb_entries[timestamp] = carb_data
                    except ValueError:
                        pass

                # Check for insulin delivery
                insulin_value = row_data[bolus_delivered_idx] if bolus_delivered_idx < len(row_data) else ""
                if insulin_value:
                    try:
                        insulin_float = float(insulin_value.replace(',', '.'))
                        if insulin_float > 0:
                            insulin_entries[timestamp] = insulin_float
                    except ValueError:
                        pass

            except ValueError:
                continue

        # Second pass: match carb entries with nearby insulin entries (within ~5 minutes)
        for carb_timestamp, carb_data in carb_entries.items():
            carb_time = datetime.strptime(carb_timestamp, "%Y/%m/%d %H:%M:%S")

            # Look for insulin delivery within 5 minutes (before or after)
            insulin_amount = None
            insulin_timestamp = None

            for ins_timestamp, ins_amount in insulin_entries.items():
                ins_time = datetime.strptime(ins_timestamp, "%Y/%m/%d %H:%M:%S")
                time_diff = abs((carb_time - ins_time).total_seconds())

                if time_diff <= 300:  # Within 5 minutes
                    insulin_amount = ins_amount
                    insulin_timestamp = ins_timestamp
                    break

            if insulin_amount:
                # Use the carb timestamp for the bolus event
                date_str, time_str = carb_timestamp.split(' ', 1)
                bolus_events.append(BolusEvent(
                    timestamp=carb_timestamp,
                    carb_input=carb_data['carb_amount'],
                    insulin_delivered=insulin_amount,
                    date=date_str,
                    time=time_str,
                    # BWZ calculation data
                    carb_ratio=carb_data['carb_ratio'],
                    food_estimate=carb_data['food_estimate'],
                    correction_estimate=carb_data['correction_estimate'],
                    bg_input=carb_data['bg_input'],
                    active_insulin=carb_data['active_insulin'],
                    final_estimate=carb_data['final_estimate']
                ))

    except Exception as e:
        print(f"❌ Error parsing bolus events from CSV file: {e}")
        return []

    # Sort by timestamp (oldest first)
    bolus_events.sort(key=lambda x: datetime.strptime(x.date, "%Y/%m/%d"))

    print(f"✅ Parsed {len(bolus_events)} bolus events from last {days_back} days")

    return bolus_events

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

def extract_bg_for_periods(filepath: str, organized_bolus_data: Dict[str, Dict[str, List[BolusEvent]]]) -> Dict[str, Dict[str, List[GlucoseReading]]]:
    """
    Extract BG sensor readings for each period/day based on bolus timing.

    For each period on each day:
    - Start: first bolus time of the period
    - End: 3 hours after last bolus time of the period

    Args:
        filepath: Path to Carelink CSV file
        organized_bolus_data: Dict with structure {date: {period: [bolus_events]}}

    Returns:
        Dict with structure {date: {period: [glucose_readings]}}
    """
    bg_data = {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the data start line
        data_start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Index;Date;Time;"):
                data_start_idx = i
                headers = [col.strip() for col in line.strip().split(';')]
                break

        if data_start_idx == -1:
            raise ValueError("Could not find data header in CSV file")

        # Find column indices for BG data
        date_idx = headers.index("Date") if "Date" in headers else 1
        time_idx = headers.index("Time") if "Time" in headers else 2
        sensor_glucose_idx = headers.index("Sensor Glucose (mg/dL)") if "Sensor Glucose (mg/dL)" in headers else 33

        print(f"📊 Extracting BG: Date col={date_idx}, Time col={time_idx}, Sensor col={sensor_glucose_idx}")

        # For each date/period combination, determine time windows
        for date, periods in organized_bolus_data.items():
            bg_data[date] = {}

            for period_name, bolus_events in periods.items():
                if not bolus_events:
                    bg_data[date][period_name] = []
                    continue

                # Find first and last bolus times
                bolus_times = [datetime.strptime(f"{event.date} {event.time}", "%Y/%m/%d %H:%M:%S") for event in bolus_events]
                first_bolus = min(bolus_times)
                last_bolus = max(bolus_times)

                # Calculate time window: first bolus to 3h after last bolus
                end_time = last_bolus + timedelta(hours=3)

                # Extract BG readings in this time window
                period_readings = []

                for line in lines[data_start_idx + 1:]:
                    line = line.strip()
                    if not line or line.startswith('-'):
                        continue

                    row_data = [col.strip().strip('"') for col in line.split(';')]

                    if len(row_data) <= max(date_idx, time_idx, sensor_glucose_idx):
                        continue

                    date_str = row_data[date_idx]
                    time_str = row_data[time_idx]

                    if not date_str or not time_str:
                        continue

                    try:
                        # Parse timestamp
                        reading_time = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")

                        # Check if reading is within our time window
                        if first_bolus <= reading_time <= end_time:
                            # Extract sensor glucose
                            sensor_value = row_data[sensor_glucose_idx] if sensor_glucose_idx < len(row_data) else ""
                            if sensor_value and sensor_value.replace(',', '.').replace('.', '').isdigit():
                                sensor_float = float(sensor_value.replace(',', '.'))
                                if sensor_float > 0:
                                    period_readings.append(GlucoseReading(
                                        timestamp=f"{date_str} {time_str}",
                                        value=int(sensor_float),
                                        type="sensor"
                                    ))

                    except ValueError:
                        continue

                # Sort readings by timestamp
                period_readings.sort(key=lambda x: datetime.strptime(x.timestamp, "%Y/%m/%d %H:%M:%S"))
                bg_data[date][period_name] = period_readings

                print(f"   📅 {date} {period_name}: {len(period_readings)} BG readings ({first_bolus.strftime('%H:%M')} - {end_time.strftime('%H:%M')})")

    except Exception as e:
        print(f"❌ Error extracting BG data: {e}")
        return {}

    return bg_data

def extract_correction_boluses(filepath: str, organized_bolus_data: Dict[str, Dict[str, List[BolusEvent]]]) -> Dict[str, Dict[str, List[BolusEvent]]]:
    """
    Extract correction boluses (insulin-only, no carbs) during the BG response periods.

    Args:
        filepath: Path to Carelink CSV file
        organized_bolus_data: Dict with structure {date: {period: [bolus_events]}}

    Returns:
        Dict with structure {date: {period: [correction_boluses]}}
    """
    correction_data = {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the data start line
        data_start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Index;Date;Time;"):
                data_start_idx = i
                headers = [col.strip() for col in line.strip().split(';')]
                break

        if data_start_idx == -1:
            raise ValueError("Could not find data header in CSV file")

        # Find column indices
        date_idx = headers.index("Date") if "Date" in headers else 1
        time_idx = headers.index("Time") if "Time" in headers else 2
        carb_input_idx = headers.index("BWZ Carb Input (grams)") if "BWZ Carb Input (grams)" in headers else -1
        bolus_delivered_idx = headers.index("Bolus Volume Delivered (U)") if "Bolus Volume Delivered (U)" in headers else -1

        if bolus_delivered_idx == -1:
            return {}

        # For each date/period combination, find correction boluses in time window
        for date, periods in organized_bolus_data.items():
            correction_data[date] = {}

            for period_name, bolus_events in periods.items():
                if not bolus_events:
                    correction_data[date][period_name] = []
                    continue

                # Find time window (same logic as BG extraction)
                bolus_times = [datetime.strptime(f"{event.date} {event.time}", "%Y/%m/%d %H:%M:%S") for event in bolus_events]
                first_bolus = min(bolus_times)
                last_bolus = max(bolus_times)
                end_time = last_bolus + timedelta(hours=3)

                # Find correction boluses in this window
                correction_boluses = []

                for line in lines[data_start_idx + 1:]:
                    line = line.strip()
                    if not line or line.startswith('-'):
                        continue

                    row_data = [col.strip().strip('"') for col in line.split(';')]

                    if len(row_data) <= max(date_idx, time_idx, bolus_delivered_idx):
                        continue

                    date_str = row_data[date_idx]
                    time_str = row_data[time_idx]

                    if not date_str or not time_str:
                        continue

                    try:
                        # Parse timestamp
                        bolus_time = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")

                        # Check if bolus is within our time window
                        if first_bolus <= bolus_time <= end_time:
                            # Check for insulin delivery
                            insulin_value = row_data[bolus_delivered_idx] if bolus_delivered_idx < len(row_data) else ""
                            carb_value = row_data[carb_input_idx] if carb_input_idx != -1 and carb_input_idx < len(row_data) else ""

                            if insulin_value:
                                try:
                                    insulin_float = float(insulin_value.replace(',', '.'))
                                    carb_float = 0.0
                                    if carb_value:
                                        try:
                                            carb_float = float(carb_value.replace(',', '.'))
                                        except ValueError:
                                            pass

                                    # Correction bolus: has insulin but no (or minimal) carbs
                                    if insulin_float > 0 and carb_float == 0:
                                        correction_boluses.append(BolusEvent(
                                            timestamp=f"{date_str} {time_str}",
                                            carb_input=carb_float,
                                            insulin_delivered=insulin_float,
                                            date=date_str,
                                            time=time_str
                                        ))

                                except ValueError:
                                    pass

                    except ValueError:
                        continue

                # Sort by timestamp
                correction_boluses.sort(key=lambda x: datetime.strptime(x.timestamp, "%Y/%m/%d %H:%M:%S"))
                correction_data[date][period_name] = correction_boluses

    except Exception as e:
        print(f"❌ Error extracting correction boluses: {e}")
        return {}

    return correction_data

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

    print("\n📊 Glucose Parsing Results:")
    for key, value in summary.items():
        print(f"   {key}: {value}")

    if readings:
        print(f"\n📋 Sample readings:")
        for i, reading in enumerate(readings[:5]):
            print(f"   {i+1}. {reading.timestamp} - {reading.value} mg/dL ({reading.type})")

    # Test bolus parsing
    print(f"\n🧪 Testing bolus parser...")
    bolus_events = parse_bolus_events(filepath, days_back=7)

    print(f"\n📊 Bolus Parsing Results:")
    print(f"   Total bolus events: {len(bolus_events)}")

    if bolus_events:
        # Group by date for summary
        by_date = {}
        for event in bolus_events:
            if event.date not in by_date:
                by_date[event.date] = []
            by_date[event.date].append(event)

        print(f"   Days with bolus: {len(by_date)}")
        print(f"   Avg bolus per day: {len(bolus_events) / len(by_date):.1f}")

        print(f"\n📋 Sample bolus events:")
        for i, event in enumerate(bolus_events[:5]):
            print(f"   {i+1}. {event.time} - {event.carb_input}g carbs, {event.insulin_delivered}U insulin")

    return readings, bolus_events

if __name__ == "__main__":
    test_parser()