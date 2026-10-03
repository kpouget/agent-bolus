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
import carelink_parser as _default_parser
from data_logger import summary_log_method


class RatioAnalysisAgent(DiabetesAgent):
    """
    AI-powered agent for analyzing I:C ratio effectiveness.

    Focuses on one period at a time (e.g., "Breakfast") across multiple days,
    with day -1 being most important for analysis.
    """

    def __init__(self, patient_id: str = "analysis_patient", llm=None, parser=None):
        # Initialize the parent DiabetesAgent
        if llm is not None:
            super().__init__(patient_id, llm)
        else:
            super().__init__(patient_id)
        self.parser = parser or _default_parser

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
        bolus_events = self.parser.parse_bolus_events(filepath, days_back=days_back)

        if not bolus_events:
            return {"error": "No bolus events found", "period": period_name}

        # Organize data by periods
        all_periods_data = self.get_all_periods_for_days(bolus_events, days=days_back)

        # Filter to only the target period for efficient extraction
        target_period_data = {}
        for date, periods in all_periods_data.items():
            if period_name in periods:
                target_period_data[date] = {period_name: periods[period_name]}

        # Extract supplementary data for target period only
        bg_data = self.parser.extract_bg_for_periods(filepath, target_period_data)
        correction_data = self.parser.extract_correction_boluses(filepath, target_period_data)
        basal_data = self.parser.extract_basal_for_periods(filepath, target_period_data)

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

        filename = f"bg_data_{days_analyzed}days.yaml"
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

        # Create period subdirectory with numeric prefix
        prefix = self._get_period_prefix(period_name)
        period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
        os.makedirs(period_dir, exist_ok=True)

        filename = "insuline_data_7days.yml"
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

        # Create period subdirectory with numeric prefix
        prefix = self._get_period_prefix(period_name)
        period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
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
        bg_data = self.parser.extract_bg_for_periods(filepath, all_periods_data)

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
    def save_llm_analysis(self, period_name: str, llm_analysis: str, output_dir: str = "output", processing_duration: float = None, period_data: Dict[str, Any] = None) -> str:
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
        # Create period subdirectory with numeric prefix
        prefix = self._get_period_prefix(period_name)
        period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
        os.makedirs(period_dir, exist_ok=True)

        filename = "llm_analysis.md"
        filepath = os.path.join(period_dir, filename)

        # Save as Markdown for readability with optional duration
        duration_info = ""
        if processing_duration is not None:
            duration_info = f"**Durée d'exécution:** {processing_duration:.1f} secondes\n"

        # Get latest sensor timestamp from the period data
        if period_data:
            latest_sensor_info = self.get_latest_sensor_timestamp(period_data)
        else:
            latest_sensor_info = "**Dernière glycémie capteur:** Non disponible"

        content = f"""# Analyse du Ratio I:C - {period_name}

**Généré le:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Période:** {period_name}
{latest_sensor_info}
{duration_info}

## Analyse Clinique

{llm_analysis}

---
*Généré par RatioAnalysisAgent (analyse en français)*
"""

        with open(filepath, 'w') as f:
            f.write(content)

        return filepath

    def get_latest_sensor_timestamp(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Extract the timestamp of the most recent sensor glucose reading.

        Args:
            period_analysis_data: Period analysis data

        Returns:
            Formatted timestamp string of most recent sensor reading
        """
        latest_timestamp = None
        latest_datetime = None

        # Look through all days to find the most recent sensor reading
        for day_data in period_analysis_data.get("days_data", []):
            bg_response = day_data.get("bg_response")
            if not bg_response:
                continue

            # Check if we have time_window information
            time_window = bg_response.get("time_window", "")
            if time_window and "-" in time_window:
                # Extract the end time (most recent)
                try:
                    date = day_data.get("date", "")
                    end_time = time_window.split("-")[1]
                    full_timestamp = f"{date} {end_time}"

                    # Convert to datetime for comparison
                    from datetime import datetime
                    dt = datetime.strptime(full_timestamp, "%Y/%m/%d %H:%M:%S")

                    if latest_datetime is None or dt > latest_datetime:
                        latest_datetime = dt
                        latest_timestamp = full_timestamp

                except Exception as e:
                    # Debug: print what failed
                    print(f"   ⚠️  Failed to parse timestamp: {date} {end_time} - {e}")
                    continue

        # If we didn't find it in bg_response, try reading from the detailed BG data
        if not latest_timestamp:
            period_name = period_analysis_data.get("period_name", "")
            try:
                # Try to get the latest from the most recent day's data
                days_data = period_analysis_data.get("days_data", [])
                if days_data:
                    # Get the most recent day (day_offset closest to 0, which is -1, -2, etc.)
                    most_recent_day = max(days_data, key=lambda x: x.get("day_offset", -999))
                    bg_response = most_recent_day.get("bg_response")
                    if bg_response:
                        time_window = bg_response.get("time_window", "")
                        if time_window:
                            # Extract just the latest time from this day
                            date = most_recent_day.get("date", "")
                            if "-" in time_window:
                                end_time = time_window.split("-")[1].strip()
                            else:
                                end_time = time_window.strip()
                            latest_timestamp = f"{date} {end_time}"
                            print(f"   📍 Found sensor timestamp from most recent day: {latest_timestamp}")

            except Exception as e:
                print(f"   ⚠️  Fallback timestamp extraction failed: {e}")

        if latest_timestamp:
            try:
                for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
                    try:
                        ts = datetime.strptime(latest_timestamp, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    ts = None

                if ts:
                    delta = datetime.now() - ts
                    total_hours = int(delta.total_seconds() // 3600)
                    if total_hours < 1:
                        minutes = int(delta.total_seconds() // 60)
                        delta_str = f"il y a {minutes}min"
                    elif total_hours < 48:
                        delta_str = f"il y a {total_hours}h"
                    else:
                        days = total_hours // 24
                        delta_str = f"il y a {days}j"
                    return f"**Dernière glycémie capteur:** {latest_timestamp} ({delta_str})"
            except Exception:
                pass
            return f"**Dernière glycémie capteur:** {latest_timestamp}"
        else:
            return "**Dernière glycémie capteur:** Non disponible"

    def extract_conclusion_from_analysis(self, llm_analysis: str) -> str:
        """
        Extract the conclusion section from LLM analysis.

        Args:
            llm_analysis: Full LLM analysis text

        Returns:
            Extracted conclusion text
        """
        # Look for conclusion markers in French
        conclusion_markers = [
            "## Conclusion",
            "## Recommandation",
            "## Recommandations",
            "## Synthèse",
            "## Résumé",
            "**Conclusion**",
            "**Recommandation**"
        ]

        lines = llm_analysis.split('\n')
        conclusion_lines = []
        in_conclusion = False

        for line in lines:
            # Check if we're entering a conclusion section
            for marker in conclusion_markers:
                if marker.lower() in line.lower():
                    in_conclusion = True
                    conclusion_lines.append(line)
                    break
            else:
                # If we're in conclusion and hit another ## header, stop
                if in_conclusion and line.strip().startswith('## ') and not any(marker.lower() in line.lower() for marker in conclusion_markers):
                    break
                elif in_conclusion:
                    conclusion_lines.append(line)

        # If no specific conclusion section found, take the last paragraph
        if not conclusion_lines:
            paragraphs = [p.strip() for p in llm_analysis.split('\n\n') if p.strip()]
            if paragraphs:
                conclusion_lines = paragraphs[-1].split('\n')

        conclusion = '\n'.join(conclusion_lines).strip()

        # If still empty, create a summary line
        if not conclusion:
            conclusion = "Analyse terminée - voir le rapport complet pour les détails."

        return conclusion

    @summary_log_method()
    def save_conclusion(self, period_name: str, conclusion_text: str, output_dir: str = "output", period_data: Dict[str, Any] = None) -> str:
        """
        Save period conclusion to a dedicated file.

        Args:
            period_name: Name of the period
            conclusion_text: Extracted conclusion
            output_dir: Output directory

        Returns:
            Path to saved conclusion file
        """
        # Create period subdirectory with numeric prefix
        prefix = self._get_period_prefix(period_name)
        period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
        os.makedirs(period_dir, exist_ok=True)

        filename = "conclusion.md"
        filepath = os.path.join(period_dir, filename)

        # Get latest sensor timestamp
        if period_data:
            latest_sensor_info = self.get_latest_sensor_timestamp(period_data)
        else:
            latest_sensor_info = "**Dernière glycémie capteur:** Non disponible"

        # Save conclusion with metadata
        content = f"""# Conclusion - {period_name}

**Généré le:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Période:** {period_name}
{latest_sensor_info}

{conclusion_text}
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    @summary_log_method()
    def aggregate_all_conclusions(self, output_dir: str, periods_analyzed: list) -> str:
        """
        Create a single file with all period conclusions.

        Args:
            output_dir: Base output directory
            periods_analyzed: List of periods that were analyzed

        Returns:
            Path to aggregated conclusions file
        """
        filename = "all_conclusions.md"
        filepath = os.path.join(output_dir, filename)

        content = f"""# Analyse des Ratios I:C - Toutes les Périodes

**Généré le:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Périodes analysées:** {', '.join(periods_analyzed)}

---

"""

        # Collect conclusions from each period
        for period_name in periods_analyzed:
            prefix = self._get_period_prefix(period_name)
            period_dir = os.path.join(output_dir, f"{prefix}_{period_name.lower()}")
            conclusion_file = os.path.join(period_dir, "conclusion.md")

            if os.path.exists(conclusion_file):
                try:
                    with open(conclusion_file, 'r', encoding='utf-8') as f:
                        conclusion_content = f.read()

                    # Extract just the conclusion text (skip metadata)
                    lines = conclusion_content.split('\n')
                    content_start = False
                    period_conclusion = []

                    for line in lines:
                        if content_start:
                            period_conclusion.append(line)
                        elif line.strip() == "":
                            content_start = True

                    if period_conclusion:
                        content += f"## {period_name}\n\n"
                        content += '\n'.join(period_conclusion).strip()
                        content += "\n\n---\n\n"

                except Exception as e:
                    content += f"## {period_name}\n\nErreur lors de la lecture de la conclusion: {e}\n\n---\n\n"
            else:
                content += f"## {period_name}\n\nAucune conclusion disponible.\n\n---\n\n"

        content += f"""
*Rapport généré automatiquement par RatioAnalysisAgent*
*Prêt pour envoi par email*
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def get_historical_conclusions(self, period_name: str, base_output_dir: str = "generated", days_back: int = 7) -> str:
        """
        Retrieve historical conclusions for a given period from previous analyses.

        Args:
            period_name: Name of the period to get history for
            base_output_dir: Base directory where previous analyses are stored
            days_back: How many days back to look for conclusions

        Returns:
            Formatted string with historical conclusions
        """
        if not os.path.exists(base_output_dir):
            return ""

        historical_conclusions = []
        prefix = self._get_period_prefix(period_name)

        # Look through timestamped directories (YYMMDD_HHMM format)
        try:
            for dir_name in sorted(os.listdir(base_output_dir), reverse=True)[:days_back]:
                dir_path = os.path.join(base_output_dir, dir_name)
                if not os.path.isdir(dir_path):
                    continue

                period_dir = os.path.join(dir_path, f"{prefix}_{period_name.lower()}")
                conclusion_file = os.path.join(period_dir, "conclusion.md")

                if os.path.exists(conclusion_file):
                    try:
                        with open(conclusion_file, 'r', encoding='utf-8') as f:
                            conclusion_content = f.read()

                        # Extract the conclusion text
                        lines = conclusion_content.split('\n')
                        for i, line in enumerate(lines):
                            if line.startswith('**Généré le:**'):
                                date_info = line.replace('**Généré le:**', '').strip()
                                # Find the actual conclusion text (skip headers)
                                conclusion_start = i + 3  # Skip date, period, empty line
                                conclusion_text = '\n'.join(lines[conclusion_start:]).strip()
                                if conclusion_text:
                                    historical_conclusions.append(f"**{date_info}:** {conclusion_text}")
                                break

                    except Exception:
                        continue

        except Exception:
            pass

        if historical_conclusions:
            return "\n\n### Conclusions des Analyses Précédentes:\n\n" + "\n\n".join(historical_conclusions[:3])  # Limit to 3 most recent
        else:
            return ""

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
                llm_analysis = await self.analyze_ic_ratio_effectiveness_fr(period_data, output_dir)
                llm_end_time = datetime.now()
                llm_duration = (llm_end_time - llm_start_time).total_seconds()

                if llm_analysis and len(str(llm_analysis).strip()) > 50:
                    # Save LLM analysis in French with processing duration
                    analysis_file = self.save_llm_analysis(period_name, llm_analysis, output_dir, processing_duration=llm_duration, period_data=period_data)
                    print(f"   📝 Analyse sauvegardée: {os.path.basename(analysis_file)} (durée: {llm_duration:.1f}s)")

                    # Extract and save conclusion
                    conclusion_text = self.extract_conclusion_from_analysis(llm_analysis)
                    conclusion_file = self.save_conclusion(period_name, conclusion_text, output_dir, period_data=period_data)
                    print(f"   📄 Conclusion sauvegardée: {os.path.basename(conclusion_file)}")

                    results["saved_files"].extend([data_file, plot_file, bg_file, analysis_file, conclusion_file])
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
                import traceback
                traceback.print_exc()

        # Save summary
        summary_file = os.path.join(output_dir, f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        with open(summary_file, 'w') as f:
            yaml.dump(results, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        results["saved_files"].append(summary_file)

        # Generate aggregated conclusions file
        if results["periods_analyzed"]:
            print(f"\n📋 Generating aggregated conclusions...")
            conclusions_file = self.aggregate_all_conclusions(output_dir, results["periods_analyzed"])
            results["saved_files"].append(conclusions_file)
            print(f"   📧 All conclusions: {os.path.basename(conclusions_file)} (ready for email)")

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

    async def analyze_ic_ratio_effectiveness_fr(self, period_analysis_data: Dict[str, Any], base_output_dir: str = "generated") -> str:
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
        # Get historical conclusions for context
        period_name = period_analysis_data.get('period_name', '')
        historical_context = self.get_historical_conclusions(period_name, base_output_dir)

        # Prepare analysis data with error handling
        try:
            pattern_analysis = await self.identify_ic_ratio_patterns(period_analysis_data)
            if pattern_analysis is None:
                pattern_analysis = "Erreur lors de l'analyse des patterns."
        except Exception as e:
            pattern_analysis = f"Erreur lors de l'analyse des patterns: {e}"

        try:
            adjustment_context = self.calculate_adjustment_context(period_analysis_data)
            if adjustment_context is None:
                adjustment_context = "Erreur lors du calcul du contexte d'ajustement."
        except Exception as e:
            adjustment_context = f"Erreur lors du calcul du contexte: {e}"

        # Create a comprehensive analysis prompt
        pattern_analysis = await self.identify_ic_ratio_patterns(period_analysis_data)
        adjustment_context = self.calculate_adjustment_context(period_analysis_data)

        # For now, return a structured analysis (NOOA framework will handle LLM generation via method docstrings)
        return await self.perform_ic_ratio_analysis_fr(
            period_name=period_name,
            pattern_analysis=pattern_analysis,
            adjustment_context=adjustment_context,
            historical_context=historical_context
        )

    async def perform_ic_ratio_analysis_fr(self, period_name: str, pattern_analysis: str, adjustment_context: str, historical_context: str) -> str:
        """
        Analysez l'efficacité du ratio I:C pour la période spécifique sur plusieurs jours.

        Vous êtes un expert en gestion du diabète. Examinez les données d'analyse de période et fournissez des recommandations spécifiques pour le ratio I:C.

        Les données contiennent des patterns cliniques détectés selon ces critères :
        - Pattern bolus insuffisant : Bolus de correction automatiques nécessaires par la pompe en boucle fermée = ratio I:C trop élevé (besoin de plus d'insuline)
        - Pattern bolus excessif : Basale suspendue + glucose sous 80 = ratio I:C trop bas (besoin de moins d'insuline)
        - Changements historiques : Apprenez des ajustements précédents

        IMPORTANT : Les "bolus de correction" sont automatiquement administrés par la pompe en boucle fermée (système automatique), pas par l'utilisateur. Ils indiquent que le bolus de repas initial était insuffisant.

        Fournissez une analyse complète incluant:
        1. Évaluation des patterns détectés
        2. Recommandations spécifiques d'ajustement du ratio I:C
        3. Justification clinique
        4. Considérations de sécurité

        Terminez votre analyse par une section "## Conclusion" avec vos recommandations principales.

        Utilisez les données d'analyse fournies et le contexte historique pour votre analyse.

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
        # Analyze each pattern type individually with error handling
        try:
            insufficient_analysis = self.analyze_pattern_consistency(period_analysis_data, "insufficient")
            if insufficient_analysis is None:
                insufficient_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}
        except Exception as e:
            insufficient_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}

        try:
            excessive_analysis = self.analyze_pattern_consistency(period_analysis_data, "excessive")
            if excessive_analysis is None:
                excessive_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}
        except Exception as e:
            excessive_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}

        try:
            correction_overshot_analysis = self.analyze_pattern_consistency(period_analysis_data, "correction_overshot")
            if correction_overshot_analysis is None:
                correction_overshot_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}
        except Exception as e:
            correction_overshot_analysis = {"trend_confirmed": False, "consistency_rate": 0.0, "pattern_days_count": 0, "total_days_analyzed": 0}

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
                "glucose_lows": (day_data.get("bg_response") or {}).get("under_80", 0),
                "glucose_highs": (day_data.get("bg_response") or {}).get("over_200", 0),
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
            (day.get("bg_response") or {}).get("under_80", 0)
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

    def calculate_adjustment_context(self, period_analysis_data: Dict[str, Any]) -> str:
        """
        Calculate adjustment context for LLM analysis.

        Args:
            period_analysis_data: Structured period data

        Returns:
            Formatted adjustment context string
        """
        # Get comprehensive trend analysis with error handling
        try:
            trend_analysis = self.calculate_trend_strength(period_analysis_data)
            if trend_analysis is None:
                trend_analysis = {"total_days_analyzed": 0, "primary_recommendation": "Données insuffisantes", "confidence_score": 0.0}
        except Exception as e:
            trend_analysis = {"total_days_analyzed": 0, "primary_recommendation": "Erreur d'analyse", "confidence_score": 0.0}

        # Detect historical changes and their effectiveness with error handling
        try:
            ratio_changes = self.detect_ratio_changes(period_analysis_data)
            if ratio_changes is None:
                ratio_changes = []
        except Exception as e:
            ratio_changes = []

        change_evaluations = []
        for change in ratio_changes:
            try:
                evaluation = self.evaluate_change_effectiveness(period_analysis_data, change)
                if evaluation is not None:
                    change_evaluations.append(evaluation)
            except Exception as e:
                continue

        # Get current I:C ratios being used
        current_ratios = []
        for day_data in period_analysis_data.get("days_data", []):
            for bolus in day_data.get("bolus_events", []):
                if bolus.get("ic_ratio"):
                    current_ratios.append(bolus["ic_ratio"])

        unique_ratios = list(set(current_ratios)) if current_ratios else []

        # Calculate safety metrics
        total_lows = sum(
            (day.get("bg_response") or {}).get("under_80", 0)
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
Trend Analysis: {trend_analysis}
Current Ratios: {unique_ratios}
Safety Metrics: {total_lows} lows, {total_corrections} corrections
Historical Changes: {len(change_evaluations)} changes detected
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
        adjustment_context = self.calculate_adjustment_context(period_analysis_data)

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
            (day.get("bg_response") or {}).get("under_80", 0)
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