#!/usr/bin/env python3
"""
Diabetes Analysis NOOA Agent - Using Real CSV Data
"""

import asyncio
import os
import traceback

from dotenv import load_dotenv
from nooa.unifiedllm.registry import get_llm_client

from diabetes_agent import DiabetesAgent, TimeInRangeData, GlucoseReading
from carelink_parser import parse_carelink_csv, summarize_readings

load_dotenv()

def create_diabetes_agent(patient_id: str = "demo_patient"):
    """Create LLM client using environment variables."""
    llm = get_llm_client(
        f"openai/{os.getenv('MODEL_NAME')}",
        api_base=os.getenv('MODEL_URL'),
        api_key=os.getenv('ACCESS_KEY')
    )

    return DiabetesAgent(patient_id=patient_id, llm=llm)


async def demo_diabetes_agent():
    """Demo function showing DiabetesAgent capabilities with real data."""
    print("🩺 Diabetes Analysis NOOA Agent - Real Data")
    print("=" * 60)

    try:
        # Create agent using factory function (handles LLM creation)
        print("🔧 Creating diabetes agent...")
        agent = create_diabetes_agent("real_patient")

        # Load real CSV data
        csv_filepath = "data/csv_report_30days-20260911_102845.csv"
        print(f"📄 Loading real data from: {csv_filepath}")

        if not os.path.exists(csv_filepath):
            print(f"❌ CSV file not found: {csv_filepath}")
            print("💡 Make sure you have downloaded Carelink data first")
            return

        # Parse last 7 days of data
        print("📊 Parsing last 7 days of glucose data...")
        readings = parse_carelink_csv(csv_filepath, days_back=7)

        if not readings:
            print("❌ No glucose readings found in the last 7 days")
            return

        # Load readings into agent
        print("📥 Loading readings into DiabetesAgent...")
        for reading in readings:
            agent.add_reading(reading.timestamp, reading.value, reading.type)

        # Show data summary
        summary = agent.get_readings_summary()
        print(f"\n📈 Real Data Summary:")
        print(f"   Total readings: {summary['count']}")
        print(f"   Average glucose: {summary['average']:.1f} mg/dL")
        print(f"   Range: {summary['min']} - {summary['max']} mg/dL")
        print(f"   Sensor readings: {summary['sensor_count']}")
        print(f"   Meter readings: {summary['meter_count']}")

        # Calculate Time-in-Range
        tir_data = agent.calculate_time_in_range()
        print(f"\n🎯 Time-in-Range (70-180 mg/dL):")
        print(f"   In range: {tir_data.in_range_percent:.1f}%")
        print(f"   Below range: {tir_data.below_range_percent:.1f}%")
        print(f"   Above range: {tir_data.above_range_percent:.1f}%")

        # Show recent trend
        recent = agent.get_recent_trend(5)
        print(f"\n🔄 Recent 5 readings:")
        for i, reading in enumerate(recent):
            print(f"   {i+1}. {reading.timestamp} - {reading.value} mg/dL ({reading.type})")

        # AI Analysis
        print("\n" + "="*60)
        print("🧠 AI ANALYSIS")
        print("="*60)

        print("\n🔍 Analyzing glucose trends...")
        trends = await agent.analyze_glucose_trends()
        print(f"Trends: {trends}")

        print("\n📊 Time-in-Range interpretation...")
        tir_interpretation = await agent.interpret_time_in_range(
            tir_data.in_range_percent,
            tir_data.below_range_percent,
            tir_data.above_range_percent
        )
        print(f"TIR Analysis: {tir_interpretation}")

        print("\n💡 Getting recommendations...")
        recommendations = await agent.recommend_actions()
        print(f"Recommendations: {recommendations}")

        print(f"\n✅ Analysis completed for {summary['count']} real glucose readings!")

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()


async def quick_demo():
    """Quick demo with just trend analysis."""
    print("⚡ Quick Real Data Analysis")
    print("-" * 40)

    try:
        agent = create_diabetes_agent("quick_patient")

        # Load real data
        csv_filepath = "data/csv_report_30days-20260911_102845.csv"
        readings = parse_carelink_csv(csv_filepath, days_back=7)

        if not readings:
            print("❌ No data found")
            return

        # Load into agent
        for reading in readings[:20]:  # Just first 20 for quick demo
            agent.add_reading(reading.timestamp, reading.value, reading.type)

        summary = agent.get_readings_summary()
        print(f"📊 Loaded {summary['count']} readings, avg: {summary['average']:.1f} mg/dL")

        # Quick analysis
        analysis = await agent.analyze_glucose_trends()
        print(f"🧠 Quick analysis: {analysis}")

    except Exception as e:
        print(f"❌ Quick demo failed: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(quick_demo())
    else:
        asyncio.run(demo_diabetes_agent())