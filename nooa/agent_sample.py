#!/usr/bin/env python3
"""
Diabetes Analysis NOOA Agent - Sample Data for Faster Testing
"""

import asyncio
import os
import traceback

from dotenv import load_dotenv
from nooa.unifiedllm.registry import get_llm_client

from diabetes_agent import DiabetesAgent
from carelink_parser import parse_carelink_csv

load_dotenv()

def create_diabetes_agent(patient_id: str = "demo_patient"):
    """Create LLM client using environment variables."""
    llm = get_llm_client(
        f"openai/{os.getenv('MODEL_NAME')}",
        api_base=os.getenv('MODEL_URL'),
        api_key=os.getenv('ACCESS_KEY')
    )
    return DiabetesAgent(patient_id=patient_id, llm=llm)

async def demo_with_sample_data():
    """Demo with a manageable sample of real data."""
    print("🩺 DiabetesAgent - Real Data Sample")
    print("=" * 50)

    try:
        agent = create_diabetes_agent("sample_patient")

        # Load real data
        csv_filepath = "data/csv_report_30days-20260911_102845.csv"
        print(f"📄 Loading data from: {csv_filepath}")

        readings = parse_carelink_csv(csv_filepath, days_back=7)

        if not readings:
            print("❌ No data found")
            return

        # Take a mix: recent readings + every 30th for manageable analysis
        recent_readings = readings[-50:]  # Last 50 readings (most recent)
        sample_readings = readings[::30]  # Every 30th reading for historical context

        # Combine and remove duplicates, keeping chronological order
        combined = sample_readings + recent_readings
        seen_timestamps = set()
        final_readings = []
        for reading in combined:
            if reading.timestamp not in seen_timestamps:
                final_readings.append(reading)
                seen_timestamps.add(reading.timestamp)

        # Sort chronologically again
        final_readings.sort(key=lambda x: x.timestamp)

        print(f"📊 Using smart sample: {len(final_readings)} readings ({len(recent_readings)} recent + every 30th from {len(readings)} total)")

        # Load into agent
        for reading in final_readings:
            agent.add_reading(reading.timestamp, reading.value, reading.type)

        # Data summary
        summary = agent.get_readings_summary()
        print(f"\n📈 Sample Data Summary:")
        print(f"   Readings: {summary['count']}")
        print(f"   Average: {summary['average']:.1f} mg/dL")
        print(f"   Range: {summary['min']} - {summary['max']} mg/dL")

        # Time-in-Range
        tir_data = agent.calculate_time_in_range()
        print(f"\n🎯 Time-in-Range: {tir_data.in_range_percent:.1f}% in range (70-180)")

        # Recent readings
        recent = agent.get_recent_trend(3)
        print(f"\n🔄 Recent readings:")
        for reading in recent:
            print(f"   {reading.timestamp} - {reading.value} mg/dL ({reading.type})")

        # AI Analysis (this is the part that takes time)
        print(f"\n🧠 AI Analysis (analyzing {summary['count']} readings)...")
        print("⏳ Please wait for LLM response...")

        trends = await agent.analyze_glucose_trends()
        print(f"\n🔍 Glucose Trends Analysis:")
        print(f"{trends}")

        print(f"\n✅ Analysis complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_with_sample_data())