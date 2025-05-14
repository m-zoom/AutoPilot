"""
Tools for requesting application paths from the user.
Includes a tool to ask for the full path of an application before opening it.
"""

import sys

import os
import platform
import logging
from typing import Optional, Dict

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

class GetApplicationPathTool(BaseTool):
    """Tool for requesting the full path of an application from the user."""
    
    name: str = "get_application_path"
    description: str = """
    Requests the full file path of an application from the user when the path is unknown.
    
    Input should be the name of the application you want to find the path for.
    Returns the full path as provided by the user, or an error message.
    
    Example: "notepad" or "arduino"
    
    Use this tool BEFORE trying to open an application when you don't have the exact path.
    """
    
    def _run(self, app_name: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Request the full path of an application from the user."""
        try:
            if not app_name.strip():
                return "Error: Application name is required."
            
            # Check if running in Replit environment
            is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
            if is_replit:
                return (f"Unable to find the path for '{app_name}' in the Replit environment. "
                        f"When running on a user's local machine, you should ask them for the full path to {app_name}. "
                        f"For example, it might be: 'C:\\Program Files\\{app_name}\\{app_name}.exe'")
                
            current_os = platform.system()
            
            if current_os == "Windows":
                sample_path = f"C:\\Program Files\\{app_name}\\{app_name}.exe"
            elif current_os == "Darwin":  # macOS
                sample_path = f"/Applications/{app_name}.app"
            else:  # Linux and others
                sample_path = f"/usr/bin/{app_name.lower()}"
            
            return (f"I need the exact path to '{app_name}' to open it reliably. "
                   f"Please provide the full path to the {app_name} executable on your system. "
                   f"It might look something like: '{sample_path}' depending on where it's installed.")
            
        except Exception as e:
            logger.error(f"Error requesting application path: {str(e)}")
            return f"Error requesting application path: {str(e)}"


class StoreApplicationPathTool(BaseTool):
    """Tool for storing application paths provided by the user."""
    
    name: str = "store_application_path"
    description: str = """
    Stores a mapping between an application name and its full path for future use.
    
    Input should be a JSON object with:
    - 'app_name': name of the application (e.g., "notepad", "chrome")
    - 'app_path': full path to the application executable (e.g., "C:\\Windows\\notepad.exe")
    
    Example: {"app_name": "vscode", "app_path": "C:\\Program Files\\Microsoft VS Code\\Code.exe"}
    
    Returns confirmation of storage or error message.
    
    Use this tool after getting the application path from the user.
    """
    
    # In-memory storage for application paths
    _app_paths = {}
    
    def _run(self, path_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Store application path mapping."""
        try:
            import json
            
            # Parse the input string as JSON
            path_info = json.loads(path_info_str)
            
            if not isinstance(path_info, dict):
                return "Error: Input should be a JSON object with 'app_name' and 'app_path' keys."
            
            app_name = path_info.get("app_name", "").strip()
            app_path = path_info.get("app_path", "").strip()
            
            if not app_name:
                return "Error: Application name is required."
            
            if not app_path:
                return "Error: Application path is required."
            
            # Store the application path
            self.__class__._app_paths[app_name.lower()] = app_path
            
            return f"Successfully stored path for '{app_name}': {app_path}"
            
        except json.JSONDecodeError:
            return "Error: Input should be a valid JSON object."
        except Exception as e:
            logger.error(f"Error storing application path: {str(e)}")
            return f"Error storing application path: {str(e)}"
    
    @classmethod
    def get_path(cls, app_name: str) -> Optional[str]:
        """Get the stored path for an application."""
        return cls._app_paths.get(app_name.lower())


class GetStoredApplicationPathTool(BaseTool):
    """Tool for retrieving stored application paths."""
    
    name: str = "get_stored_application_path"
    description: str = """
    Retrieves a previously stored application path.
    
    Input should be the name of the application to get the path for.
    Returns the stored path or a message that the path is not stored.
    
    Example: "vscode" or "chrome"
    
    Use this tool to check if you already have the path before asking the user.
    """
    
    def _run(self, app_name: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get stored application path."""
        try:
            if not app_name.strip():
                return "Error: Application name is required."
            
            # Get the path from the storage
            app_path = StoreApplicationPathTool.get_path(app_name)
            
            if app_path:
                return f"Found stored path for '{app_name}': {app_path}"
            else:
                return f"No stored path found for '{app_name}'."
            
        except Exception as e:
            logger.error(f"Error retrieving application path: {str(e)}")
            return f"Error retrieving application path: {str(e)}"