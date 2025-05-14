"""
Utility tools for the AI agent.
Includes operations for working with the clipboard, getting current date/time,
and other miscellaneous utilities.
"""

import sys

import os
import logging
import datetime
import platform
import subprocess
from typing import Optional
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.base import BaseTool

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


logger = logging.getLogger(__name__)

class GetCurrentDateTimeTool(BaseTool):
    """Tool for getting the current date and time."""
    
    name: str = "get_current_datetime"
    description: str = """
    Gets the current date and time.
    
    No input is required. 
    Returns the current date and time in a formatted string.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Get the current date and time."""
        try:
            now = datetime.datetime.now()
            
            # Format the date and time
            formatted_date = now.strftime("%A, %B %d, %Y")
            formatted_time = now.strftime("%I:%M:%S %p")
            timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()
            
            return f"Current Date: {formatted_date}\nCurrent Time: {formatted_time} {timezone}"
            
        except Exception as e:
            logger.error(f"Error getting date/time: {str(e)}")
            return f"Error getting date/time: {str(e)}"


class GetSystemInfoTool(BaseTool):
    """Tool for getting system information."""
    
    name: str = "get_system_info"
    description: str = """
    Gets information about the current system.
    
    No input is required.
    Returns information about the operating system, hostname, etc.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Get system information."""
        try:
            info = []
            
            # Platform information
            info.append(f"System: {platform.system()}")
            info.append(f"Platform: {platform.platform()}")
            info.append(f"Python Version: {platform.python_version()}")
            
            # Current directory
            info.append(f"Current Directory: {os.getcwd()}")
            
            # Get machine info if available
            if hasattr(platform, "machine"):
                info.append(f"Machine: {platform.machine()}")
                
            # Get processor info if available
            if hasattr(platform, "processor"):
                processor = platform.processor()
                if processor:
                    info.append(f"Processor: {processor}")
            
            return "\n".join(info)
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return f"Error getting system info: {str(e)}"


class ClipboardTool(BaseTool):
    """Tool for interacting with the clipboard."""
    
    name: str = "clipboard"
    description: str = """
    Interacts with the system clipboard.
    
    Input should be the text to copy to clipboard.
    If input is empty, it will attempt to read from the clipboard.
    
    Example: "Copy this text to clipboard" 
    
    Note: Clipboard access may be limited in environments without a GUI.
    """
    
    def _run(self, text: str = "", run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Interact with the clipboard."""
        try:
            current_os = platform.system()
            
            # If no text provided, try to read from clipboard
            if not text:
                logger.info("Attempting to read from clipboard")
                
                if current_os == "Darwin":  # macOS
                    try:
                        result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
                        return f"Clipboard content:\n{result.stdout}"
                    except subprocess.CalledProcessError:
                        return "Failed to read from clipboard on macOS"
                    
                elif current_os == "Windows":
                    try:
                        # Requires pywin32, which might not be available
                        return "Reading from clipboard is not supported in this environment"
                    except Exception:
                        return "Failed to read from clipboard on Windows"
                        
                else:  # Linux and others
                    try:
                        result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                              capture_output=True, text=True, check=True)
                        return f"Clipboard content:\n{result.stdout}"
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        return "Failed to read from clipboard on Linux (xclip may not be installed)"
            
            # If text provided, try to copy to clipboard
            else:
                logger.info(f"Attempting to copy to clipboard: {text}")
                
                if current_os == "Darwin":  # macOS
                    try:
                        subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
                        return f"Successfully copied text to clipboard: {text}"
                    except subprocess.CalledProcessError:
                        return "Failed to copy to clipboard on macOS"
                    
                elif current_os == "Windows":
                    return "Copying to clipboard is not supported in this environment"
                        
                else:  # Linux and others
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'], 
                                     input=text.encode('utf-8'), check=True)
                        return f"Successfully copied text to clipboard: {text}"
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        return "Failed to copy to clipboard on Linux (xclip may not be installed)"
                        
        except Exception as e:
            logger.error(f"Error interacting with clipboard: {str(e)}")
            return f"Error interacting with clipboard: {str(e)}"