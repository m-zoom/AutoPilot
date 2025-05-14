"""
Tools for the AI agent to interact with the operating system.
Includes operations for opening applications and navigating directories.
"""

import sys

import os
import platform
import subprocess
import logging
from typing import List, Dict, Any, Optional, Union
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

class OpenApplicationTool(BaseTool):
    """Tool for opening applications on Mac or Windows."""
    
    name: str = "open_application"
    description: str = """
    Opens an application installed on the user's computer.
    Works for both Mac and Windows operating systems.
    
    Input should be the name of the application to open.
    Returns confirmation or error message.
    """
    
    def _run(self, app_name: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Open an application on the user's system."""
        try:
            current_os = platform.system()
            
            if current_os == "Darwin":  # macOS
                # Use 'open' command on Mac
                logger.info(f"Attempting to open {app_name} on macOS")
                result = subprocess.run(['open', '-a', app_name], 
                                       capture_output=True, text=True, check=False)
                
                if result.returncode != 0:
                    return f"Error opening {app_name}: {result.stderr}"
                return f"Successfully opened {app_name}"
                
            elif current_os == "Windows":
                # For Windows, try multiple methods to open the application
                logger.info(f"Attempting to open {app_name} on Windows")
                
                # Check if running in Replit environment
                is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
                if is_replit:
                    return f"Cannot launch desktop application '{app_name}' in the Replit environment. This tool is designed to work on local machines."
                
                # Map of common applications to their executable paths or commands
                app_path_mapping = {
                    "chrome": "chrome.exe",
                    "google chrome": "chrome.exe",
                    "firefox": "firefox.exe",
                    "edge": "msedge.exe",
                    "microsoft edge": "msedge.exe",
                    "word": "winword.exe",
                    "excel": "excel.exe",
                    "powerpoint": "powerpnt.exe",
                    "outlook": "outlook.exe",
                    "notepad": "notepad.exe",
                    "paint": "mspaint.exe",
                    "calculator": "calc.exe",
                    "cmd": "cmd.exe",
                    "command prompt": "cmd.exe",
                    "powershell": "powershell.exe",
                    "file explorer": "explorer.exe",
                    "explorer": "explorer.exe",
                    "vscode": "code.exe", 
                    "visual studio code": "code.exe",
                    "arduino": "arduino.exe",
                    "arduino ide": "arduino.exe"
                }
                
                # Look up the executable name if it exists in our mapping
                executable = app_path_mapping.get(app_name.lower(), app_name)
                
                # For Windows, always use 'start' command which is the proper way to launch applications
                
                # First attempt: Try using the mapped executable directly with start command
                try:
                    subprocess.run(f'start "" "{executable}"', shell=True, check=False)
                    return f"Attempted to open {app_name} using Windows start command"
                except Exception as e1:
                    logger.info(f"Direct start command failed: {str(e1)}")
                
                # Second attempt: Try finding the application in Program Files
                try:
                    program_files = [
                        os.environ.get("ProgramFiles", "C:\\Program Files"),
                        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
                    ]
                    
                    # Search through common paths where applications might be installed
                    common_app_locations = program_files + [
                        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                    ]
                    
                    for location in common_app_locations:
                        if not os.path.exists(location):
                            continue
                            
                        # Look for executables matching our app name
                        for root, dirs, files in os.walk(location):
                            # First check if we have an exact match for the executable
                            if executable.lower() in [f.lower() for f in files]:
                                full_path = os.path.join(root, [f for f in files if f.lower() == executable.lower()][0])
                                subprocess.run(f'start "" "{full_path}"', shell=True, check=False)
                                return f"Opened {app_name} from {full_path}"
                            
                            # Check for folders containing the app name
                            app_dirs = [d for d in dirs if app_name.lower() in d.lower()]
                            for app_dir in app_dirs:
                                app_dir_path = os.path.join(root, app_dir)
                                
                                # Common executable names to try
                                possible_exes = [
                                    executable,
                                    f"{app_name}.exe",
                                    "launch.exe", 
                                    "launcher.exe",
                                    "app.exe",
                                    "program.exe",
                                    "bin\\{}.exe".format(app_name),
                                    "bin\\{}.exe".format(executable.replace('.exe', ''))
                                ]
                                
                                for exe_name in possible_exes:
                                    exe_path = os.path.join(app_dir_path, exe_name)
                                    if os.path.exists(exe_path):
                                        subprocess.run(f'start "" "{exe_path}"', shell=True, check=False)
                                        return f"Opened {app_name} from {exe_path}"
                    
                    # Third attempt: Look for shortcuts in Start Menu
                    start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu")
                    if os.path.exists(start_menu):
                        for root, dirs, files in os.walk(start_menu):
                            shortcuts = [f for f in files if f.lower().endswith('.lnk') and app_name.lower() in f.lower()]
                            if shortcuts:
                                shortcut_path = os.path.join(root, shortcuts[0])
                                subprocess.run(f'start "" "{shortcut_path}"', shell=True, check=False)
                                return f"Opened {app_name} shortcut from Start Menu"
                    
                    # Final attempt: Use the Windows Run dialog approach
                    subprocess.run(f'start "" "{app_name}"', shell=True, check=False)
                    return f"Attempted to open {app_name} through Windows Run dialog"
                
                except Exception as e2:
                    logger.info(f"App search failed: {str(e2)}")
                    
                    # Last resort attempt with just the app name
                    try:
                        subprocess.run(f'start {app_name}', shell=True, check=False)
                        return f"Attempted to open {app_name} through Windows shell"
                    except Exception as e3:
                        return f"Failed to open {app_name}. Error: {str(e3)}"
            else:
                return f"Unsupported operating system: {current_os}"
                
        except Exception as e:
            logger.error(f"Error opening application: {str(e)}")
            return f"Error opening application: {str(e)}"

class NavigateDirectoryTool(BaseTool):
    """Tool for navigating to directories."""
    
    name: str = "navigate_directory"
    description: str = """
    Navigates to a specified directory in the file system.
    
    Input should be the path to the directory (absolute or relative).
    Returns the current directory after navigation or error message.
    """
    
    def _run(self, directory_path: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Navigate to the specified directory."""
        try:
            # Expand user directory if needed (e.g., ~/Documents)
            expanded_path = os.path.expanduser(directory_path)
            
            # Check if directory exists
            if not os.path.exists(expanded_path):
                return f"Error: Directory '{directory_path}' does not exist"
            
            if not os.path.isdir(expanded_path):
                return f"Error: '{directory_path}' is not a directory"
            
            # Change to the directory
            os.chdir(expanded_path)
            current_dir = os.getcwd()
            
            return f"Successfully navigated to: {current_dir}"
            
        except Exception as e:
            logger.error(f"Error navigating to directory: {str(e)}")
            return f"Error navigating to directory: {str(e)}"
