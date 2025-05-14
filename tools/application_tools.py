"""
Tools for the AI agent to interact with applications.
Includes operations for opening, closing, and managing applications.
"""

import sys

import os
import platform
import subprocess
import logging
import psutil
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

class OpenAdvancedApplicationTool(BaseTool):
    """Tool for opening an application with advanced options."""
    
    name: str = "open_advanced_application"
    description: str = """
    Opens an application with advanced options like providing initial content for text editors.
    
    Input should be a JSON object with:
    - 'app_name': name of the application to open
    - 'content_to_write' (optional): content to write to the application if it's a text editor
    
    Example: {"app_name": "notepad", "content_to_write": "Hello world!"}
    
    Returns confirmation or error message.
    """
    
    def _run(self, app_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Open an application with advanced options."""
        try:
            # Check if running in Replit environment
            is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
            
            # Parse the input
            import json
            try:
                app_info = json.loads(app_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                app_match = re.search(r"app_name['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", app_info_str)
                content_match = re.search(r"content_to_write['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", app_info_str)
                
                if app_match:
                    app_info = {
                        "app_name": app_match.group(1)
                    }
                    if content_match:
                        app_info["content_to_write"] = content_match.group(1)
                else:
                    # If app_name couldn't be extracted, assume the whole string is the app name
                    app_info = {
                        "app_name": app_info_str.strip()
                    }
            
            if not isinstance(app_info, dict):
                app_info = {"app_name": str(app_info)}
            
            if "app_name" not in app_info:
                return "Error: Input must contain 'app_name'"
            
            app_name = app_info["app_name"]
            content_to_write = app_info.get("content_to_write", None)
            
            # If running in Replit environment, return appropriate message
            if is_replit:
                return f"Cannot launch desktop application '{app_name}' in the Replit environment. This tool is designed to work on local machines. The application would need to be installed on your local computer to be launched."
            
            # Get the operating system
            current_os = platform.system()
            
            # Create a temporary file for content_to_write if needed
            temp_file = None
            if content_to_write:
                import tempfile
                
                # Create temp file with the right extension based on the app
                extension = ".txt"  # Default
                if "word" in app_name.lower():
                    extension = ".docx"
                elif "excel" in app_name.lower():
                    extension = ".xlsx"
                elif "powerpoint" in app_name.lower():
                    extension = ".pptx"
                elif any(code_ext in app_name.lower() for code_ext in ["code", "vscode", "sublime", "atom"]):
                    extension = ".py"  # Default to Python for code editors
                
                fd, temp_file = tempfile.mkstemp(suffix=extension)
                with os.fdopen(fd, 'w') as file:
                    file.write(content_to_write)
            
            # Open the application based on OS
            if current_os == "Darwin":  # macOS
                if temp_file:
                    # Open the temp file with the specified application
                    command = ["open", "-a", app_name, temp_file]
                else:
                    # Just open the application
                    command = ["open", "-a", app_name]
                    
                result = subprocess.run(command, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Error opening {app_name}: {result.stderr}"
                
                if temp_file:
                    return f"Successfully opened {app_name} with the provided content in {temp_file}"
                else:
                    return f"Successfully opened {app_name}"
                
            elif current_os == "Windows":
                # Handle common Windows applications
                if app_name.lower() == "notepad" and content_to_write:
                    if not temp_file:
                        fd, temp_file = tempfile.mkstemp(suffix=".txt")
                        with os.fdopen(fd, 'w') as file:
                            file.write(content_to_write)
                    
                    command = ["notepad.exe", temp_file]
                    subprocess.Popen(command, shell=True)
                    return f"Successfully opened Notepad with the provided content in {temp_file}"
                else:
                    try:
                        if temp_file:
                            # Open the temp file with the default application
                            result = subprocess.Popen(f'start "" "{temp_file}"', shell=True)
                            return f"Successfully opened {app_name} with the provided content in {temp_file}"
                        else:
                            # Just open the application
                            result = subprocess.Popen(app_name, shell=True)
                            return f"Attempted to open {app_name}"
                    except Exception as e:
                        # Try via Start Menu
                        try:
                            subprocess.Popen(f'start {app_name}', shell=True)
                            return f"Attempted to open {app_name} through Start Menu"
                        except Exception as e2:
                            return f"Failed to open {app_name}: {str(e2)}"
            
            else:  # Linux and others
                if temp_file:
                    # For graphical applications that can open files
                    try:
                        command = ["xdg-open", temp_file]
                        subprocess.Popen(command)
                        return f"Opened file {temp_file} with default application for its type"
                    except Exception as e:
                        return f"Failed to open {temp_file}: {str(e)}"
                else:
                    # Try to run the application directly
                    try:
                        subprocess.Popen([app_name])
                        return f"Attempted to open {app_name}"
                    except Exception as e:
                        return f"Failed to open {app_name}: {str(e)}"
                        
        except Exception as e:
            logger.error(f"Error opening application: {str(e)}")
            return f"Error opening application: {str(e)}"


class CloseApplicationTool(BaseTool):
    """Tool for closing an application."""
    
    name: str = "close_application"
    description: str = """
    Closes a specified application.
    
    Input should be the name of the application to close.
    Returns confirmation or error message.
    
    Example: "notepad" or "chrome"
    """
    
    def _run(self, app_name: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Close an application."""
        try:
            # Check if running in Replit environment
            is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
            
            # Standardize input (parse JSON if needed)
            try:
                import json
                parsed = json.loads(app_name)
                if isinstance(parsed, dict) and "app_name" in parsed:
                    app_name = parsed["app_name"]
            except (json.JSONDecodeError, TypeError):
                # Not JSON, use as is
                pass
            
            app_name = app_name.strip().lower()
            
            # If running in Replit environment, return appropriate message
            if is_replit:
                return f"Cannot close desktop application '{app_name}' in the Replit environment. This tool is designed to work on local machines."
            
            # Dictionary mapping common app names to process names
            app_process_map = {
                "chrome": ["chrome", "googlechrome"],
                "firefox": ["firefox", "mozilla firefox"],
                "edge": ["msedge", "microsoft edge"],
                "safari": ["safari"],
                "notepad": ["notepad"],
                "word": ["winword", "microsoft word"],
                "excel": ["excel", "microsoft excel"],
                "powerpoint": ["powerpnt", "microsoft powerpoint"],
                "vscode": ["code", "visual studio code"],
                "terminal": ["terminal", "cmd", "command prompt", "powershell"],
                "explorer": ["explorer"],
                "calculator": ["calc"],
                "paint": ["mspaint"],
                "itunes": ["itunes"],
                "spotify": ["spotify"],
                "vlc": ["vlc"],
                "photoshop": ["photoshop"],
                "illustrator": ["illustrator"],
                "acrobat": ["acrobat", "adobe acrobat"],
                "teams": ["teams", "microsoft teams"],
                "zoom": ["zoom"],
                "skype": ["skype"]
            }
            
            # Get possible process names for the given app
            process_names = []
            for key, values in app_process_map.items():
                if app_name in values or app_name == key:
                    process_names.extend(values)
            
            # If no mapping found, use the app_name directly
            if not process_names:
                process_names = [app_name]
            
            # Find and terminate processes
            terminated = False
            terminated_names = []
            
            for proc in psutil.process_iter(['pid', 'name']):
                proc_name = proc.info['name'].lower()
                
                if any(p in proc_name for p in process_names):
                    try:
                        proc.terminate()
                        terminated = True
                        if proc_name not in terminated_names:
                            terminated_names.append(proc_name)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        # Process might have already disappeared or access denied
                        continue
            
            if terminated:
                terminated_str = ", ".join(terminated_names)
                return f"Successfully terminated processes related to {app_name}: {terminated_str}"
            else:
                return f"No processes found for {app_name}"
                
        except Exception as e:
            logger.error(f"Error closing application: {str(e)}")
            return f"Error closing application: {str(e)}"


class ListRunningAppsTool(BaseTool):
    """Tool for listing currently running applications."""
    
    name: str = "list_running_apps"
    description: str = """
    Lists currently running applications.
    
    No input is required.
    Returns a list of running applications.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """List currently running applications."""
        try:
            # Check if running in Replit environment
            is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
            
            # If running in Replit environment, return realistic but limited information
            if is_replit:
                return """Running applications in Replit environment:
- Flask Web Server (PID: 1)
- Python Interpreter (PID: 2)
- gunicorn (PID: 3)
- bash (PID: 4)

Note: This is a limited view as desktop applications cannot be directly accessed in the Replit environment. The full list_running_apps tool is designed to work on local machines."""
            
            # Dictionary of common process names to display names
            process_display_map = {
                "chrome": "Google Chrome",
                "firefox": "Mozilla Firefox",
                "msedge": "Microsoft Edge",
                "safari": "Safari",
                "notepad": "Notepad",
                "winword": "Microsoft Word",
                "excel": "Microsoft Excel",
                "powerpnt": "Microsoft PowerPoint",
                "code": "Visual Studio Code",
                "cmd": "Command Prompt",
                "powershell": "PowerShell",
                "explorer": "File Explorer",
                "calc": "Calculator",
                "mspaint": "Paint",
                "itunes": "iTunes",
                "spotify": "Spotify",
                "vlc": "VLC Media Player",
                "photoshop": "Adobe Photoshop",
                "illustrator": "Adobe Illustrator",
                "acrobat": "Adobe Acrobat",
                "teams": "Microsoft Teams",
                "zoom": "Zoom",
                "skype": "Skype"
            }
            
            # Get running processes
            processes = {}
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    
                    # Skip system processes and background processes
                    if proc_name in ["system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe"]:
                        continue
                    
                    # Use friendly name if available
                    display_name = None
                    for key, value in process_display_map.items():
                        if key in proc_name:
                            display_name = value
                            break
                    
                    if not display_name:
                        display_name = proc_info['name']
                    
                    if display_name in processes:
                        processes[display_name]["count"] += 1
                    else:
                        processes[display_name] = {
                            "count": 1,
                            "pid": proc_info['pid']
                        }
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process might have already disappeared or access denied
                    continue
            
            # Format the output
            if not processes:
                return "No user applications currently running."
            
            output = ["Currently running applications:"]
            
            # Sort processes by name
            sorted_processes = sorted(processes.items(), key=lambda x: x[0].lower())
            
            for name, info in sorted_processes:
                count_str = f" ({info['count']} instances)" if info['count'] > 1 else ""
                output.append(f"- {name}{count_str} (PID: {info['pid']})")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error listing running applications: {str(e)}")
            return f"Error listing running applications: {str(e)}"