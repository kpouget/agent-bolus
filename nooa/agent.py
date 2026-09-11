#!/usr/bin/env python3
"""
Diabetes Analysis NOOA Agent - Updated for Flexible LLM Instantiation
"""

import asyncio
import os
import traceback

from dotenv import load_dotenv
from nooa.unifiedllm.registry import get_llm_client

from diabetes_agent import DiabetesAgent, TimeInRangeData, GlucoseReading

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
    """Demo function showing DiabetesAgent capabilities."""
    print("🩺 Diabetes Analysis NOOA Agent")
    print("=" * 50)

    try:
        # Create agent using factory function (handles LLM creation)
        print("🔧 Creating diabetes agent...")
        agent = create_diabetes_agent("demo_patient")

        # Add sample glucose data
        print("📊 Adding sample glucose readings...")
        agent.add_reading("2026-09-11 08:00", 120, "sensor")
        agent.add_reading("2026-09-11 08:15", 125, "sensor")
        agent.add_reading("2026-09-11 08:30", 180, "sensor")  # Post-meal spike
        agent.add_reading("2026-09-11 10:00", 160, "sensor")
        agent.add_reading("2026-09-11 12:00", 95, "bg_meter")
        agent.add_reading("2026-09-11 14:00", 110, "sensor")
        agent.add_reading("2026-09-11 16:00", 140, "sensor")
        agent.add_reading("2026-09-11 18:00", 220, "sensor")  # High reading

        summary = agent.get_readings_summary()
        print(f"✅ Added {summary['count']} readings")
        print(f"📈 Average glucose: {summary['average']:.1f} mg/dL")
        print(f"📊 Range: {summary['min']} - {summary['max']} mg/dL")
        print(f"🔬 Sensor readings: {summary['sensor_count']}, Meter: {summary['meter_count']}")

        # Test 1: Analyze trends
        print("\n" + "="*50)
        print("TEST 1: Glucose Trend Analysis")
        print("="*50)

        trends = await agent.analyze_glucose_trends()
        print(f"🔍 Trends: {trends}")

        full = False
        if full:
            # Test 2: Time-in-Range interpretation
            print("\n" + "="*50)
            print("TEST 2: Time-in-Range Analysis")
            print("="*50)

            tir_interpretation = await agent.interpret_time_in_range(65.0, 8.0, 27.0)
            print(f"📊 TIR Analysis: {tir_interpretation}")

            # Test 3: Recommendations
            print("\n" + "="*50)
            print("TEST 3: Action Recommendations")
            print("="*50)

            recommendations = await agent.recommend_actions()
            print(f"💡 Recommendations: {recommendations}")

        print("\n✅ Diabetes agent demo completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_diabetes_agent())
