#!/usr/bin/env python3
"""
NOOA Bolus Review - Agentic analysis of diabetes data
Analyzes CSV data using RatioAnalysisAgent and generates organized output
"""
import os
import sys
import json
import shutil
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path

MAX_DATA_AGE_HOURS = 24

# Add nooa to path
sys.path.append(str(Path(__file__).parent.parent / "nooa"))
sys.path.append(str(Path(__file__).parent.parent / "carelink-python-client"))

def find_latest_csv_file():
    """Find the most recent CSV file in the data directory."""
    data_dir = Path("data")
    if not data_dir.exists():
        return None

    csv_files = list(data_dir.glob("csv_report_*.csv"))
    if not csv_files:
        return None

    # Sort by modification time, newest first
    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return csv_files[0]

def load_fetch_status():
    """Load the fetch status to get latest data file info."""
    status_file = Path("data/fetch_status.json")
    if not status_file.exists():
        return {}

    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

async def run_bolus_review(target_periods=None, force=False):
    """Run the NOOA bolus review analysis."""
    start_time = datetime.now()
    print(f"🧪 NOOA Bolus Review - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if target_periods:
        print(f"🎯 Target periods: {', '.join(target_periods)}")
    else:
        print(f"🌍 Analyzing all periods")

    print("=" * 60)

    try:
        from dotenv import load_dotenv
        from nooa.unifiedllm.registry import get_llm_client
        from ratio_analysis_agent import RatioAnalysisAgent

        # Load environment
        load_dotenv()

        # Find latest CSV data file
        csv_file = find_latest_csv_file()
        fetch_status = load_fetch_status()

        # Try to get the latest file from status first
        if fetch_status.get("latest_data_file"):
            status_file = Path(fetch_status["latest_data_file"])
            if status_file.exists():
                csv_file = status_file

        if not csv_file or not csv_file.exists():
            print(f"❌ No CSV data file found!")
            print(f"   💡 Run 'python3 scripts/fetch_diabetes_data.py' first to fetch data")
            return False

        print(f"📁 Using data file: {csv_file}")

        # Check data freshness
        data_age = None
        if fetch_status.get("last_fetch_timestamp"):
            fetch_time = datetime.fromisoformat(fetch_status["last_fetch_timestamp"])
            data_age = start_time - fetch_time
            print(f"📅 Data fetched: {fetch_time.strftime('%Y-%m-%d at %H:%M:%S')} ({data_age.total_seconds()/3600:.1f}h ago)")
        else:
            mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
            data_age = start_time - mtime
            print(f"📅 Data file modified: {mtime.strftime('%Y-%m-%d at %H:%M:%S')} ({data_age.total_seconds()/3600:.1f}h ago)")

        if data_age and data_age > timedelta(hours=MAX_DATA_AGE_HOURS) and not force:
            print(f"❌ Data is {data_age.total_seconds()/3600:.1f}h old (max {MAX_DATA_AGE_HOURS}h)")
            print(f"   💡 Run 'python3 scripts/fetch_diabetes_data.py' to refresh data")
            print(f"   💡 Or use --force to bypass this check")
            return False

        # Setup LLM client
        print(f"🔧 Setting up LLM client...")
        try:
            llm = get_llm_client(
                f"openai/{os.getenv('MODEL_NAME')}",
                api_base=os.getenv('MODEL_URL'),
                api_key=os.getenv('ACCESS_KEY')
            )
            print(f"   ✅ LLM client created")
        except Exception as e:
            print(f"❌ Failed to create LLM client: {e}")
            return False

        # Create analysis agent
        agent = RatioAnalysisAgent("review_patient", llm=llm)
        print(f"✅ RatioAnalysisAgent created")

        # Create timestamped output directories
        timestamp = start_time.strftime("%y%m%d_%H%M")
        generated_base = Path("generated")
        generated_dir = generated_base / timestamp
        generated_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 Output directory: generated/{timestamp}/")
        print(f"📊 Running analysis for last 7 days...")

        # Run analysis - save directly to timestamped directory
        results = await agent.analyze_all_periods_and_save(
            filepath=str(csv_file),
            days_back=7,
            output_dir=str(generated_dir),
            target_periods=target_periods
        )

        if not results.get("periods_analyzed"):
            print(f"❌ No periods analyzed!")
            return False

        print(f"✅ Analysis completed for {len(results['periods_analyzed'])} periods")

        # Post-process: generate HTML reports with charts
        from postprocess import postprocess
        print(f"\n📊 Running post-processing...")
        postprocess(generated_dir)

        # Calculate total duration
        end_time = datetime.now()
        total_duration = end_time - start_time
        duration_str = f"{total_duration.total_seconds():.1f} secondes"

        print(f"\n✅ NOOA Bolus Review completed successfully!")
        print(f"⏱️  Durée totale: {duration_str}")
        return True

    except Exception as e:
        print(f"❌ Error during review: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    valid_periods = ["breakfast", "lunch", "snack", "dinner", "night"]

    parser = argparse.ArgumentParser(description="NOOA Bolus Review - Analyze diabetes data")
    parser.add_argument("periods", nargs="*", choices=valid_periods, metavar="PERIOD",
                        help=f"Periods to analyze ({', '.join(valid_periods)}). All if omitted.")
    parser.add_argument("--force", "-f", action="store_true",
                        help=f"Run even if data is older than {MAX_DATA_AGE_HOURS}h")
    args = parser.parse_args()

    target_periods = args.periods or None

    try:
        success = asyncio.run(run_bolus_review(target_periods, force=args.force))
        if success:
            print(f"\n🎉 Review completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Review failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Review interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()