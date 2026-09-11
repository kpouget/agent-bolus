#!/usr/bin/env python3
"""
Data Logger Decorator for GlucoseDataManager
Logs method inputs and outputs in YAML format
"""
import yaml
import functools
import datetime
import os
from typing import Any, Dict, List
from dataclasses import asdict
import logging

# Create a logger specific to this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler if not already added
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False  # Don't propagate to root logger

def summary_log_method():
    """
    Lighter logging decorator that only logs method calls and summary results.
    Logs to logs/glucose_data.yaml by default.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Call the original method
            result = func(self, *args, **kwargs)

            # Prepare minimal log entry
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
            }

            method = func.__name__ + "("
            if args:
                method += ", ".join(map(str, args))
                if kwargs:
                    method += ", "

            if kwargs:
                method += ", ".join([f"{k}={v}" for k, v in kwargs.items()])

            method += ")"

            log_entry["method"] = method

            # Add result summary based on type
            if isinstance(result, (int, float, str, bool)):
                log_entry["result"] = result
            elif isinstance(result, dict):
                log_entry["result"] = result
            elif isinstance(result, list):
                log_entry["result"] = {"count": len(result), "type": "list"}
            elif hasattr(result, '__dataclass_fields__'):
                log_entry["result"] = asdict(result)
            else:
                log_entry["result"] = {"type": str(type(result).__name__)}

            logger.info("---")
            logger.info(yaml.dump(log_entry, default_flow_style=False, allow_unicode=True, sort_keys=False))

            return result

        return wrapper
    return decorator
