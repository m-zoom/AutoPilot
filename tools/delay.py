import os
import sys

import time
import json
from typing import Optional
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class DelayTool(BaseTool):
    """Tool for delaying execution."""

    name: str = "delay"
    description: str = """
    Delays execution for a specified number of seconds.

    Input should be a JSON object like:
    {"seconds": 2.5}

    Returns a confirmation message after the delay.
    """

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            params = json.loads(input_str)
            seconds = float(params.get("seconds", 0))
            if seconds < 0:
                return "Error: Delay time cannot be negative."
            time.sleep(seconds)
            return f"Delayed for {seconds} seconds."
        except json.JSONDecodeError:
            return "Error: Invalid JSON input."
        except (ValueError, TypeError):
            return "Error: 'seconds' must be a valid number."
