#!/usr/bin/env python3
"""
GlookoXT JSON Data Parser
Parse GlookoXT JSON files (from GET_COLLECTED_DATA) and extract glucose readings,
bolus events, correction boluses, and basal data.

Exposes the same function signatures as carelink_parser.py so the two are interchangeable.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

from diabetes_agent import GlucoseReading
from carelink_parser import BolusEvent, BasalEvent

LOCAL_TS_FMT = "%Y/%m/%d %H:%M:%S"


def _load_records(filepath: str, days_back: int = None):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tz_name = None
    profile = data.get("profile", {})
    if isinstance(profile, dict):
        tz_name = profile.get("timezone") or profile.get("profile", {}).get("timezone")

    local_tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("Europe/Paris")

    cutoff = None
    if days_back is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    records = data.get("records", [])
    parsed = []
    for rec in records:
        recorded_at = rec.get("recorded_at")
        if not recorded_at:
            continue
        try:
            dt_utc = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if cutoff and dt_utc < cutoff:
            continue
        dt_local = dt_utc.astimezone(local_tz)
        parsed.append((rec, dt_local))

    parsed.sort(key=lambda x: x[1])
    return parsed, local_tz


def _to_float(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return None


def _to_int(val):
    f = _to_float(val)
    return int(f) if f is not None else None


def _local_ts(dt):
    return dt.strftime(LOCAL_TS_FMT)


def _local_date(dt):
    return dt.strftime("%Y/%m/%d")


def _local_time(dt):
    return dt.strftime("%H:%M:%S")


def parse_carelink_csv(filepath: str, days_back: int = 7) -> List[GlucoseReading]:
    """Parse GlookoXT JSON and return glucose readings (same interface as carelink_parser)."""
    records, _ = _load_records(filepath, days_back)
    readings = []

    for rec, dt in records:
        cgm = _to_float(rec.get("glycemia_cgm"))
        if cgm and cgm > 0:
            readings.append(GlucoseReading(
                timestamp=_local_ts(dt),
                value=int(cgm),
                type="sensor"
            ))
        bg = _to_float(rec.get("glycemia"))
        if bg and bg > 0:
            readings.append(GlucoseReading(
                timestamp=_local_ts(dt),
                value=int(bg),
                type="bg_meter"
            ))

    print(f"Parsed {len(readings)} glucose readings from last {days_back} days")
    return readings


def parse_bolus_events(filepath: str, days_back: int = 7) -> List[BolusEvent]:
    """Parse GlookoXT JSON and return bolus events (meals with carbs + insulin)."""
    records, _ = _load_records(filepath, days_back)
    bolus_events = []

    for rec, dt in records:
        carbs = _to_float(rec.get("carbs"))
        fast_insulin = _to_float(rec.get("fast_insulin"))

        if not carbs or carbs <= 0:
            continue
        if not fast_insulin or fast_insulin <= 0:
            fast_insulin = 0.0

        bolus_events.append(BolusEvent(
            timestamp=_local_ts(dt),
            carb_input=carbs,
            insulin_delivered=fast_insulin,
            date=_local_date(dt),
            time=_local_time(dt),
        ))

    print(f"Parsed {len(bolus_events)} bolus events from last {days_back} days")
    return bolus_events


def extract_bg_for_periods(filepath: str, organized_bolus_data: Dict[str, Dict[str, list]]) -> Dict[str, Dict[str, List[GlucoseReading]]]:
    """Extract BG sensor readings for each period/day based on bolus timing."""
    records, _ = _load_records(filepath)
    bg_data = {}

    for date, periods in organized_bolus_data.items():
        bg_data[date] = {}
        for period_name, bolus_events in periods.items():
            if not bolus_events:
                bg_data[date][period_name] = []
                continue

            bolus_times = [datetime.strptime(f"{e.date} {e.time}", LOCAL_TS_FMT) for e in bolus_events]
            start_time = min(bolus_times) - timedelta(minutes=15)
            end_time = max(bolus_times) + timedelta(hours=3)

            period_readings = []
            for rec, dt in records:
                dt_naive = dt.replace(tzinfo=None)
                if start_time <= dt_naive <= end_time:
                    cgm = _to_float(rec.get("glycemia_cgm"))
                    if cgm and cgm > 0:
                        period_readings.append(GlucoseReading(
                            timestamp=_local_ts(dt),
                            value=int(cgm),
                            type="sensor"
                        ))

            period_readings.sort(key=lambda x: x.timestamp)
            bg_data[date][period_name] = period_readings

            print(f"   {date} {period_name}: {len(period_readings)} BG readings ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})")

    return bg_data


def extract_correction_boluses(filepath: str, organized_bolus_data: Dict[str, Dict[str, list]]) -> Dict[str, Dict[str, List[BolusEvent]]]:
    """Extract correction boluses (insulin-only, no carbs) during BG response periods."""
    records, _ = _load_records(filepath)
    correction_data = {}

    for date, periods in organized_bolus_data.items():
        correction_data[date] = {}
        for period_name, bolus_events in periods.items():
            if not bolus_events:
                correction_data[date][period_name] = []
                continue

            bolus_times = [datetime.strptime(f"{e.date} {e.time}", LOCAL_TS_FMT) for e in bolus_events]
            first_bolus = min(bolus_times)
            end_time = max(bolus_times) + timedelta(hours=3)

            meal_timestamps = {e.timestamp for e in bolus_events}
            corrections = []

            for rec, dt in records:
                dt_naive = dt.replace(tzinfo=None)
                if first_bolus <= dt_naive <= end_time:
                    ts = _local_ts(dt)
                    if ts in meal_timestamps:
                        continue

                    corr_insulin = _to_float(rec.get("correction_insulin"))
                    fast_insulin = _to_float(rec.get("fast_insulin"))
                    carbs = _to_float(rec.get("carbs"))

                    insulin = corr_insulin or fast_insulin
                    has_carbs = carbs and carbs > 0

                    if insulin and insulin > 0 and not has_carbs:
                        corrections.append(BolusEvent(
                            timestamp=ts,
                            carb_input=0.0,
                            insulin_delivered=insulin,
                            date=_local_date(dt),
                            time=_local_time(dt),
                        ))

            corrections.sort(key=lambda x: x.timestamp)
            correction_data[date][period_name] = corrections

    return correction_data


def extract_basal_for_periods(filepath: str, organized_bolus_data: Dict[str, Dict[str, list]]) -> Dict[str, Dict[str, List[BasalEvent]]]:
    """Extract basal rate information for each period/day based on bolus timing."""
    records, _ = _load_records(filepath)
    basal_data = {}

    for date, periods in organized_bolus_data.items():
        basal_data[date] = {}
        for period_name, bolus_events in periods.items():
            if not bolus_events:
                basal_data[date][period_name] = []
                continue

            bolus_times = [datetime.strptime(f"{e.date} {e.time}", LOCAL_TS_FMT) for e in bolus_events]
            first_bolus = min(bolus_times)
            end_time = max(bolus_times) + timedelta(hours=3)

            period_basal = []
            for rec, dt in records:
                dt_naive = dt.replace(tzinfo=None)
                if first_bolus <= dt_naive <= end_time:
                    rate = _to_float(rec.get("basal_rate"))
                    if rate is not None:
                        period_basal.append(BasalEvent(
                            timestamp=_local_ts(dt),
                            basal_rate=rate,
                            date=_local_date(dt),
                            time=_local_time(dt),
                        ))

            period_basal.sort(key=lambda x: x.timestamp)
            basal_data[date][period_name] = period_basal

            if period_basal:
                print(f"   {date} {period_name}: {len(period_basal)} basal events")

    return basal_data
