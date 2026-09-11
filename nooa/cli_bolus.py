#!/usr/bin/env python3
"""
CLI tool for displaying bolus data organized by periods
"""
import sys
import argparse
import statistics
from diabetes_agent import GlucoseDataManager
from carelink_parser import parse_bolus_events, load_latest_csv_file, extract_bg_for_periods, extract_correction_boluses

def show_bolus(filepath: str = None, days: int = 7):
    """
    Show bolus data organized by periods, then by days within each period.

    Args:
        filepath: Path to Carelink CSV file (auto-detect if None)
        days: Number of days to show (default: 7)
    """
    print(f"🍽️  Bolus Analysis - Last {days} Days")
    print("=" * 50)

    # Auto-detect CSV file if not provided
    if filepath is None:
        filepath = load_latest_csv_file()
        if filepath is None:
            print("❌ No CSV files found in data/ directory")
            return
        print(f"📁 Using: {filepath}")

    # Parse bolus events
    bolus_events = parse_bolus_events(filepath, days_back=days)

    if not bolus_events:
        print("❌ No bolus events found")
        return

    print(f"📊 Found {len(bolus_events)} bolus events")
    print()

    # Create data manager and get all periods data
    manager = GlucoseDataManager("cli_user")
    all_data = manager.get_all_periods_for_days(bolus_events, days=days)

    # Extract BG data for each period
    print("🩸 Extracting BG sensor data...")
    bg_data = extract_bg_for_periods(filepath, all_data)

    # Extract correction boluses for each period
    print("💉 Extracting correction boluses...")
    correction_data = extract_correction_boluses(filepath, all_data)
    print()

    # Define period order for consistent display
    periods = ["Breakfast", "Lunch", "Snack", "Dinner", "Night"]

    # Display data organized by periods first, then days
    for period in periods:
        print(f"🕐 {period.upper()}")
        print("-" * 20)

        # Check if any days have data for this period
        has_data = False
        sorted_dates = sorted(all_data.keys())

        for date in sorted_dates:
            events = all_data[date][period]
            if events:
                has_data = True
                print(f"  📅 {date}")
                for event in events:
                    # Basic bolus info
                    print(f"     {event.time} - {event.carb_input}g carbs, {event.insulin_delivered}U insulin")

                    # BWZ calculation details
                    bwz_parts = []
                    if event.carb_ratio is not None:
                        bwz_parts.append(f"I:C {event.carb_ratio}g/U")
                    if event.food_estimate is not None:
                        bwz_parts.append(f"Food {event.food_estimate}U")
                    if event.correction_estimate is not None and event.correction_estimate != 0:
                        bwz_parts.append(f"Corr {event.correction_estimate:+.2f}U")
                    if event.bg_input is not None:
                        bwz_parts.append(f"BG {event.bg_input}mg/dL")

                    if bwz_parts:
                        print(f"       📊 {' | '.join(bwz_parts)}")

                # Show BG data for this period/date
                if date in bg_data and period in bg_data[date]:
                    bg_readings = bg_data[date][period]
                    if bg_readings:
                        values = [r.value for r in bg_readings]
                        start_bg = bg_readings[0].value
                        finish_bg = bg_readings[-1].value
                        min_bg = min(values)
                        max_bg = max(values)
                        median_bg = statistics.median(values)
                        avg_bg = sum(values) / len(values)
                        under_80 = len([v for v in values if v < 80])
                        above_200 = len([v for v in values if v > 200])
                        first_time = bg_readings[0].timestamp.split()[1]
                        last_time = bg_readings[-1].timestamp.split()[1]

                        print(f"     🩸 BG Response: {len(bg_readings)} readings ({first_time}-{last_time})")
                        print(f"       📊 Start {start_bg} → Finish {finish_bg} | Min {min_bg} | Max {max_bg} | Median {median_bg:.0f} | Avg {avg_bg:.0f} mg/dL")
                        print(f"       🚨 Under 80: {under_80} | Over 200: {above_200} readings")

                # Show correction boluses for this period/date
                if date in correction_data and period in correction_data[date]:
                    correction_boluses = correction_data[date][period]
                    if correction_boluses:
                        print(f"     💉 Correction Boluses: {len(correction_boluses)} during period")
                        for corr in correction_boluses:
                            print(f"       {corr.time} - {corr.insulin_delivered}U correction")

        if not has_data:
            print(f"     (no {period.lower()} boluses in last {days} days)")

        print()

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Show bolus data organized by time periods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_bolus.py                    # Show last 7 days from auto-detected CSV
  python cli_bolus.py --days 3           # Show last 3 days
  python cli_bolus.py --file data.csv    # Use specific CSV file
  python cli_bolus.py --days 14 --file data.csv  # 14 days from specific file
        """)

    parser.add_argument(
        "--file", "-f",
        help="Path to Carelink CSV file (auto-detects latest if not provided)"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)"
    )

    args = parser.parse_args()

    try:
        show_bolus(filepath=args.file, days=args.days)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()