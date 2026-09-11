#!/usr/bin/env python3
"""
RatioAnalysisAgent - AI-powered I:C ratio analysis agent
Analyzes insulin-to-carb ratio effectiveness one period at a time across multiple days
"""

from typing import List, Dict, Any, Optional
from dataclasses import asdict
import os
import yaml
import json
from datetime import datetime

from nooa import Agent
from diabetes_agent import DiabetesAgent
from carelink_parser import parse_bolus_events, extract_bg_for_periods, extract_correction_boluses, extract_basal_for_periods
from data_logger import summary_log_method


class RatioAnalysisAgent(DiabetesAgent):
    """
    AI-powered agent for analyzing I:C ratio effectiveness.

    Focuses on one period at a time (e.g., "Breakfast") across multiple days,
    with day -1 being most important for analysis.
    """

    def __init__(self, patient_id: str = "analysis_patient", llm=None):
        # Initialize the parent DiabetesAgent
        if llm is not None:
            super().__init__(patient_id, llm)
        else:
            super().__init__(patient_id)

    @summary_log_method()
    def get_period_analysis_data(self, filepath: str, period_name: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Extract and structure all data for a specific period across multiple days.

        Args:
            filepath: Path to Carelink CSV file
            period_name: One of 'Breakfast', 'Lunch', 'Snack', 'Dinner', 'Night'
            days_back: Number of days to analyze

        Returns:
            Structured dictionary with all period data for LLM analysis
        """
        # Parse all the raw data
        bolus_events = parse_bolus_events(filepath, days_back=days_back)

        if not bolus_events:
            return {"error": "No bolus events found", "period": period_name}

        # Organize data by periods
        all_periods_data = self.get_all_periods_for_days(bolus_events, days=days_back)

        # Extract supplementary data
        bg_data = extract_bg_for_periods(filepath, all_periods_data)
        correction_data = extract_correction_boluses(filepath, all_periods_data)
        basal_data = extract_basal_for_periods(filepath, all_periods_data)

        # Structure data for the specified period only
        period_analysis = {
            "period_name": period_name,
            "days_analyzed": days_back,
            "analysis_date": "2026-09-11",  # Current date
            "days_data": []
        }

        # Get all dates with data for this period, sorted by most recent first
        dates_with_data = []
        for date, periods in all_periods_data.items():
            if period_name in periods and periods[period_name]:
                dates_with_data.append(date)

        # Sort dates: most recent first (day -1, day -2, etc.)
        dates_with_data.sort(reverse=True)

        # Structure data for each day
        for i, date in enumerate(dates_with_data):
            day_offset = -(i + 1)  # Day -1, -2, -3, etc.

            # Get bolus events for this period/date
            bolus_events_day = all_periods_data[date][period_name]

            # Convert bolus events to dict format
            bolus_data = []
            for event in bolus_events_day:
                bolus_data.append({
                    "time": event.time,
                    "carb_input": event.carb_input,
                    "insulin_delivered": event.insulin_delivered,
                    "ic_ratio": event.carb_ratio,
                    "food_estimate": event.food_estimate,
                    "correction_estimate": event.correction_estimate,
                    "bg_input": event.bg_input,
                    "active_insulin": event.active_insulin
                })

            # Get BG response data
            bg_response = None
            if date in bg_data and period_name in bg_data[date]:
                bg_readings = bg_data[date][period_name]
                if bg_readings:
                    values = [r.value for r in bg_readings]
                    bg_response = {
                        "start_bg": bg_readings[0].value,
                        "finish_bg": bg_readings[-1].value,
                        "min_bg": min(values),
                        "max_bg": max(values),
                        "avg_bg": sum(values) / len(values),
                        "median_bg": sorted(values)[len(values)//2],
                        "readings_count": len(bg_readings),
                        "under_80": len([v for v in values if v < 80]),
                        "over_200": len([v for v in values if v > 200]),
                        "time_window": f"{bg_readings[0].timestamp.split()[1]}-{bg_readings[-1].timestamp.split()[1]}"
                    }

            # Get correction boluses
            corrections = []
            if date in correction_data and period_name in correction_data[date]:
                for corr in correction_data[date][period_name]:
                    corrections.append({
                        "time": corr.time,
                        "insulin_delivered": corr.insulin_delivered
                    })

            # Get basal summary
            basal_summary = None
            if date in basal_data and period_name in basal_data[date]:
                basal_events = basal_data[date][period_name]
                if basal_events:
                    standard_basal = [e for e in basal_events if e.basal_rate is not None and not e.temp_basal_type]
                    temp_basal = [e for e in basal_events if e.temp_basal_type]

                    if standard_basal:
                        rates = [e.basal_rate for e in standard_basal]
                        avg_rate = sum(rates) / len(rates)
                        basal_summary = {
                            "avg_rate": avg_rate,
                            "total_estimated": avg_rate * 3.0,  # 3-hour window
                            "rate_changes": len(set(rates)),
                            "temp_basal_events": len(temp_basal)
                        }

            # Add this day's structured data
            day_data = {
                "date": date,
                "day_offset": day_offset,  # -1, -2, -3, etc.
                "bolus_events": bolus_data,
                "bg_response": bg_response,
                "correction_boluses": corrections,
                "basal_summary": basal_summary
            }

            period_analysis["days_data"].append(day_data)

        return period_analysis

    def _get_period_prefix(self, period_name: str) -> str:
        """Get numeric prefix for period to ensure proper file ordering."""
        period_prefixes = {
            "breakfast": "0",
            "lunch": "1",
            "snack": "2",
            "dinner": "3",
            "night": "4"
        }
        return period_prefixes.get(period_name.lower(), "9")

    @summary_log_method()
    def save_period_analysis(self, period_analysis_data: Dict[str, Any], output_dir: str = "output") -> str:
        """
        Save period analysis data to output directory.

        Args:
            period_analysis_data: Data from get_period_analysis_data()
            output_dir: Base output directory

        Returns:
            Path to saved file
        """
        # Create output directory structure with period subdirectory
        period_name = period_analysis_data.get("period_name", "unknown")
        days_analyzed = period_analysis_data.get("days_analyzed", 0)

        # Create period subdirectory with numeric prefix
        prefix = self._get_period_prefix(period_name)
        period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
        os.makedirs(period_dir, exist_ok=True)

        filename = f"{days_analyzed}days.yaml"
        filepath = os.path.join(period_dir, filename)

        # Add metadata
        save_data = {
            "analysis_metadata": {
                "generated_at": datetime.now().isoformat(),
                "period_name": period_name,
                "days_analyzed": days_analyzed,
                "total_days_with_data": len(period_analysis_data.get("days_data", [])),
                "analysis_date_range": self._get_date_range(period_analysis_data)
            },
            "period_analysis_data": period_analysis_data
        }

        # Save as YAML for readability
        with open(filepath, 'w') as f:
            yaml.dump(save_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return filepath

    @summary_log_method()
    def save_period_plot_data(self, period_analysis_data: Dict[str, Any], output_dir: str = "output") -> str:
        """
        Save period data in format optimized for plotting and visual inspection.

        Args:
            period_analysis_data: Data from get_period_analysis_data()
            output_dir: Base output directory

        Returns:
            Path to saved plot data file
        """
        # Create period-specific subdirectory for YAML files
        period_name = period_analysis_data.get("period_name", "unknown")
        days_analyzed = len(period_analysis_data.get("days_data", []))

        period_dir = os.path.join(output_dir, period_name.lower())
        os.makedirs(period_dir, exist_ok=True)

        filename = "plot_data.yaml"
        filepath = os.path.join(period_dir, filename)

        # Organize data for plotting
        plot_data = {
            "metadata": {
                "period_name": period_name,
                "generated_at": datetime.now().isoformat(),
                "total_days": days_analyzed,
                "date_range": self._get_date_range(period_analysis_data),
                "description": f"Données de glycémie et bolus pour {period_name} - prêtes pour visualisation"
            },
            "days_data": []
        }

        # Process each day's data for plotting
        for day_data in period_analysis_data.get("days_data", []):
            day_plot = {
                "date": day_data["date"],
                "day_offset": day_data["day_offset"],
                "bolus_events": [],
                "bg_summary": None,
                "correction_boluses": [],
                "basal_summary": None
            }

            # Bolus events (meals)
            for bolus in day_data.get("bolus_events", []):
                day_plot["bolus_events"].append({
                    "time": bolus["time"],
                    "carb_input": bolus["carb_input"],
                    "insulin_delivered": bolus["insulin_delivered"],
                    "ic_ratio": bolus.get("ic_ratio"),
                    "bg_input": bolus.get("bg_input"),
                    "food_estimate": bolus.get("food_estimate"),
                    "correction_estimate": bolus.get("correction_estimate")
                })

            # BG summary for reference
            bg_response = day_data.get("bg_response")
            if bg_response:
                day_plot["bg_summary"] = {
                    "start_bg": bg_response["start_bg"],
                    "finish_bg": bg_response["finish_bg"],
                    "min_bg": bg_response["min_bg"],
                    "max_bg": bg_response["max_bg"],
                    "avg_bg": bg_response["avg_bg"],
                    "under_80_count": bg_response.get("under_80", 0),
                    "over_200_count": bg_response.get("over_200", 0),
                    "readings_count": bg_response.get("readings_count", 0),
                    "time_window": bg_response.get("time_window", "")
                }

            # Correction boluses
            for corr in day_data.get("correction_boluses", []):
                day_plot["correction_boluses"].append({
                    "time": corr["time"],
                    "insulin_delivered": corr["insulin_delivered"]
                })

            # Basal summary
            basal_summary = day_data.get("basal_summary")
            if basal_summary:
                day_plot["basal_summary"] = {
                    "avg_rate": basal_summary["avg_rate"],
                    "total_estimated": basal_summary.get("total_estimated", basal_summary["avg_rate"] * 3.0),
                    "rate_changes": basal_summary.get("rate_changes", 0),
                    "temp_basal_events": basal_summary.get("temp_basal_events", 0)
                }

            plot_data["days_data"].append(day_plot)

        # Save as YAML
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(plot_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return filepath

    @summary_log_method()
    def save_detailed_bg_data(self, period_analysis_data: Dict[str, Any], filepath: str, output_dir: str = "output") -> str:
        """
        Save detailed BG readings for plotting (all individual points).

        Args:
            period_analysis_data: Data from get_period_analysis_data()
            filepath: Original Carelink CSV file
            output_dir: Base output directory

        Returns:
            Path to saved detailed BG file
        """
        # Create period-specific subdirectory for YAML files
        period_name = period_analysis_data.get("period_name", "unknown")

        period_dir = os.path.join(output_dir, period_name.lower())
        os.makedirs(period_dir, exist_ok=True)

        filename = "bg_detailed.yaml"
        bg_filepath = os.path.join(period_dir, filename)

        # Re-extract BG data with individual readings
        all_periods_data = {}
        for day_data in period_analysis_data.get("days_data", []):
            date = day_data["date"]
            all_periods_data[date] = {period_name: []}

            # Reconstruct bolus events for BG extraction
            for bolus in day_data.get("bolus_events", []):
                # Create minimal BolusEvent structure
                bolus_event = type('BolusEvent', (), {
                    'date': date,
                    'time': bolus["time"],
                    'timestamp': f"{date} {bolus['time']}"
                })()
                all_periods_data[date][period_name].append(bolus_event)

        # Extract detailed BG readings
        bg_data = extract_bg_for_periods(filepath, all_periods_data)

        # Organize for plotting
        detailed_bg = {
            "metadata": {
                "period_name": period_name,
                "generated_at": datetime.now().isoformat(),
                "description": f"Lectures détaillées de glycémie pour {period_name} - tous les points individuels"
            },
            "days_bg_data": []
        }

        for day_data in period_analysis_data.get("days_data", []):
            date = day_data["date"]
            day_offset = day_data["day_offset"]

            bg_readings_list = []
            if date in bg_data and period_name in bg_data[date]:
                for reading in bg_data[date][period_name]:
                    bg_readings_list.append({
                        "timestamp": reading.timestamp,
                        "time": reading.timestamp.split()[1],  # Just the time part
                        "value": reading.value,
                        "type": reading.type
                    })

            detailed_bg["days_bg_data"].append({
                "date": date,
                "day_offset": day_offset,
                "bg_readings": bg_readings_list,
                "readings_count": len(bg_readings_list)
            })

        # Save detailed BG data
        with open(bg_filepath, 'w', encoding='utf-8') as f:
            yaml.dump(detailed_bg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return bg_filepath

    @summary_log_method()
    def save_llm_analysis(self, period_name: str, llm_analysis: str, output_dir: str = "output", processing_duration: float = None) -> str:
        """
        Save LLM analysis results to output directory.

        Args:
            period_name: Name of the period analyzed
            llm_analysis: LLM analysis result text
            output_dir: Base output directory

        Returns:
            Path to saved file
        """
        # Create period-specific subdirectory
        period_dir = os.path.join(output_dir, period_name.lower())
        os.makedirs(period_dir, exist_ok=True)

        filename = "llm_analysis.md"
        filepath = os.path.join(period_dir, filename)

        # Save as Markdown for readability with optional duration
        duration_info = ""
        if processing_duration is not None:
            duration_info = f"**Durée d'exécution:** {processing_duration:.1f} secondes\n"

        content = f"""# Analyse du Ratio I:C - {period_name}

**Généré le:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Période:** {period_name}
{duration_info}

## Analyse Clinique

{llm_analysis}

---
*Généré par RatioAnalysisAgent (analyse en français)*
"""

        with open(filepath, 'w') as f:
            f.write(content)

        return filepath

    @summary_log_method()
    async def analyze_all_periods_and_save(self, filepath: str, days_back: int = 7, output_dir: str = "output", target_periods: list = None) -> Dict[str, Any]:
        """
        Analyze all periods and save results to output directory.

        Args:
            filepath: Path to Carelink CSV file
            days_back: Number of days to analyze
            output_dir: Output directory for results
            target_periods: Optional list of specific periods to analyze (e.g., ["breakfast", "lunch"])

        Returns:
            Summary of analysis and saved files
        """
        all_periods = ["Breakfast", "Lunch", "Snack", "Dinner", "Night"]

        # Filter periods if specific ones are requested
        if target_periods:
            periods = [p for p in all_periods if p.lower() in [t.lower() for t in target_periods]]
            if not periods:
                raise ValueError(f"No valid periods found in {target_periods}")
        else:
            periods = all_periods
        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "periods_analyzed": [],
            "saved_files": [],
            "summary": {}
        }

        if target_periods:
            print(f"🧪 Analyzing {len(periods)} specific periods over last {days_back} days: {', '.join(periods)}")
        else:
            print(f"🧪 Analyzing all {len(periods)} periods over last {days_back} days...")
        print(f"📁 Saving results to: {output_dir}/")

        for period_name in periods:
            print(f"\n🕐 Analyzing {period_name}...")

            try:
                # Get period data
                period_data = self.get_period_analysis_data(filepath, period_name, days_back)

                if "error" in period_data:
                    print(f"   ❌ {period_data['error']}")
                    continue

                days_with_data = len(period_data.get("days_data", []))
                if days_with_data == 0:
                    print(f"   ⚠️  No data for {period_name}")
                    continue

                print(f"   📊 Found data for {days_with_data} days")

                # Save period data
                data_file = self.save_period_analysis(period_data, output_dir)
                print(f"   💾 Data saved: {os.path.basename(data_file)}")

                # Save plot-ready data for visualization
                plot_file = self.save_period_plot_data(period_data, output_dir)
                print(f"   📊 Plot data saved: {os.path.basename(plot_file)}")

                # Save detailed BG readings for plotting
                bg_file = self.save_detailed_bg_data(period_data, filepath, output_dir)
                print(f"   🩸 BG detail saved: {os.path.basename(bg_file)}")

                # Get LLM analysis in French with timing
                print(f"   🧠 Analyse LLM en français...")
                llm_start_time = datetime.now()
                llm_analysis = await self.analyze_ic_ratio_effectiveness_fr(period_data)
                llm_end_time = datetime.now()
                llm_duration = (llm_end_time - llm_start_time).total_seconds()

                if llm_analysis and len(str(llm_analysis).strip()) > 50:
                    # Save LLM analysis in French with processing duration
                    analysis_file = self.save_llm_analysis(period_name, llm_analysis, output_dir, processing_duration=llm_duration)
                    print(f"   📝 Analyse sauvegardée: {os.path.basename(analysis_file)} (durée: {llm_duration:.1f}s)")

                    results["saved_files"].extend([data_file, plot_file, bg_file, analysis_file])
                else:
                    print(f"   ⚠️  LLM analysis was empty or failed")
                    results["saved_files"].extend([data_file, plot_file, bg_file])

                # Add to summary
                trend_analysis = self.calculate_trend_strength(period_data)
                results["summary"][period_name] = {
                    "days_with_data": days_with_data,
                    "primary_recommendation": trend_analysis["primary_recommendation"],
                    "confidence": trend_analysis["confidence_score"],
                    "has_llm_analysis": bool(llm_analysis and len(str(llm_analysis).strip()) > 50)
                }

                results["periods_analyzed"].append(period_name)

            except Exception as e:
                print(f"   ❌ Error analyzing {period_name}: {e}")

        # Save summary
        summary_file = os.path.join(output_dir, f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        with open(summary_file, 'w') as f:
            yaml.dump(results, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        results["saved_files"].append(summary_file)
        print(f"\n✅ Analysis complete! {len(results['periods_analyzed'])} periods analyzed")
        print(f"📁 {len(results['saved_files'])} files saved to {output_dir}/")

        return results

    def _get_date_range(self, period_data: Dict[str, Any]) -> str:
        """Get date range string from period data."""
        days_data = period_data.get("days_data", [])
        if not days_data:
            return "No data"

        dates = [day["date"] for day in days_data]
        return f"{min(dates)} to {max(dates)}"

    # ---
    # --- Pattern Detection Methods for I:C Ratio Analysis
    # ---

    @summary_log_method()
    def detect_insufficient_bolus_pattern(self, day_data: Dict[str, Any]) -> bool:
        """
        Detect if bolus was too low (needs more insulin = decrease I:C ratio).

        Pattern: Correction boluses needed during the period.

        Args:
            day_data: Single day's data from period analysis

        Returns:
            True if pattern indicates insufficient meal bolus
        """
        # Check if correction boluses were needed
        correction_count = len(day_data.get("correction_boluses", []))
        return correction_count > 0

    @summary_log_method()
    def detect_excessive_bolus_pattern(self, day_data: Dict[str, Any]) -> bool:
        """
        Detect if bolus was too strong (needs less insulin = increase I:C ratio).

        Pattern: Basal suspended to 0 AND glucose under 80 AND no corrections.

        Args:
            day_data: Single day's data from period analysis

        Returns:
            True if pattern indicates excessive meal bolus
        """
        # Check for glucose under 80
        bg_response = day_data.get("bg_response")
        if not bg_response:
            return False

        has_lows = bg_response.get("under_80", 0) > 0

        # Check for basal suspension
        basal_summary = day_data.get("basal_summary")
        if not basal_summary:
            return False

        # Look for signs of basal suspension (very low average rate or rate changes)
        has_basal_suspension = (
            basal_summary.get("avg_rate", 1.0) < 0.1 or  # Very low average suggests suspension
            basal_summary.get("rate_changes", 0) > 2     # Multiple rate changes suggest temp adjustments
        )

        # Check that this wasn't caused by correction boluses
        correction_count = len(day_data.get("correction_boluses", []))
        no_corrections = correction_count == 0

        return has_lows and has_basal_suspension and no_corrections

    @summary_log_method()
    def detect_correction_overshot_pattern(self, day_data: Dict[str, Any]) -> bool:
        """
        Detect if correction bolus was too aggressive (flag only, can't control).

        Pattern: Correction boluses followed by basal suspension AND glucose under 80.

        Args:
            day_data: Single day's data from period analysis

        Returns:
            True if pattern indicates correction bolus overshot
        """
        # Must have correction boluses
        correction_count = len(day_data.get("correction_boluses", []))
        if correction_count == 0:
            return False

        # Check for glucose under 80
        bg_response = day_data.get("bg_response")
        if not bg_response:
            return False

        has_lows = bg_response.get("under_80", 0) > 0

        # Check for basal suspension
        basal_summary = day_data.get("basal_summary")
        if not basal_summary:
            return False

        has_basal_suspension = (
            basal_summary.get("avg_rate", 1.0) < 0.1 or
            basal_summary.get("rate_changes", 0) > 2
        )

        return has_lows and has_basal_suspension

    @summary_log_method()
    def analyze_pattern_consistency(self, period_data: Dict[str, Any], pattern_type: str, min_days: int = 3) -> Dict[str, Any]:
        """
        Analyze consistency of a pattern across multiple days.

        Args:
            period_data: Full period analysis data
            pattern_type: 'insufficient', 'excessive', or 'correction_overshot'
            min_days: Minimum days needed to confirm trend

        Returns:
            Pattern consistency analysis
        """
        days_data = period_data.get("days_data", [])

        # Select the appropriate detection method
        if pattern_type == "insufficient":
            detect_method = self.detect_insufficient_bolus_pattern
        elif pattern_type == "excessive":
            detect_method = self.detect_excessive_bolus_pattern
        elif pattern_type == "correction_overshot":
            detect_method = self.detect_correction_overshot_pattern
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")

        # Analyze each day
        pattern_days = []
        total_days = 0

        for day_data in days_data:
            total_days += 1
            if detect_method(day_data):
                pattern_days.append({
                    "date": day_data["date"],
                    "day_offset": day_data["day_offset"]
                })

        pattern_count = len(pattern_days)
        consistency_rate = pattern_count / total_days if total_days > 0 else 0

        # Determine if trend is confirmed
        trend_confirmed = (
            pattern_count >= min_days and  # Minimum occurrences
            consistency_rate >= 0.6       # At least 60% of days
        )

        return {
            "pattern_type": pattern_type,
            "total_days_analyzed": total_days,
            "pattern_days_count": pattern_count,
            "pattern_days": pattern_days,
            "consistency_rate": consistency_rate,
            "trend_confirmed": trend_confirmed,
            "min_days_threshold": min_days
        }

    @summary_log_method()
    def calculate_trend_strength(self, period_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall trend strength for I:C ratio adjustment needs.

        Args:
            period_data: Full period analysis data

        Returns:
            Trend strength analysis with recommendations
        """
        # Analyze all pattern types
        insufficient_analysis = self.analyze_pattern_consistency(period_data, "insufficient")
        excessive_analysis = self.analyze_pattern_consistency(period_data, "excessive")
        correction_overshot_analysis = self.analyze_pattern_consistency(period_data, "correction_overshot")

        # Calculate trend strength scores
        trends = {
            "insufficient_bolus": {
                "confirmed": insufficient_analysis["trend_confirmed"],
                "strength": insufficient_analysis["consistency_rate"],
                "occurrences": insufficient_analysis["pattern_days_count"]
            },
            "excessive_bolus": {
                "confirmed": excessive_analysis["trend_confirmed"],
                "strength": excessive_analysis["consistency_rate"],
                "occurrences": excessive_analysis["pattern_days_count"]
            },
            "correction_overshot": {
                "confirmed": correction_overshot_analysis["trend_confirmed"],
                "strength": correction_overshot_analysis["consistency_rate"],
                "occurrences": correction_overshot_analysis["pattern_days_count"]
            }
        }

        # Determine primary recommendation
        primary_recommendation = "no_adjustment"
        if trends["insufficient_bolus"]["confirmed"]:
            primary_recommendation = "decrease_ic_ratio"  # More insulin
        elif trends["excessive_bolus"]["confirmed"]:
            primary_recommendation = "increase_ic_ratio"   # Less insulin

        # Calculate confidence score
        strongest_trend = max(
            trends["insufficient_bolus"]["strength"],
            trends["excessive_bolus"]["strength"]
        )

        return {
            "period_name": period_data.get("period_name"),
            "trends": trends,
            "primary_recommendation": primary_recommendation,
            "confidence_score": strongest_trend,
            "total_days_analyzed": period_data.get("days_analyzed", 0)
        }

    @summary_log_method()
    def detect_ratio_changes(self, period_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect I:C ratio changes between days in the period data.

        Args:
            period_data: Full period analysis data

        Returns:
            List of detected ratio changes with dates
        """
        days_data = period_data.get("days_data", [])
        ratio_changes = []

        prev_ratio = None
        prev_date = None

        for day_data in days_data:
            # Get the I:C ratio(s) used for this day
            bolus_events = day_data.get("bolus_events", [])
            if not bolus_events:
                continue

            # Use the first bolus event's ratio as representative
            current_ratio = bolus_events[0].get("ic_ratio")
            current_date = day_data["date"]

            if prev_ratio is not None and current_ratio != prev_ratio:
                ratio_changes.append({
                    "change_date": current_date,
                    "previous_date": prev_date,
                    "old_ratio": prev_ratio,
                    "new_ratio": current_ratio,
                    "change_direction": "increase" if current_ratio > prev_ratio else "decrease",
                    "change_magnitude": abs(current_ratio - prev_ratio) if current_ratio and prev_ratio else 0
                })

            prev_ratio = current_ratio
            prev_date = current_date

        return ratio_changes

    @summary_log_method()
    def evaluate_change_effectiveness(self, period_data: Dict[str, Any], ratio_change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate effectiveness of a detected I:C ratio change.

        Args:
            period_data: Full period analysis data
            ratio_change: Ratio change info from detect_ratio_changes()

        Returns:
            Effectiveness analysis of the ratio change
        """
        days_data = period_data.get("days_data", [])

        # Split days into before and after the change
        change_date = ratio_change["change_date"]
        before_days = []
        after_days = []

        for day_data in days_data:
            if day_data["date"] < change_date:
                before_days.append(day_data)
            elif day_data["date"] >= change_date:
                after_days.append(day_data)

        if len(before_days) == 0 or len(after_days) == 0:
            return {"error": "Insufficient data before/after change"}

        # Analyze patterns before and after
        def analyze_days_patterns(days_list):
            insufficient_count = sum(1 for day in days_list if self.detect_insufficient_bolus_pattern(day))
            excessive_count = sum(1 for day in days_list if self.detect_excessive_bolus_pattern(day))
            correction_overshot_count = sum(1 for day in days_list if self.detect_correction_overshot_pattern(day))

            # Average glucose metrics
            avg_corrections = sum(len(day.get("correction_boluses", [])) for day in days_list) / len(days_list)

            bg_metrics = []
            for day in days_list:
                if day.get("bg_response"):
                    bg_metrics.append(day["bg_response"])

            if bg_metrics:
                avg_glucose = sum(bg["avg_bg"] for bg in bg_metrics) / len(bg_metrics)
                avg_lows = sum(bg["under_80"] for bg in bg_metrics) / len(bg_metrics)
                avg_highs = sum(bg["over_200"] for bg in bg_metrics) / len(bg_metrics)
            else:
                avg_glucose = None
                avg_lows = 0
                avg_highs = 0

            return {
                "days_count": len(days_list),
                "insufficient_pattern_days": insufficient_count,
                "excessive_pattern_days": excessive_count,
                "correction_overshot_days": correction_overshot_count,
                "avg_corrections_per_day": avg_corrections,
                "avg_glucose": avg_glucose,
                "avg_lows_per_day": avg_lows,
                "avg_highs_per_day": avg_highs
            }

        before_analysis = analyze_days_patterns(before_days)
        after_analysis = analyze_days_patterns(after_days)

        # Calculate improvement metrics
        correction_improvement = before_analysis["avg_corrections_per_day"] - after_analysis["avg_corrections_per_day"]
        lows_improvement = before_analysis["avg_lows_per_day"] - after_analysis["avg_lows_per_day"]
        highs_improvement = before_analysis["avg_highs_per_day"] - after_analysis["avg_highs_per_day"]

        # Determine effectiveness
        effectiveness = "unclear"
        if ratio_change["change_direction"] == "decrease":  # More insulin
            # Should reduce corrections and highs
            if correction_improvement > 0 and highs_improvement > 0:
                effectiveness = "effective"
            elif lows_improvement < -0.5:  # Increased lows significantly
                effectiveness = "excessive"
        elif ratio_change["change_direction"] == "increase":  # Less insulin
            # Should reduce lows
            if lows_improvement > 0:
                effectiveness = "effective"
            elif correction_improvement < -0.5:  # Increased corrections significantly
                effectiveness = "insufficient"

        return {
            "ratio_change": ratio_change,
            "before_period": before_analysis,
            "after_period": after_analysis,
            "improvements": {
                "corrections_per_day": correction_improvement,
                "lows_per_day": lows_improvement,
                "highs_per_day": highs_improvement
            },
            "effectiveness": effectiveness
        }

    # ---
    # --- LLM Generation Methods for I:C Ratio Analysis
    # ---

    async def analyze_ic_ratio_effectiveness(self, period_analysis_data: Dict[str, Any], language: str = "French") -> str:
        """
        Analyze I:C ratio effectiveness for a specific period across multiple days.

        You are a diabetes management expert. Review the period analysis data and provide specific I:C ratio recommendations.

        The period_analysis_data contains clinical patterns detected using these criteria:
        - Insufficient bolus pattern: Correction boluses needed = I:C ratio too high (need more insulin)
        - Excessive bolus pattern: Basal suspended + glucose under 80 = I:C ratio too low (need less insulin)
        - Historical changes: Learn from previous adjustments

        Provide clear assessment and specific adjustment recommendations with clinical rationale.
        Be conservative - small changes are safer. Consider safety to avoid hypoglycemia.

        **IMPORTANT: Respond in French (français). Provide your entire analysis in French.**

        If a different language is specified in the language parameter, respond in that language instead.
        """
        ...

    async def analyze_ic_ratio_effectiveness_fr(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Analysez l'efficacité du ratio I:C pour une période spécifique sur plusieurs jours.

        Vous êtes un expert en gestion du diabète. Examinez les données d'analyse de période et fournissez des recommandations spécifiques pour le ratio I:C.

        Les données period_analysis_data contiennent des patterns cliniques détectés selon ces critères :
        - Pattern bolus insuffisant : Bolus de correction automatiques nécessaires par la pompe en boucle fermée = ratio I:C trop élevé (besoin de plus d'insuline)
        - Pattern bolus excessif : Basale suspendue + glucose sous 80 = ratio I:C trop bas (besoin de moins d'insuline)
        - Changements historiques : Apprenez des ajustements précédents

        IMPORTANT : Les "bolus de correction" sont automatiquement administrés par la pompe en boucle fermée (système automatique), pas par l'utilisateur. Ils indiquent que le bolus de repas initial était insuffisant.

        Fournissez une évaluation claire et des recommandations d'ajustement spécifiques avec une justification clinique.
        Soyez conservateur - les petits changements sont plus sûrs. Considérez la sécurité pour éviter l'hypoglycémie.

        **Répondez entièrement en français.**
        """
        ...

    async def identify_ic_ratio_patterns(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Identify patterns in I:C ratio usage and glucose responses.

        Uses clinical pattern detection to identify specific trends in diabetes management.

        Args:
            period_analysis_data: Structured period data

        Returns:
            Pattern analysis focusing on I:C ratio trends with clinical evidence
        """
        # Analyze each pattern type individually
        insufficient_analysis = self.analyze_pattern_consistency(period_analysis_data, "insufficient")
        excessive_analysis = self.analyze_pattern_consistency(period_analysis_data, "excessive")
        correction_overshot_analysis = self.analyze_pattern_consistency(period_analysis_data, "correction_overshot")

        # Get detailed day-by-day patterns
        daily_patterns = []
        for day_data in period_analysis_data.get("days_data", []):
            patterns = {
                "date": day_data["date"],
                "day_offset": day_data["day_offset"],
                "insufficient": self.detect_insufficient_bolus_pattern(day_data),
                "excessive": self.detect_excessive_bolus_pattern(day_data),
                "correction_overshot": self.detect_correction_overshot_pattern(day_data),
                "corrections_count": len(day_data.get("correction_boluses", [])),
                "glucose_lows": day_data.get("bg_response", {}).get("under_80", 0),
                "glucose_highs": day_data.get("bg_response", {}).get("over_200", 0),
                "ic_ratios_used": [b.get("ic_ratio") for b in day_data.get("bolus_events", []) if b.get("ic_ratio")]
            }
            daily_patterns.append(patterns)

        return f"""
Pattern Analysis for {period_analysis_data.get('period_name')}:

INSUFFICIENT BOLUS PATTERN:
- Confirmed: {insufficient_analysis['trend_confirmed']}
- Occurrence rate: {insufficient_analysis['consistency_rate']:.1%}
- Days detected: {insufficient_analysis['pattern_days_count']}/{insufficient_analysis['total_days_analyzed']}

EXCESSIVE BOLUS PATTERN:
- Confirmed: {excessive_analysis['trend_confirmed']}
- Occurrence rate: {excessive_analysis['consistency_rate']:.1%}
- Days detected: {excessive_analysis['pattern_days_count']}/{excessive_analysis['total_days_analyzed']}

CORRECTION OVERSHOT PATTERN:
- Confirmed: {correction_overshot_analysis['trend_confirmed']}
- Occurrence rate: {correction_overshot_analysis['consistency_rate']:.1%}
- Days detected: {correction_overshot_analysis['pattern_days_count']}/{correction_overshot_analysis['total_days_analyzed']}

Daily Pattern Details: {daily_patterns}

Analyze these clinical patterns and identify the most significant I:C ratio trends.
        """

    async def suggest_ic_ratio_adjustments(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Suggest specific I:C ratio adjustments based on clinical pattern analysis.

        Uses evidence-based criteria to provide concrete adjustment recommendations
        with safety considerations.

        Args:
            period_analysis_data: Structured period data

        Returns:
            Specific I:C ratio adjustment recommendations with clinical rationale
        """
        # Get comprehensive trend analysis
        trend_analysis = self.calculate_trend_strength(period_analysis_data)

        # Detect historical changes and their effectiveness
        ratio_changes = self.detect_ratio_changes(period_analysis_data)
        change_evaluations = []
        for change in ratio_changes:
            evaluation = self.evaluate_change_effectiveness(period_analysis_data, change)
            change_evaluations.append(evaluation)

        # Get current I:C ratios being used
        current_ratios = []
        for day_data in period_analysis_data.get("days_data", []):
            for bolus in day_data.get("bolus_events", []):
                if bolus.get("ic_ratio"):
                    current_ratios.append(bolus["ic_ratio"])

        unique_ratios = list(set(current_ratios)) if current_ratios else []

        # Calculate safety metrics
        total_lows = sum(
            day.get("bg_response", {}).get("under_80", 0)
            for day in period_analysis_data.get("days_data", [])
        )
        total_corrections = sum(
            len(day.get("correction_boluses", []))
            for day in period_analysis_data.get("days_data", [])
        )

        adjustment_context = {
            "trend_analysis": trend_analysis,
            "current_ratios": unique_ratios,
            "historical_changes": change_evaluations,
            "safety_metrics": {
                "total_hypoglycemic_events": total_lows,
                "total_corrections_needed": total_corrections,
                "days_analyzed": trend_analysis["total_days_analyzed"]
            }
        }

        return f"""
I:C Ratio Adjustment Recommendations for {period_analysis_data.get('period_name')}:

CURRENT STATUS:
- Current I:C ratios: {unique_ratios}g/U
- Primary recommendation: {trend_analysis['primary_recommendation']}
- Confidence level: {trend_analysis['confidence_score']:.1%}

CLINICAL EVIDENCE:
- Insufficient bolus confirmed: {trend_analysis['trends']['insufficient_bolus']['confirmed']}
- Excessive bolus confirmed: {trend_analysis['trends']['excessive_bolus']['confirmed']}
- Correction overshots: {trend_analysis['trends']['correction_overshot']['confirmed']}

SAFETY METRICS:
- Hypoglycemic events: {total_lows} over {trend_analysis['total_days_analyzed']} days
- Corrections needed: {total_corrections} over {trend_analysis['total_days_analyzed']} days

HISTORICAL CHANGES:
- Recent adjustments: {len(ratio_changes)}
- Change effectiveness: {[e['effectiveness'] for e in change_evaluations]}

Provide specific I:C ratio adjustment recommendations with clinical rationale and safety considerations.
        """

    async def generate_period_summary(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Generate a comprehensive summary of I:C ratio performance for this period.

        Provides executive summary with key clinical insights and actionable recommendations.

        Args:
            period_analysis_data: Structured period data

        Returns:
            Executive summary of I:C ratio effectiveness for this period
        """
        # Get all analysis components
        trend_analysis = self.calculate_trend_strength(period_analysis_data)
        ratio_changes = self.detect_ratio_changes(period_analysis_data)

        # Calculate overall period metrics
        total_days = len(period_analysis_data.get("days_data", []))
        total_bolus_events = sum(
            len(day.get("bolus_events", []))
            for day in period_analysis_data.get("days_data", [])
        )
        total_corrections = sum(
            len(day.get("correction_boluses", []))
            for day in period_analysis_data.get("days_data", [])
        )
        total_lows = sum(
            day.get("bg_response", {}).get("under_80", 0)
            for day in period_analysis_data.get("days_data", [])
        )

        # Get glucose averages
        glucose_averages = []
        for day in period_analysis_data.get("days_data", []):
            bg_response = day.get("bg_response")
            if bg_response and bg_response.get("avg_bg"):
                glucose_averages.append(bg_response["avg_bg"])

        avg_glucose = sum(glucose_averages) / len(glucose_averages) if glucose_averages else None

        # Get I:C ratio usage
        all_ratios = []
        for day in period_analysis_data.get("days_data", []):
            for bolus in day.get("bolus_events", []):
                if bolus.get("ic_ratio"):
                    all_ratios.append(bolus["ic_ratio"])

        summary_data = {
            "period_name": period_analysis_data.get("period_name"),
            "analysis_period": f"{total_days} days",
            "total_meals": total_bolus_events,
            "total_corrections": total_corrections,
            "total_hypoglycemic_events": total_lows,
            "average_glucose": avg_glucose,
            "ic_ratios_used": list(set(all_ratios)),
            "trend_analysis": trend_analysis,
            "recent_changes": len(ratio_changes),
            "primary_recommendation": trend_analysis["primary_recommendation"],
            "recommendation_confidence": trend_analysis["confidence_score"]
        }

        return f"""
EXECUTIVE SUMMARY: {summary_data['period_name']} I:C Ratio Analysis

PERIOD OVERVIEW:
- Analysis period: {summary_data['analysis_period']}
- Total meals analyzed: {summary_data['total_meals']}
- I:C ratios used: {summary_data['ic_ratios_used']}g/U
- Average glucose response: {summary_data['average_glucose']:.0f}mg/dL

CLINICAL PERFORMANCE:
- Corrections needed: {summary_data['total_corrections']}
- Hypoglycemic events: {summary_data['total_hypoglycemic_events']}
- Pattern confidence: {summary_data['recommendation_confidence']:.1%}

RECOMMENDATION:
- Primary action: {summary_data['primary_recommendation']}
- Recent changes: {summary_data['recent_changes']} ratio adjustments made

TREND ANALYSIS:
{summary_data['trend_analysis']}

Generate a comprehensive diabetes management summary with actionable insights.
        """


# Convenience function for quick analysis
def analyze_period_ic_ratios(filepath: str, period_name: str, days_back: int = 7) -> Dict[str, Any]:
    """
    Quick function to get structured period data for I:C ratio analysis.

    Args:
        filepath: Path to Carelink CSV file
        period_name: Period to analyze ('Breakfast', 'Lunch', etc.)
        days_back: Number of days to include

    Returns:
        Structured period data ready for LLM analysis
    """
    from nooa import get_llm_client
    llm = get_llm_client()
    agent = RatioAnalysisAgent("analysis_patient", llm)
    return agent.get_period_analysis_data(filepath, period_name, days_back)