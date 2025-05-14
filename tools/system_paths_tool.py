"""
Tool for the AI agent to discover and use common system paths.
Provides functionality to identify standard locations like Desktop, Documents, Downloads, etc.
"""

import os
import sys
import json
import logging
import platform
from typing import Dict, List, Optional
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

class GetSystemPathsTool(BaseTool):
    """Tool for identifying common system paths."""
    
    name: str = "get_system_paths"
    description: str = """
    Returns the paths to common system locations like Desktop, Documents, Downloads, etc.
    
    No input is needed.
    Returns a dictionary of common system paths or error message.
    
    Use this tool to help locate standard directories on the user's system without
    requiring the user to provide explicit paths.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get paths to common system locations."""
        try:
            paths = {}
            system = platform.system()
            
            # Get home directory
            home = os.path.expanduser("~")
            paths["home"] = home
            
            # Define standard directories that exist across platforms
            standard_dirs = {
                "desktop": ["Desktop"],
                "documents": ["Documents", "My Documents"],
                "downloads": ["Downloads"],
                "pictures": ["Pictures", "My Pictures"],
                "music": ["Music", "My Music"],
                "videos": ["Videos", "My Videos"]
            }
            
            # Detect if we're running in a Replit environment
            in_replit = "REPL_ID" in os.environ or "REPLIT_DEPLOYMENT_ID" in os.environ
            if in_replit:
                # In Replit, create standard directories in workspace if they don't exist
                logger.info("Detected Replit environment. Creating standard directories in workspace.")
                workspace_dir = os.path.join(home, "workspace")
                paths["workspace"] = workspace_dir
                
                # Create standard directories within workspace
                for key, folders in standard_dirs.items():
                    folder_name = folders[0]  # Use the first folder name option
                    path = os.path.join(workspace_dir, folder_name)
                    # Create the directory if it doesn't exist
                    if not os.path.exists(path):
                        try:
                            os.makedirs(path, exist_ok=True)
                            logger.info(f"Created directory: {path}")
                        except Exception as e:
                            logger.error(f"Error creating directory {path}: {str(e)}")
                    paths[key] = path
            
            # Additional OS-specific paths (for non-Replit environments)
            elif system == "Windows":
                # Windows specific paths
                paths["appdata"] = os.getenv("APPDATA", "")
                paths["programfiles"] = os.getenv("ProgramFiles", "")
                paths["programfiles_x86"] = os.getenv("ProgramFiles(x86)", "")
                paths["temp"] = os.getenv("TEMP", "")
                
                # User folders are typically in a predictable location
                for key, folders in standard_dirs.items():
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
                
            elif system == "Darwin":  # macOS
                # macOS specific paths
                paths["applications"] = "/Applications"
                paths["library"] = os.path.join(home, "Library")
                
                # User folders follow macOS conventions
                for key, folders in standard_dirs.items():
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
                
            elif system == "Linux":
                # Linux specific paths
                paths["config"] = os.path.join(home, ".config")
                
                # Check XDG directories first (modern Linux)
                try:
                    import subprocess
                    xdg_dirs = {}
                    for key in ["DESKTOP", "DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS"]:
                        try:
                            result = subprocess.run(
                                ["xdg-user-dir", key], 
                                capture_output=True, 
                                text=True, 
                                check=True
                            )
                            xdg_path = result.stdout.strip()
                            if xdg_path and os.path.exists(xdg_path):
                                xdg_key = key.lower()
                                if xdg_key == "download":
                                    xdg_key = "downloads"
                                paths[xdg_key] = xdg_path
                        except (subprocess.SubprocessError, FileNotFoundError):
                            pass
                except ImportError:
                    pass
                
                # Fallback to standard directories
                for key, folders in standard_dirs.items():
                    if key not in paths:  # Only check if not already found via XDG
                        for folder in folders:
                            path = os.path.join(home, folder)
                            if os.path.exists(path):
                                paths[key] = path
                                break
            
            # Always check current working directory
            paths["current"] = os.getcwd()
            paths["workspace"] = os.getcwd()  # Add workspace alias pointing to current directory
            
            # Check if Python executable directory exists
            if hasattr(sys, 'executable') and sys.executable:
                paths["python"] = os.path.dirname(sys.executable)
            
            # Format the result
            result = "Common system paths detected:\n"
            for key, path in paths.items():
                if path:  # Only include non-empty paths
                    result += f"- {key}: {path}\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting system paths: {str(e)}")
            return f"Error getting system paths: {str(e)}"


