from typing import List, Dict, Optional

from nooa import Agent

from dataclasses import dataclass
from data_logger import summary_log_method

@dataclass
class GlucoseReading:
    """A glucose reading with timestamp and value."""
    timestamp: str
    value: int
    type: str  # 'sensor' or 'bg_meter'

@dataclass
class TimeInRangeData:
    """Time-in-Range analysis results."""
    in_range_percent: float
    below_range_percent: float
    above_range_percent: float
    period_days: int


class GlucoseDataManager:
    """
    Base class for managing glucose data and performing calculations.
    Contains all the deterministic Python methods for data management.
    """

    def __init__(self, patient_id: str = "demo_patient"):
        self.readings: List[GlucoseReading] = []
        self.patient_id: str = patient_id

    @summary_log_method()
    def add_reading(self, timestamp: str, value: int, reading_type: str = "sensor") -> int:
        """Add a glucose reading to our dataset."""
        reading = GlucoseReading(timestamp, value, reading_type)
        self.readings.append(reading)
        return len(self.readings)

    @summary_log_method()
    def get_average_glucose(self) -> float:
        """Calculate average glucose from stored readings."""
        if not self.readings:
            return 0.0
        return sum(r.value for r in self.readings) / len(self.readings)

    @summary_log_method()
    def get_reading_count(self) -> int:
        """Get total number of stored readings."""
        return len(self.readings)

    @summary_log_method()
    def clear_readings(self):
        """Clear all stored readings."""
        self.readings = []

    @summary_log_method()
    def get_readings_summary(self) -> Dict[str, any]:
        """Get summary statistics of stored readings."""
        if not self.readings:
            return {"count": 0, "average": 0, "min": 0, "max": 0, "sensor_count": 0, "meter_count": 0}

        values = [r.value for r in self.readings]
        return {
            "count": len(values),
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "sensor_count": len([r for r in self.readings if r.type == "sensor"]),
            "meter_count": len([r for r in self.readings if r.type == "bg_meter"])
        }

    @summary_log_method()
    def get_readings_in_range(self, min_value: int = 70, max_value: int = 180) -> List[GlucoseReading]:
        """Get readings within target range (default: 70-180 mg/dL)."""
        return [r for r in self.readings if min_value <= r.value <= max_value]

    @summary_log_method()
    def get_high_readings(self, threshold: int = 180) -> List[GlucoseReading]:
        """Get readings above threshold (default: >180 mg/dL)."""
        return [r for r in self.readings if r.value > threshold]

    @summary_log_method()
    def get_low_readings(self, threshold: int = 70) -> List[GlucoseReading]:
        """Get readings below threshold (default: <70 mg/dL)."""
        return [r for r in self.readings if r.value < threshold]

    @summary_log_method()
    def calculate_time_in_range(self, target_min: int = 70, target_max: int = 180) -> TimeInRangeData:
        """Calculate Time-in-Range statistics."""
        if not self.readings:
            return TimeInRangeData(0.0, 0.0, 0.0, 0)

        total_readings = len(self.readings)
        in_range_count = len(self.get_readings_in_range(target_min, target_max))
        below_range_count = len(self.get_low_readings(target_min))
        above_range_count = len(self.get_high_readings(target_max))

        return TimeInRangeData(
            in_range_percent=(in_range_count / total_readings) * 100,
            below_range_percent=(below_range_count / total_readings) * 100,
            above_range_percent=(above_range_count / total_readings) * 100,
            period_days=1  # Assuming daily data for now
        )

    @summary_log_method()
    def get_recent_trend(self, num_readings: int = 3) -> List[GlucoseReading]:
        """Get the most recent N readings for trend analysis."""
        return self.readings[-num_readings:] if self.readings else []


class DiabetesAgent(GlucoseDataManager, Agent):
    """
    AI-powered diabetes analysis agent that extends GlucoseDataManager.
    Contains LLM-driven generation methods for clinical insights and recommendations.
    """

    def __init__(self, patient_id: str = "demo_patient", llm=None):
        # Initialize the data manager
        GlucoseDataManager.__init__(self, patient_id)
        # Initialize Agent with LLM
        Agent.__init__(self, llm=llm)

    # ---
    # --- Generation methods (LLM-implemented)
    # ---

    async def analyze_glucose_trends(self) -> str:
        """
        Analyze the glucose readings and identify patterns.
        Look for concerning trends, good control periods, and recommendations.
        Mention specific values and timeframes when possible.
        Use the stored readings data to provide specific insights.
        """
        ...

    async def interpret_time_in_range(self, tir_percent: float, below_percent: float, above_percent: float) -> str:
        """
        Interpret Time-in-Range percentages and provide clinical insights.
        Explain what these numbers mean for diabetes management.
        TIR target is 70%+, below range should be <4%, above range <25%.
        Provide specific recommendations based on the percentages.
        """
        ...

    async def recommend_actions(self) -> str:
        """
        Based on current glucose data, recommend specific actions
        for better diabetes management. Be practical and actionable.
        Consider the patient's recent readings, trends, and patterns.
        """
        ...

    async def generate_daily_report(self) -> str:
        """
        Generate a comprehensive daily diabetes report based on stored readings.
        Include key metrics, patterns, alerts, and actionable insights.
        Format as a summary suitable for patients or healthcare providers.
        Include specific numbers from the data.
        """
        ...

    async def explain_glucose_value(self, value: int, context: str = "") -> str:
        """
        Explain what a specific glucose value means clinically.
        Include target ranges, potential causes, and next steps.
        Use the context to provide personalized advice.
        Be specific about whether this is low, normal, or high.
        """
        ...

    async def assess_control_quality(self) -> str:
        """
        Assess overall diabetes control quality based on all stored data.
        Look at averages, variability, time-in-range, and patterns.
        Provide an overall grade and specific areas for improvement.
        """
        ...

    async def identify_patterns(self) -> str:
        """
        Identify patterns in glucose data such as dawn phenomenon,
        post-meal spikes, exercise effects, or other trends.
        Be specific about times and glucose values observed.
        """
        ...

    async def suggest_discussion_points(self) -> str:
        """
        Based on the glucose data analysis, suggest key points
        to discuss with healthcare providers at the next appointment.
        Include specific data points and concerns.
        """
        ...
