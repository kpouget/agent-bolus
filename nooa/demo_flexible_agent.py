#!/usr/bin/env python3
"""
Demo showing flexible LLM instantiation with DiabetesAgent
"""
import asyncio
from diabetes_agent import DiabetesAgent, GlucoseDataManager, create_default_llm, create_diabetes_agent

async def demo_flexible_instantiation():
    """Demo different ways to create DiabetesAgent instances."""
    print("🧪 Flexible DiabetesAgent Instantiation Demo")
    print("=" * 50)

    # Method 1: Create LLM once, use for multiple agents
    print("\n📋 Method 1: Shared LLM for multiple agents")
    llm = create_default_llm()

    agent1 = DiabetesAgent(patient_id="patient_001", llm=llm)
    agent2 = DiabetesAgent(patient_id="patient_002", llm=llm)

    print(f"✅ Created agent1 for {agent1.patient_id}")
    print(f"✅ Created agent2 for {agent2.patient_id}")

    # Method 2: Use factory function (convenience)
    print("\n📋 Method 2: Factory function")
    agent3 = create_diabetes_agent("patient_003")
    print(f"✅ Created agent3 for {agent3.patient_id}")

    # Method 3: Data manager only (no AI)
    print("\n📋 Method 3: Pure data manager (no AI)")
    data_manager = GlucoseDataManager("patient_data_only")
    data_manager.add_reading("2026-09-11 08:00", 120)
    summary = data_manager.get_readings_summary()
    print(f"✅ Data manager: {summary}")

    # Test with agent1 - add data and analyze
    print("\n📋 Testing agent1 with glucose analysis")
    agent1.add_reading("2026-09-11 08:00", 130, "meter")
    agent1.add_reading("2026-09-11 12:00", 180, "sensor")
    agent1.add_reading("2026-09-11 18:00", 145, "sensor")

    summary = agent1.get_readings_summary()
    print(f"📊 Agent1 data: {summary}")

    # Get AI analysis
    try:
        analysis = await agent1.analyze_glucose_trends()
        print(f"🧠 AI Analysis: {analysis}")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

    # Test agent2 with different data
    print("\n📋 Testing agent2 with different data")
    agent2.add_reading("2026-09-11 07:00", 95, "meter")
    agent2.add_reading("2026-09-11 11:00", 160, "sensor")
    agent2.add_reading("2026-09-11 15:00", 135, "sensor")

    summary2 = agent2.get_readings_summary()
    print(f"📊 Agent2 data: {summary2}")

    try:
        recommendation = await agent2.recommend_actions()
        print(f"💡 AI Recommendation: {recommendation}")
    except Exception as e:
        print(f"❌ Recommendation failed: {e}")

    print("\n✅ Demo completed - LLM flexibility working!")

if __name__ == "__main__":
    asyncio.run(demo_flexible_instantiation())