class NavigateToSystemPathTool(BaseTool):
    """Tool for navigating to a specific system path."""
    
    name: str = "navigate_to_path"
    description: str = """
    Navigates to a specified system path, creating it if it doesn't exist (optional).
    
    Input:
        - Path string (e.g., "/path/to/directory" or "C:\\path\\to\\directory")
        - Or a shorthand name for common paths (e.g., "desktop", "documents", "downloads")
        - Add "--create" flag to create the directory if it doesn't exist
        - Add "--show" flag to list contents after navigating
    
    Returns the result of navigation attempt and directory information.
    
    Use this tool to navigate to specific locations on the file system.
    """
    
    def _run(self, input_str: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Navigate to a specified system path."""
        if not input_str.strip():
            return "Error: No path specified. Please provide a valid path or shorthand name."
        
        try:
            # Parse flags
            create_dir = "--create" in input_str
            show_contents = "--show" in input_str
            
            # Remove flags from input string
            path_str = input_str.replace("--create", "").replace("--show", "").strip()
            
            # Check if the input is a shorthand name
            system_paths = self._get_common_paths()
            target_path = system_paths.get(path_str.lower(), path_str)
            
            # Ensure path exists
            if not os.path.exists(target_path):
                if create_dir:
                    try:
                        os.makedirs(target_path, exist_ok=True)
                        result = f"Created and navigated to: {target_path}\n"
                    except Exception as e:
                        return f"Error creating directory '{target_path}': {str(e)}"
                else:
                    return f"Error: Path does not exist: {target_path}\nAdd '--create' flag to create it."
            else:
                result = f"Successfully navigated to: {target_path}\n"
            
            # Change current working directory
            os.chdir(target_path)
            
            # Get directory info
            result += f"Current working directory: {os.getcwd()}\n"
            
            # Show contents if requested
            if show_contents:
                try:
                    items = os.listdir(target_path)
                    dirs = [d for d in items if os.path.isdir(os.path.join(target_path, d))]
                    files = [f for f in items if os.path.isfile(os.path.join(target_path, f))]
                    
                    result += f"\nContents of {target_path}:\n"
                    result += "Directories:\n"
                    for d in dirs:
                        result += f"  - {d}/\n"
                    
                    result += "Files:\n"
                    for f in files:
                        size = os.path.getsize(os.path.join(target_path, f))
                        size_str = self._format_size(size)
                        result += f"  - {f} ({size_str})\n"
                except Exception as e:
                    result += f"\nError listing directory contents: {str(e)}"
            
            return result
        
        except Exception as e:
            logger.error(f"Error navigating to path: {str(e)}")
            return f"Error navigating to path: {str(e)}"
    
    def _get_common_paths(self) -> dict:
        """Get common system paths for shorthand navigation."""
        paths = {}
        home = os.path.expanduser("~")
        paths["home"] = home
        
        # Define standard directories
        standard_dirs = {
            "desktop": ["Desktop"],
            "documents": ["Documents", "My Documents"],
            "downloads": ["Downloads"],
            "pictures": ["Pictures", "My Pictures"],
            "music": ["Music", "My Music"],
            "videos": ["Videos", "My Videos"]
        }
        
        system = platform.system()
        
        if system == "Windows":
            paths["appdata"] = os.getenv("APPDATA", "")
            paths["localappdata"] = os.getenv("LOCALAPPDATA", "")
            paths["programfiles"] = os.getenv("ProgramFiles", "")
            paths["programfiles_x86"] = os.getenv("ProgramFiles(x86)", "")
            paths["temp"] = os.getenv("TEMP", "")
            
            # User folders
            for key, folders in standard_dirs.items():
                for folder in folders:
                    path = os.path.join(home, folder)
                    if os.path.exists(path):
                        paths[key] = path
                        break
        
        elif system == "Darwin":  # macOS
            paths["applications"] = "/Applications"
            paths["library"] = os.path.join(home, "Library")
            
            # User folders
            for key, folders in standard_dirs.items():
                for folder in folders:
                    path = os.path.join(home, folder)
                    if os.path.exists(path):
                        paths[key] = path
                        break
        
        elif system == "Linux":
            paths["config"] = os.path.join(home, ".config")
            paths["local_share"] = os.path.join(home, ".local", "share")
            paths["usr_bin"] = "/usr/bin"
            paths["usr_local_bin"] = "/usr/local/bin"
            
            # Try XDG directories first
            try:
                import subprocess
                for key in ["DESKTOP", "DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS"]:
                    try:
                        result = subprocess.run(
                            ["xdg-user-dir", key], 
                            capture_output=True, 
                            text=True, 
                            check=True
                        )
                        xdg_path = result.stdout.strip()
                        if xdg_path and os.path.exists(xdg_path):
                            xdg_key = key.lower()
                            if xdg_key == "download":
                                xdg_key = "downloads"
                            paths[xdg_key] = xdg_path
                    except (subprocess.SubprocessError, FileNotFoundError):
                        pass
            except ImportError:
                pass
            
            # Fallback to standard directories
            for key, folders in standard_dirs.items():
                if key not in paths:
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
        
        # Always include current directory
        paths["current"] = os.getcwd()
        paths["workspace"] = os.getcwd()
        
        return paths
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        
                
class GetInstalledAppsTool(BaseTool):
    """ Tool for discovering all installed applications on the system."""
    
    name: str = "get_installed_apps"
    description: str = """
    Returns the paths to all installed applications on the system.
    
    Input:
        - Empty string to list all applications
        - Filter string to narrow down the list (e.g., "microsoft" to only show Microsoft apps)
        - "--detailed" flag to include version information (when available)
        - "--system" flag to include system applications
    
    Returns a list of installed applications with their paths.
    
    Use this tool to discover what applications are installed on the user's system.
    """
    
    def _run(self, input_str: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get a list of all installed applications."""
        try:
            # Parse input parameters
            detailed_info = "--detailed" in input_str
            include_system = "--system" in input_str
            
            # Remove flags from input string
            filter_str = input_str.replace("--detailed", "").replace("--system", "").strip().lower()
            
            system = platform.system()
            installed_apps = []
            
            if system == "Windows":
                installed_apps = self._get_windows_apps(detailed_info, include_system)
            elif system == "Darwin":  # macOS
                installed_apps = self._get_macos_apps(detailed_info, include_system)
            elif system == "Linux":
                installed_apps = self._get_linux_apps(detailed_info, include_system)
            else:
                return f"Unsupported operating system: {system}"
            
            # Apply filter if provided
            if filter_str:
                installed_apps = [app for app in installed_apps if filter_str in app.get("name", "").lower()]
            
            # Format the response
            if not installed_apps:
                if filter_str:
                    return f"No applications matching '{filter_str}' were found on your system."
                else:
                    return "No applications were found on your system."
            
            # Sort by name for a consistent display
            installed_apps.sort(key=lambda x: x.get("name", "").lower())
            
            # Format the result
            result = f"Found {len(installed_apps)} installed applications"
            if filter_str:
                result += f" matching '{filter_str}'"
            result += ":\n\n"
            
            for app in installed_apps:
                result += f"• {app.get('name', 'Unknown')}\n"
                result += f"  Path: {app.get('path', 'Unknown')}\n"
                
                if detailed_info:
                    if "version" in app and app["version"]:
                        result += f"  Version: {app['version']}\n"
                    if "publisher" in app and app["publisher"]:
                        result += f"  Publisher: {app['publisher']}\n"
                    if "install_date" in app and app["install_date"]:
                        result += f"  Install Date: {app['install_date']}\n"
                
                result += "\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting installed applications: {str(e)}")
            return f"Error getting installed applications: {str(e)}"
    
    def _get_windows_apps(self, detailed=False, include_system=False) -> list:
        """Get installed applications on Windows."""
        apps = []
        
        try:
            # Method 1: Use Windows Registry
            import winreg
            
            # Registry paths for installed applications
            reg_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for reg_path in reg_paths:
                try:
                    registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    
                    # Enumerate all subkeys (installed applications)
                    for i in range(winreg.QueryInfoKey(registry_key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(registry_key, i)
                            subkey = winreg.OpenKey(registry_key, subkey_name)
                            
                            try:
                                app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                
                                # Skip system components and updates if not requested
                                if not include_system:
                                    # Check if it's a system component
                                    try:
                                        is_system = bool(winreg.QueryValueEx(subkey, "SystemComponent")[0])
                                        if is_system:
                                            continue
                                    except (FileNotFoundError, OSError):
                                        pass
                                    
                                    # Skip Windows updates
                                    if "KB" in app_name and "Update for Microsoft" in app_name:
                                        continue
                                
                                # Get installation path
                                try:
                                    app_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                except (FileNotFoundError, OSError):
                                    app_path = ""
                                
                                # Skip if both name and path are empty
                                if not app_name and not app_path:
                                    continue
                                
                                app_info = {
                                    "name": app_name,
                                    "path": app_path
                                }
                                
                                # Get additional info if detailed view requested
                                if detailed:
                                    try:
                                        app_info["version"] = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                    except (FileNotFoundError, OSError):
                                        pass
                                    
                                    try:
                                        app_info["publisher"] = winreg.QueryValueEx(subkey, "Publisher")[0]
                                    except (FileNotFoundError, OSError):
                                        pass
                                    
                                    try:
                                        app_info["install_date"] = winreg.QueryValueEx(subkey, "InstallDate")[0]
                                    except (FileNotFoundError, OSError):
                                        pass
                                
                                # Add to the list if not already present
                                if app_info not in apps:
                                    apps.append(app_info)
                            
                            except (FileNotFoundError, OSError):
                                continue
                            
                            finally:
                                winreg.CloseKey(subkey)
                        
                        except (FileNotFoundError, OSError):
                            continue
                    
                    winreg.CloseKey(registry_key)
                
                except (FileNotFoundError, OSError):
                    pass
            
            # Method 2: Check common installation directories (as a fallback)
            if len(apps) == 0:
                program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
                program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
                
                for program_dir in [program_files, program_files_x86]:
                    if os.path.exists(program_dir):
                        for item in os.listdir(program_dir):
                            item_path = os.path.join(program_dir, item)
                            if os.path.isdir(item_path):
                                # Check if there are executables
                                has_exe = False
                                for root, dirs, files in os.walk(item_path):
                                    if any(file.endswith(".exe") for file in files):
                                        has_exe = True
                                        break
                                    
                                    # Limit depth to avoid excessive searching
                                    if root.count(os.sep) - item_path.count(os.sep) > 2:
                                        break
                                
                                if has_exe:
                                    apps.append({
                                        "name": item,
                                        "path": item_path
                                    })
        
        except Exception as e:
            logger.error(f"Error enumerating Windows applications: {str(e)}")
        
        return apps
    
    def _get_macos_apps(self, detailed=False, include_system=False) -> list:
        """Get installed applications on macOS."""
        apps = []
        
        try:
            # Check in /Applications and ~/Applications
            app_locations = ["/Applications"]
            
            # Add user Applications folder
            home = os.path.expanduser("~")
            user_apps = os.path.join(home, "Applications")
            if os.path.exists(user_apps):
                app_locations.append(user_apps)
            
            # Add system applications if requested
            if include_system:
                system_apps = "/System/Applications"
                if os.path.exists(system_apps):
                    app_locations.append(system_apps)
            
            # Enumerate applications
            for app_location in app_locations:
                if os.path.exists(app_location):
                    for item in os.listdir(app_location):
                        if item.endswith(".app"):
                            app_path = os.path.join(app_location, item)
                            
                            # Get app name (remove .app extension)
                            app_name = item[:-4]
                            
                            app_info = {
                                "name": app_name,
                                "path": app_path
                            }
                            
                            # Get additional info if detailed view requested
                            if detailed:
                                try:
                                    # Get version from Info.plist
                                    info_plist = os.path.join(app_path, "Contents", "Info.plist")
                                    if os.path.exists(info_plist):
                                        # Try to use plistlib if available
                                        try:
                                            import plistlib
                                            with open(info_plist, 'rb') as f:
                                                plist_data = plistlib.load(f)
                                                
                                                if "CFBundleShortVersionString" in plist_data:
                                                    app_info["version"] = plist_data["CFBundleShortVersionString"]
                                                
                                                if "CFBundleIdentifier" in plist_data:
                                                    app_info["bundle_id"] = plist_data["CFBundleIdentifier"]
                                                
                                        except (ImportError, Exception) as e:
                                            # Fallback: Use mdls command
                                            try:
                                                import subprocess
                                                result = subprocess.run(
                                                    ["mdls", "-name", "kMDItemVersion", app_path],
                                                    capture_output=True,
                                                    text=True
                                                )
                                                
                                                if result.returncode == 0:
                                                    output = result.stdout.strip()
                                                    if "= " in output:
                                                        version = output.split("= ")[1].strip('"')
                                                        if version != "(null)":
                                                            app_info["version"] = version
                                            except:
                                                pass
                                except:
                                    pass
                            
                            # Add to the list
                            apps.append(app_info)
        
        except Exception as e:
            logger.error(f"Error enumerating macOS applications: {str(e)}")
        
        return apps
    
    def _get_linux_apps(self, detailed=False, include_system=False) -> list:
        """Get installed applications on Linux."""
        apps = []
        
        try:
            # Method 1: Use .desktop files (standard for Linux applications)
            desktop_locations = [
                "/usr/share/applications",
                "/usr/local/share/applications",
                os.path.expanduser("~/.local/share/applications")
            ]
            
            for location in desktop_locations:
                if os.path.exists(location):
                    for file in os.listdir(location):
                        if file.endswith(".desktop"):
                            desktop_file = os.path.join(location, file)
                            
                            try:
                                # Parse .desktop file
                                app_name = ""
                                app_exec = ""
                                app_path = ""
                                app_comment = ""
                                app_version = ""
                                is_hidden = False
                                
                                with open(desktop_file, "r", encoding="utf-8", errors="ignore") as f:
                                    for line in f:
                                        line = line.strip()
                                        if line.startswith("Name="):
                                            app_name = line[5:]
                                        elif line.startswith("Exec="):
                                            app_exec = line[5:]
                                        elif line.startswith("Path="):
                                            app_path = line[5:]
                                        elif line.startswith("Comment="):
                                            app_comment = line[8:]
                                        elif line.startswith("Version="):
                                            app_version = line[8:]
                                        elif line.startswith("NoDisplay=true") or line.startswith("Hidden=true"):
                                            is_hidden = True
                                
                                # Skip hidden applications unless system apps are requested
                                if is_hidden and not include_system:
                                    continue
                                
                                # Skip entries without a name
                                if not app_name:
                                    continue
                                
                                # If no path specified, try to determine it from Exec
                                if not app_path and app_exec:
                                    exec_parts = app_exec.split()
                                    if exec_parts:
                                        exec_cmd = exec_parts[0]
                                        
                                        # Try to find the executable path
                                        try:
                                            import subprocess
                                            result = subprocess.run(
                                                ["which", exec_cmd],
                                                capture_output=True,
                                                text=True
                                            )
                                            
                                            if result.returncode == 0:
                                                cmd_path = result.stdout.strip()
                                                if cmd_path:
                                                    app_path = os.path.dirname(cmd_path)
                                        except:
                                            pass
                                
                                app_info = {
                                    "name": app_name,
                                    "path": app_path or desktop_file,  # Use desktop file path if app path not found
                                    "exec": app_exec
                                }
                                
                                # Add additional info if detailed view requested
                                if detailed:
                                    if app_version:
                                        app_info["version"] = app_version
                                    if app_comment:
                                        app_info["description"] = app_comment
                                
                                # Add to the list
                                apps.append(app_info)
                            
                            except Exception as e:
                                logger.error(f"Error parsing desktop file {desktop_file}: {str(e)}")
            
            # Method 2: Check common application directories (as a fallback)
            if len(apps) == 0:
                common_dirs = [
                    "/usr/bin",
                    "/usr/local/bin",
                    "/opt"
                ]
                
                for directory in common_dirs:
                    if os.path.exists(directory):
                        for item in os.listdir(directory):
                            item_path = os.path.join(directory, item)
                            
                            # Skip non-executable files and directories
                            if os.path.isdir(item_path) or not os.access(item_path, os.X_OK):
                                continue
                            
                            # Add executable files
                            apps.append({
                                "name": item,
                                "path": item_path
                            })
        
        except Exception as e:
            logger.error(f"Error enumerating Linux applications: {str(e)}")
        
        return apps


class GetSystemPathsTool(BaseTool):
    """Tool for identifying common system paths."""
    
    name: str = "get_system_paths"
    description: str = """
    Returns the paths to common system locations like Desktop, Documents, Downloads, etc.
    
    No input is needed.
    Returns a dictionary of common system paths or error message.
    
    Use this tool to help locate standard directories on the user's system without
    requiring the user to provide explicit paths.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get paths to common system locations."""
        try:
            paths = {}
            system = platform.system()
            
            # Get home directory
            home = os.path.expanduser("~")
            paths["home"] = home
            
            # Define standard directories that exist across platforms
            standard_dirs = {
                "desktop": ["Desktop"],
                "documents": ["Documents", "My Documents"],
                "downloads": ["Downloads"],
                "pictures": ["Pictures", "My Pictures"],
                "music": ["Music", "My Music"],
                "videos": ["Videos", "My Videos"]
            }
            
            # Detect if we're running in a Replit environment
            in_replit = "REPL_ID" in os.environ or "REPLIT_DEPLOYMENT_ID" in os.environ
            if in_replit:
                # In Replit, create standard directories in workspace if they don't exist
                logger.info("Detected Replit environment. Creating standard directories in workspace.")
                workspace_dir = os.path.join(home, "workspace")
                paths["workspace"] = workspace_dir
                
                # Create standard directories within workspace
                for key, folders in standard_dirs.items():
                    folder_name = folders[0]  # Use the first folder name option
                    path = os.path.join(workspace_dir, folder_name)
                    # Create the directory if it doesn't exist
                    if not os.path.exists(path):
                        try:
                            os.makedirs(path, exist_ok=True)
                            logger.info(f"Created directory: {path}")
                        except Exception as e:
                            logger.error(f"Error creating directory {path}: {str(e)}")
                    paths[key] = path
            
            # Additional OS-specific paths (for non-Replit environments)
            elif system == "Windows":
                # Windows specific paths
                paths["appdata"] = os.getenv("APPDATA", "")
                paths["programfiles"] = os.getenv("ProgramFiles", "")
                paths["programfiles_x86"] = os.getenv("ProgramFiles(x86)", "")
                paths["temp"] = os.getenv("TEMP", "")
                
                # User folders are typically in a predictable location
                for key, folders in standard_dirs.items():
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
                
            elif system == "Darwin":  # macOS
                # macOS specific paths
                paths["applications"] = "/Applications"
                paths["library"] = os.path.join(home, "Library")
                
                # User folders follow macOS conventions
                for key, folders in standard_dirs.items():
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
                
            elif system == "Linux":
                # Linux specific paths
                paths["config"] = os.path.join(home, ".config")
                
                # Check XDG directories first (modern Linux)
                try:
                    import subprocess
                    xdg_dirs = {}
                    for key in ["DESKTOP", "DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS"]:
                        try:
                            result = subprocess.run(
                                ["xdg-user-dir", key], 
                                capture_output=True, 
                                text=True, 
                                check=True
                            )
                            xdg_path = result.stdout.strip()
                            if xdg_path and os.path.exists(xdg_path):
                                xdg_key = key.lower()
                                if xdg_key == "download":
                                    xdg_key = "downloads"
                                paths[xdg_key] = xdg_path
                        except (subprocess.SubprocessError, FileNotFoundError):
                            pass
                except ImportError:
                    pass
                
                # Fallback to standard directories
                for key, folders in standard_dirs.items():
                    if key not in paths:  # Only check if not already found via XDG
                        for folder in folders:
                            path = os.path.join(home, folder)
                            if os.path.exists(path):
                                paths[key] = path
                                break
            
            # Always check current working directory
            paths["current"] = os.getcwd()
            paths["workspace"] = os.getcwd()  # Add workspace alias pointing to current directory
            
            # Check if Python executable directory exists
            if hasattr(sys, 'executable') and sys.executable:
                paths["python"] = os.path.dirname(sys.executable)
            
            # Format the result
            result = "Common system paths detected:\n"
            for key, path in paths.items():
                if path:  # Only include non-empty paths
                    result += f"- {key}: {path}\n"
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting system paths: {str(e)}")
            return f"Error getting system paths: {str(e)}"
            
    """Tool for navigating to a specific system path."""
    
    name: str = "navigate_to_path"
    description: str = """
    Navigates to a specified system path, creating it if it doesn't exist (optional).
    
    Input:
        - Path string (e.g., "/path/to/directory" or "C:\\path\\to\\directory")
        - Or a shorthand name for common paths (e.g., "desktop", "documents", "downloads")
        - Add "--create" flag to create the directory if it doesn't exist
        - Add "--show" flag to list contents after navigating
    
    Returns the result of navigation attempt and directory information.
    
    Use this tool to navigate to specific locations on the file system.
    """
    
    def _run(self, input_str: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Navigate to a specified system path."""
        if not input_str.strip():
            return "Error: No path specified. Please provide a valid path or shorthand name."
        
        try:
            # Parse flags
            create_dir = "--create" in input_str
            show_contents = "--show" in input_str
            
            # Remove flags from input string
            path_str = input_str.replace("--create", "").replace("--show", "").strip()
            
            # Check if the input is a shorthand name
            system_paths = self._get_common_paths()
            target_path = system_paths.get(path_str.lower(), path_str)
            
            # Ensure path exists
            if not os.path.exists(target_path):
                if create_dir:
                    try:
                        os.makedirs(target_path, exist_ok=True)
                        result = f"Created and navigated to: {target_path}\n"
                    except Exception as e:
                        return f"Error creating directory '{target_path}': {str(e)}"
                else:
                    return f"Error: Path does not exist: {target_path}\nAdd '--create' flag to create it."
            else:
                result = f"Successfully navigated to: {target_path}\n"
            
            # Change current working directory
            os.chdir(target_path)
            
            # Get directory info
            result += f"Current working directory: {os.getcwd()}\n"
            
            # Show contents if requested
            if show_contents:
                try:
                    items = os.listdir(target_path)
                    dirs = [d for d in items if os.path.isdir(os.path.join(target_path, d))]
                    files = [f for f in items if os.path.isfile(os.path.join(target_path, f))]
                    
                    result += f"\nContents of {target_path}:\n"
                    result += "Directories:\n"
                    for d in dirs:
                        result += f"  - {d}/\n"
                    
                    result += "Files:\n"
                    for f in files:
                        size = os.path.getsize(os.path.join(target_path, f))
                        size_str = self._format_size(size)
                        result += f"  - {f} ({size_str})\n"
                except Exception as e:
                    result += f"\nError listing directory contents: {str(e)}"
            
            return result
        
        except Exception as e:
            logger.error(f"Error navigating to path: {str(e)}")
            return f"Error navigating to path: {str(e)}"
    
    def _get_common_paths(self) -> dict:
        """Get common system paths for shorthand navigation."""
        paths = {}
        home = os.path.expanduser("~")
        paths["home"] = home
        
        # Define standard directories
        standard_dirs = {
            "desktop": ["Desktop"],
            "documents": ["Documents", "My Documents"],
            "downloads": ["Downloads"],
            "pictures": ["Pictures", "My Pictures"],
            "music": ["Music", "My Music"],
            "videos": ["Videos", "My Videos"]
        }
        
        system = platform.system()
        
        if system == "Windows":
            paths["appdata"] = os.getenv("APPDATA", "")
            paths["localappdata"] = os.getenv("LOCALAPPDATA", "")
            paths["programfiles"] = os.getenv("ProgramFiles", "")
            paths["programfiles_x86"] = os.getenv("ProgramFiles(x86)", "")
            paths["temp"] = os.getenv("TEMP", "")
            
            # User folders
            for key, folders in standard_dirs.items():
                for folder in folders:
                    path = os.path.join(home, folder)
                    if os.path.exists(path):
                        paths[key] = path
                        break
        
        elif system == "Darwin":  # macOS
            paths["applications"] = "/Applications"
            paths["library"] = os.path.join(home, "Library")
            
            # User folders
            for key, folders in standard_dirs.items():
                for folder in folders:
                    path = os.path.join(home, folder)
                    if os.path.exists(path):
                        paths[key] = path
                        break
        
        elif system == "Linux":
            paths["config"] = os.path.join(home, ".config")
            paths["local_share"] = os.path.join(home, ".local", "share")
            paths["usr_bin"] = "/usr/bin"
            paths["usr_local_bin"] = "/usr/local/bin"
            
            # Try XDG directories first
            try:
                import subprocess
                for key in ["DESKTOP", "DOCUMENTS", "DOWNLOAD", "PICTURES", "MUSIC", "VIDEOS"]:
                    try:
                        result = subprocess.run(
                            ["xdg-user-dir", key], 
                            capture_output=True, 
                            text=True, 
                            check=True
                        )
                        xdg_path = result.stdout.strip()
                        if xdg_path and os.path.exists(xdg_path):
                            xdg_key = key.lower()
                            if xdg_key == "download":
                                xdg_key = "downloads"
                            paths[xdg_key] = xdg_path
                    except (subprocess.SubprocessError, FileNotFoundError):
                        pass
            except ImportError:
                pass
            
            # Fallback to standard directories
            for key, folders in standard_dirs.items():
                if key not in paths:
                    for folder in folders:
                        path = os.path.join(home, folder)
                        if os.path.exists(path):
                            paths[key] = path
                            break
        
        # Always include current directory
        paths["current"] = os.getcwd()
        paths["workspace"] = os.getcwd()
        
        return paths
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"