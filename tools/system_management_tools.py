"""
Advanced system management tools for the AI agent.
Includes operations for listing installed applications, uninstalling applications,
clearing temporary files, managing disk space, and system personalization.
"""

import sys

import os
import shutil
import platform
import subprocess
import json
from typing import Dict, List, Optional, Any, Union
import psutil
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


# Helper functions for system operations
def _run_platform_command(command: List[str]) -> str:
    """Run a platform-specific command and return the output."""
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def _get_platform() -> str:
    """Get the current platform (windows, macos, linux)."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system

def _get_file_size_str(size_in_bytes: int) -> str:
    """Convert file size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

class ListInstalledApplicationsTool(BaseTool):
    """Tool for listing installed applications on the system."""

    name: str = "list_installed_applications"
    description: str = """
    Lists installed applications on the system.
    On Windows, lists from Programs and Features.
    On macOS, lists applications from the Applications folder.
    On Linux, lists installed packages depending on the distribution.
    
    No input is required.
    Returns a list of installed applications.
    """

    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """List installed applications on the system."""
        try:
            # Check if running in Replit environment
            is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
            
            # If running in Replit environment, return sample data with disclaimer
            if is_replit:
                return """Installed Applications in Replit environment:

Application Verifier x64 External Package - Microsoft
Arduino IDE 2.3.2 - Arduino SA
CMake 4.0.0 - Kitware
Cursor (User) 0.49.5 - Anysphere
Dell Touchpad 10.3201.101.215 - ALPSALPINE CO., LTD.
Docker Desktop 4.36.0 - Docker Inc.
Git 2.47.0 - The Git Development Community
GitHub Desktop 3.4.5 - GitHub, Inc.
Google Chrome 136.0.7103.92 - Google LLC
Intel(R) Processor Graphics 20.19.15.4835 - Intel Corporation
Microsoft Edge 136.0.3240.50 - Microsoft Corporation
Microsoft OneDrive 25.065.0406.0002 - Microsoft Corporation
Microsoft Visual Studio Code (User) 1.99.3 - Microsoft Corporation
Node.js 22.4.1 - Node.js Foundation
Python 3.12.4 (64-bit) - Python Software Foundation
Raspberry Pi Imager 1.8.5 - Raspberry Pi Ltd

Note: This is example data. The actual list_installed_applications tool is designed to work on local machines. In this Replit environment, the list is simulated for demonstration purposes."""
            
            platform_name = _get_platform()
            
            if platform_name == "windows":
                # PowerShell command to get installed applications
                command = ["powershell", "-Command", 
                          "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, " +
                          "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, " +
                          "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | " +
                          "Where-Object { $_.DisplayName -ne $null } | " +
                          "Select-Object DisplayName, DisplayVersion, Publisher | " +
                          "Sort-Object DisplayName | Format-Table -AutoSize"]
                return _run_platform_command(command)
                
            elif platform_name == "macos":
                # List applications in the Applications folder
                command = ["find", "/Applications", "-maxdepth", "2", "-name", "*.app"]
                output = _run_platform_command(command)
                apps = [line.replace("/Applications/", "").replace(".app", "") for line in output.splitlines()]
                return "Installed Applications:\n" + "\n".join(sorted(apps))
                
            elif platform_name == "linux":
                # Try different package managers based on distribution
                if os.path.exists(resource_path("/usr/bin/dpkg")):  # Debian/Ubuntu
                    command = ["dpkg", "--get-selections"]
                elif os.path.exists(resource_path("/usr/bin/rpm")):  # Red Hat/Fedora
                    command = ["rpm", "-qa"]
                elif os.path.exists(resource_path("/usr/bin/pacman")):  # Arch Linux
                    command = ["pacman", "-Q"]
                else:
                    # If specific package manager not found, try a more generic approach
                    command = ["ls", "-la", "/usr/share/applications/"]
                
                output = _run_platform_command(command)
                return f"Installed Applications:\n{output}"
            
            else:
                return f"Unsupported platform: {platform_name}"
        
        except Exception as e:
            return f"Error listing installed applications: {str(e)}"

class UninstallApplicationTool(BaseTool):
    """Tool for uninstalling an application."""

    name: str = "uninstall_application"
    description: str = """
    Uninstalls an application from the system.
    
    Input should be the name of the application to uninstall.
    Returns confirmation or error message.
    
    Example: "Google Chrome" or "Microsoft Office"
    
    IMPORTANT: This tool will attempt to uninstall the specified application.
    Use with caution as it will permanently remove the application from the system.
    """

    def _run(self, app_name: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Uninstall an application from the system."""
        if not app_name.strip():
            return "Error: Application name is required."
        
        # Check if running in Replit environment
        is_replit = os.environ.get('REPL_ID') is not None or os.environ.get('REPL_OWNER') is not None
        if is_replit:
            return f"Cannot uninstall application '{app_name}' in the Replit environment. This tool is designed to work on local machines."
            
        platform_name = _get_platform()
        
        try:
            if platform_name == "windows":
                # PowerShell command to uninstall an application
                command = ["powershell", "-Command", 
                          f"$app = Get-WmiObject -Class Win32_Product | Where-Object {{ $_.Name -like '*{app_name}*' }}; " +
                          "if ($app) { $app.Uninstall() } else { Write-Output 'Application not found' }"]
                return _run_platform_command(command)
                
            elif platform_name == "macos":
                # Check if app exists in Applications folder
                app_path = f"/Applications/{app_name}.app"
                if not os.path.exists(app_path):
                    return f"Error: Application '{app_name}' not found in Applications folder."
                
                # Move to Trash
                command = ["osascript", "-e", f'tell application "Finder" to move POSIX file "{app_path}" to trash']
                _run_platform_command(command)
                return f"Application '{app_name}' has been moved to the Trash."
                
            elif platform_name == "linux":
                # Try different package managers based on distribution
                if os.path.exists(resource_path("/usr/bin/apt")):  # Debian/Ubuntu
                    command = ["apt", "remove", "-y", app_name]
                elif os.path.exists(resource_path("/usr/bin/yum")):  # Red Hat/Fedora
                    command = ["yum", "remove", "-y", app_name]
                elif os.path.exists(resource_path("/usr/bin/pacman")):  # Arch Linux
                    command = ["pacman", "-R", app_name]
                else:
                    return "Unsupported Linux distribution for uninstallation."
                
                return _run_platform_command(command)
            
            else:
                return f"Unsupported platform: {platform_name} for uninstallation."
        
        except Exception as e:
            return f"Error uninstalling application: {str(e)}"

class ClearRecycleBinTool(BaseTool):
    """Tool for clearing the Recycle Bin or Trash."""

    name: str = "clear_recycle_bin"
    description: str = """
    Clears the Recycle Bin (Windows) or Trash (macOS/Linux).
    
    No input is required.
    Returns confirmation or error message.
    
    IMPORTANT: This permanently deletes all files in the Recycle Bin/Trash.
    """

    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Clear the Recycle Bin or Trash."""
        platform_name = _get_platform()
        
        try:
            if platform_name == "windows":
                # PowerShell command to clear Recycle Bin
                command = ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"]
                _run_platform_command(command)
                return "Recycle Bin has been emptied."
                
            elif platform_name == "macos":
                # AppleScript to empty Trash
                command = ["osascript", "-e", 'tell app "Finder" to empty trash']
                _run_platform_command(command)
                return "Trash has been emptied."
                
            elif platform_name == "linux":
                # Empty trash on Linux
                home_dir = os.path.expanduser("~")
                trash_dirs = [
                    os.path.join(home_dir, ".local/share/Trash/files"),
                    os.path.join(home_dir, ".local/share/Trash/info")
                ]
                
                for trash_dir in trash_dirs:
                    if os.path.exists(trash_dir):
                        for item in os.listdir(trash_dir):
                            item_path = os.path.join(trash_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
                            else:
                                os.remove(item_path)
                
                return "Trash has been emptied."
            
            else:
                return f"Unsupported platform: {platform_name}"
        
        except Exception as e:
            return f"Error clearing Recycle Bin/Trash: {str(e)}"

class FreeDiskSpaceTool(BaseTool):
    """Tool for analyzing and freeing disk space."""

    name: str = "free_disk_space"
    description: str = """
    Analyzes disk space usage and provides options to free up space.
    
    Input should be a JSON object with:
    - 'action': 'analyze' to show disk usage, 'cleanup_temp' to clean temporary files, 'cleanup_downloads' to clean downloads folder
    
    Example: {"action": "analyze"} or {"action": "cleanup_temp"}
    
    Returns disk space information or cleanup results.
    """

    def _run(self, space_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Analyze and free disk space."""
        try:
            # Parse the input as JSON
            if not space_info_str or space_info_str.strip() == "":
                space_info = {"action": "analyze"}  # Default action
            else:
                space_info = json.loads(space_info_str)
            
            action = space_info.get("action", "analyze").lower()
            
            if action == "analyze":
                return self._analyze_disk_space()
            elif action == "cleanup_temp":
                return self._cleanup_temp_files()
            elif action == "cleanup_downloads":
                return self._cleanup_downloads_folder()
            else:
                return f"Unknown action: {action}. Supported actions are: analyze, cleanup_temp, cleanup_downloads."
        
        except json.JSONDecodeError:
            return "Error: Input must be a valid JSON object."
        except Exception as e:
            return f"Error during disk space operation: {str(e)}"
    
    def _analyze_disk_space(self) -> str:
        """Analyze disk space usage."""
        results = []
        
        for partition in psutil.disk_partitions():
            if os.name == 'nt' and ('cdrom' in partition.opts or partition.fstype == ''):
                # Skip CD-ROM drives on Windows
                continue
                
            usage = psutil.disk_usage(partition.mountpoint)
            
            disk_info = {
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": _get_file_size_str(usage.total),
                "used": _get_file_size_str(usage.used),
                "free": _get_file_size_str(usage.free),
                "percent": usage.percent
            }
            
            results.append(disk_info)
        
        # Format the results
        output = "Disk Space Analysis:\n\n"
        for disk in results:
            output += f"Mount Point: {disk['mountpoint']}\n"
            output += f"File System Type: {disk['fstype']}\n"
            output += f"Total Space: {disk['total']}\n"
            output += f"Used Space: {disk['used']} ({disk['percent']}%)\n"
            output += f"Free Space: {disk['free']}\n"
            output += "-" * 40 + "\n"
        
        return output
    
    def _cleanup_temp_files(self) -> str:
        """Clean up temporary files."""
        platform_name = _get_platform()
        files_removed = 0
        space_freed = 0
        
        try:
            temp_dirs = []
            
            if platform_name == "windows":
                # Windows temp directories
                temp_dirs = [
                    os.environ.get('TEMP', ''),
                    os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Temp'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp')
                ]
            elif platform_name in ["macos", "linux"]:
                # macOS and Linux temp directories
                temp_dirs = [
                    '/tmp',
                    os.path.expanduser('~/Library/Caches') if platform_name == "macos" else '',
                    os.path.expanduser('~/.cache') if platform_name == "linux" else ''
                ]
            
            # Filter out empty paths
            temp_dirs = [d for d in temp_dirs if d]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir, topdown=False):
                        for name in files:
                            try:
                                file_path = os.path.join(root, name)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    files_removed += 1
                                    space_freed += file_size
                            except (PermissionError, FileNotFoundError, OSError):
                                # Skip files that can't be removed
                                pass
                        
                        for name in dirs:
                            try:
                                dir_path = os.path.join(root, name)
                                if os.path.isdir(dir_path) and not os.listdir(dir_path):
                                    os.rmdir(dir_path)
                            except (PermissionError, FileNotFoundError, OSError):
                                # Skip directories that can't be removed
                                pass
            
            return f"Cleanup complete. Removed {files_removed} temporary files, freeing {_get_file_size_str(space_freed)} of disk space."
        
        except Exception as e:
            return f"Error during temp file cleanup: {str(e)}"
    
    def _cleanup_downloads_folder(self) -> str:
        """Clean up the Downloads folder."""
        try:
            # Get the Downloads folder path
            if platform.system() == "Windows":
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            elif platform.system() == "Darwin":  # macOS
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            else:  # Linux and others
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            
            if not os.path.exists(downloads_path):
                return f"Downloads folder not found at {downloads_path}"
            
            # List files in Downloads folder with sizes
            files_info = []
            total_size = 0
            
            for item in os.listdir(downloads_path):
                item_path = os.path.join(downloads_path, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    total_size += size
                    files_info.append({
                        "name": item,
                        "size": size,
                        "size_str": _get_file_size_str(size),
                        "modified": os.path.getmtime(item_path)
                    })
            
            # Sort by size (largest first)
            files_info.sort(key=lambda x: x["size"], reverse=True)
            
            output = f"Downloads Folder Analysis ({_get_file_size_str(total_size)} total):\n\n"
            output += f"Location: {downloads_path}\n"
            output += f"Number of files: {len(files_info)}\n\n"
            
            if files_info:
                output += "Largest files (top 10):\n"
                for i, file_info in enumerate(files_info[:10]):
                    output += f"{i+1}. {file_info['name']} - {file_info['size_str']}\n"
            
            output += "\nTo clean the Downloads folder, use the clean_specific_files tool with specific file patterns or ask for guidance."
            
            return output
        
        except Exception as e:
            return f"Error analyzing Downloads folder: {str(e)}"

class SystemInfoTool(BaseTool):
    """Tool for getting detailed system information."""

    name: str = "get_detailed_system_info"
    description: str = """
    Provides detailed information about the system hardware, OS, and resources.
    
    Input should be a JSON object with:
    - 'info_type': Type of information to retrieve (optional). 
      Options: 'all' (default), 'cpu', 'memory', 'disk', 'network', 'os'
    
    Example: {"info_type": "cpu"} or {} for all information
    
    Returns detailed system information based on the requested type.
    """

    def _run(self, info_request_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get detailed system information."""
        try:
            # Parse the input as JSON
            if not info_request_str or info_request_str.strip() == "":
                info_request = {"info_type": "all"}  # Default to all info
            else:
                info_request = json.loads(info_request_str)
            
            info_type = info_request.get("info_type", "all").lower()
            
            if info_type == "all":
                return self._get_all_system_info()
            elif info_type == "cpu":
                return self._get_cpu_info()
            elif info_type == "memory":
                return self._get_memory_info()
            elif info_type == "disk":
                return self._get_disk_info()
            elif info_type == "network":
                return self._get_network_info()
            elif info_type == "os":
                return self._get_os_info()
            else:
                return f"Unknown info_type: {info_type}. Supported types are: all, cpu, memory, disk, network, os."
        
        except json.JSONDecodeError:
            return "Error: Input must be a valid JSON object."
        except Exception as e:
            return f"Error retrieving system information: {str(e)}"
    
    def _get_all_system_info(self) -> str:
        """Get all system information."""
        return (
            "SYSTEM INFORMATION\n" +
            "=" * 50 + "\n\n" +
            self._get_os_info() + "\n\n" +
            self._get_cpu_info() + "\n\n" +
            self._get_memory_info() + "\n\n" +
            self._get_disk_info() + "\n\n" +
            self._get_network_info()
        )
    
    def _get_os_info(self) -> str:
        """Get operating system information."""
        os_info = platform.uname()
        
        return (
            "OPERATING SYSTEM INFORMATION\n" +
            "-" * 30 + "\n" +
            f"System: {os_info.system}\n" +
            f"Node Name: {os_info.node}\n" +
            f"Release: {os_info.release}\n" +
            f"Version: {os_info.version}\n" +
            f"Machine: {os_info.machine}\n" +
            f"Processor: {os_info.processor}\n" +
            f"Python Version: {platform.python_version()}\n"
        )
    
    def _get_cpu_info(self) -> str:
        """Get CPU information."""
        cpu_info = {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "current_frequency": psutil.cpu_freq() if hasattr(psutil, 'cpu_freq') and psutil.cpu_freq() else None,
            "usage_percent": psutil.cpu_percent(interval=1, percpu=True)
        }
        
        result = "CPU INFORMATION\n" + "-" * 30 + "\n"
        result += f"Logical CPU Cores: {cpu_info['logical_cores']}\n"
        result += f"Physical CPU Cores: {cpu_info['physical_cores']}\n"
        
        if cpu_info['current_frequency']:
            result += f"Current Frequency: {cpu_info['current_frequency'].current:.2f} MHz\n"
            if hasattr(cpu_info['current_frequency'], 'min') and cpu_info['current_frequency'].min:
                result += f"Minimum Frequency: {cpu_info['current_frequency'].min:.2f} MHz\n"
            if hasattr(cpu_info['current_frequency'], 'max') and cpu_info['current_frequency'].max:
                result += f"Maximum Frequency: {cpu_info['current_frequency'].max:.2f} MHz\n"
        
        result += "\nCPU Usage per Core:\n"
        for i, percentage in enumerate(cpu_info['usage_percent']):
            result += f"Core {i+1}: {percentage:.1f}%\n"
        
        return result
    
    def _get_memory_info(self) -> str:
        """Get memory information."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return (
            "MEMORY INFORMATION\n" +
            "-" * 30 + "\n" +
            f"Total Memory: {_get_file_size_str(memory.total)}\n" +
            f"Available Memory: {_get_file_size_str(memory.available)}\n" +
            f"Used Memory: {_get_file_size_str(memory.used)} ({memory.percent}%)\n" +
            f"Free Memory: {_get_file_size_str(memory.free)}\n" +
            "\nSWAP INFORMATION\n" +
            f"Total Swap: {_get_file_size_str(swap.total)}\n" +
            f"Used Swap: {_get_file_size_str(swap.used)} ({swap.percent}%)\n" +
            f"Free Swap: {_get_file_size_str(swap.free)}\n"
        )
    
    def _get_disk_info(self) -> str:
        """Get disk information."""
        result = "DISK INFORMATION\n" + "-" * 30 + "\n"
        
        for i, partition in enumerate(psutil.disk_partitions()):
            if os.name == 'nt' and ('cdrom' in partition.opts or partition.fstype == ''):
                # Skip CD-ROM drives on Windows
                continue
            
            usage = psutil.disk_usage(partition.mountpoint)
            
            result += f"Disk {i+1}:\n"
            result += f"  Mount Point: {partition.mountpoint}\n"
            result += f"  File System Type: {partition.fstype}\n"
            result += f"  Total Space: {_get_file_size_str(usage.total)}\n"
            result += f"  Used Space: {_get_file_size_str(usage.used)} ({usage.percent}%)\n"
            result += f"  Free Space: {_get_file_size_str(usage.free)}\n\n"
        
        # Disk I/O statistics
        try:
            disk_io = psutil.disk_io_counters()
            result += "Disk I/O Statistics:\n"
            result += f"  Read Count: {disk_io.read_count}\n"
            result += f"  Write Count: {disk_io.write_count}\n"
            result += f"  Read Bytes: {_get_file_size_str(disk_io.read_bytes)}\n"
            result += f"  Write Bytes: {_get_file_size_str(disk_io.write_bytes)}\n"
        except Exception:
            result += "Disk I/O Statistics: Not available\n"
        
        return result
    
    def _get_network_info(self) -> str:
        """Get network information."""
        result = "NETWORK INFORMATION\n" + "-" * 30 + "\n"
        
        # Network interfaces
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        
        for interface_name, addresses in if_addrs.items():
            stats = if_stats.get(interface_name)
            result += f"Interface: {interface_name}\n"
            
            if stats:
                result += f"  Status: {'Up' if stats.isup else 'Down'}\n"
                result += f"  Speed: {stats.speed} Mbps\n"
                result += f"  MTU: {stats.mtu}\n"
            
            for addr in addresses:
                if addr.family == 2:  # IPv4
                    result += f"  IPv4 Address: {addr.address}\n"
                    result += f"  Netmask: {addr.netmask}\n"
                elif addr.family == 23:  # IPv6
                    result += f"  IPv6 Address: {addr.address}\n"
                elif addr.family == 17:  # MAC
                    result += f"  MAC Address: {addr.address}\n"
            
            result += "\n"
        
        # Network I/O statistics
        try:
            net_io = psutil.net_io_counters()
            result += "Network I/O Statistics:\n"
            result += f"  Bytes Sent: {_get_file_size_str(net_io.bytes_sent)}\n"
            result += f"  Bytes Received: {_get_file_size_str(net_io.bytes_recv)}\n"
            result += f"  Packets Sent: {net_io.packets_sent}\n"
            result += f"  Packets Received: {net_io.packets_recv}\n"
        except Exception:
            result += "Network I/O Statistics: Not available\n"
        
        return result

class NetworkManagementTool(BaseTool):
    """Tool for managing network connections (WiFi, Bluetooth, etc.)."""

    name: str = "manage_network"
    description: str = """
    Manages network connections including WiFi, Bluetooth, and more.
    
    Input should be a JSON object with:
    - 'action': The action to perform ('status', 'toggle_wifi', 'toggle_bluetooth', 'list_wifi')
    - 'state' (optional): For toggle actions, 'on' or 'off' (defaults to toggle current state)
    
    Example: {"action": "status"} or {"action": "toggle_wifi", "state": "on"}
    
    Returns the status of the requested action or information.
    """

    def _run(self, network_request_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage network connections."""
        try:
            # Parse the input as JSON
            if not network_request_str or network_request_str.strip() == "":
                network_request = {"action": "status"}  # Default to status
            else:
                network_request = json.loads(network_request_str)
            
            action = network_request.get("action", "status").lower()
            state = network_request.get("state", "").lower()
            
            platform_name = _get_platform()
            
            if action == "status":
                return self._get_network_status(platform_name)
            elif action == "toggle_wifi":
                return self._toggle_wifi(platform_name, state)
            elif action == "toggle_bluetooth":
                return self._toggle_bluetooth(platform_name, state)
            elif action == "list_wifi":
                return self._list_wifi_networks(platform_name)
            else:
                return f"Unknown action: {action}. Supported actions are: status, toggle_wifi, toggle_bluetooth, list_wifi."
        
        except json.JSONDecodeError:
            return "Error: Input must be a valid JSON object."
        except Exception as e:
            return f"Error during network management: {str(e)}"
    
    def _get_network_status(self, platform: str) -> str:
        """Get the current status of network connections."""
        result = "NETWORK CONNECTION STATUS\n" + "-" * 30 + "\n"
        
        try:
            # Network interfaces status
            if_stats = psutil.net_if_stats()
            
            result += "Network Interfaces:\n"
            for interface_name, stats in if_stats.items():
                result += f"  {interface_name}: {'Connected' if stats.isup else 'Disconnected'}\n"
            
            # WiFi status (platform specific)
            if platform == "windows":
                wifi_status = _run_platform_command(["netsh", "wlan", "show", "interfaces"])
                result += f"\nWiFi Status:\n{wifi_status}\n"
            elif platform == "macos":
                wifi_status = _run_platform_command(["/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport", "-I"])
                result += f"\nWiFi Status:\n{wifi_status}\n"
            elif platform == "linux":
                if os.path.exists(resource_path("/usr/sbin/iwconfig")):
                    wifi_status = _run_platform_command(["iwconfig"])
                    result += f"\nWiFi Status:\n{wifi_status}\n"
            
            # Bluetooth status (platform specific)
            if platform == "windows":
                # Using PowerShell to get Bluetooth status
                bt_status = _run_platform_command(["powershell", "-Command", 
                                                 "Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Select-Object Status, Name"])
                result += f"\nBluetooth Status:\n{bt_status}\n"
            elif platform == "macos":
                bt_status = _run_platform_command(["system_profiler", "SPBluetoothDataType"])
                result += f"\nBluetooth Status:\n{bt_status}\n"
            elif platform == "linux":
                if os.path.exists(resource_path("/usr/bin/bluetoothctl")):
                    bt_status = _run_platform_command(["bluetoothctl", "show"])
                    result += f"\nBluetooth Status:\n{bt_status}\n"
            
            return result
        
        except Exception as e:
            return f"Error getting network status: {str(e)}"
    
    def _toggle_wifi(self, platform: str, state: str) -> str:
        """Toggle WiFi on or off."""
        try:
            if platform == "windows":
                if state == "on":
                    _run_platform_command(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enabled"])
                    return "WiFi has been enabled."
                elif state == "off":
                    _run_platform_command(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disabled"])
                    return "WiFi has been disabled."
                else:
                    # Toggle current state
                    wifi_status = _run_platform_command(["netsh", "wlan", "show", "interfaces"])
                    if "State : connected" in wifi_status:
                        _run_platform_command(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disabled"])
                        return "WiFi has been disabled."
                    else:
                        _run_platform_command(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enabled"])
                        return "WiFi has been enabled."
            
            elif platform == "macos":
                if state == "on":
                    _run_platform_command(["networksetup", "-setairportpower", "en0", "on"])
                    return "WiFi has been enabled."
                elif state == "off":
                    _run_platform_command(["networksetup", "-setairportpower", "en0", "off"])
                    return "WiFi has been disabled."
                else:
                    # Toggle current state
                    wifi_status = _run_platform_command(["networksetup", "-getairportpower", "en0"])
                    if "On" in wifi_status:
                        _run_platform_command(["networksetup", "-setairportpower", "en0", "off"])
                        return "WiFi has been disabled."
                    else:
                        _run_platform_command(["networksetup", "-setairportpower", "en0", "on"])
                        return "WiFi has been enabled."
            
            elif platform == "linux":
                if os.path.exists(resource_path("/usr/sbin/nmcli")):
                    if state == "on":
                        _run_platform_command(["nmcli", "radio", "wifi", "on"])
                        return "WiFi has been enabled."
                    elif state == "off":
                        _run_platform_command(["nmcli", "radio", "wifi", "off"])
                        return "WiFi has been disabled."
                    else:
                        # Toggle current state
                        wifi_status = _run_platform_command(["nmcli", "radio", "wifi"])
                        if "enabled" in wifi_status.lower():
                            _run_platform_command(["nmcli", "radio", "wifi", "off"])
                            return "WiFi has been disabled."
                        else:
                            _run_platform_command(["nmcli", "radio", "wifi", "on"])
                            return "WiFi has been enabled."
                else:
                    return "WiFi management requires NetworkManager (nmcli) which is not available."
            
            else:
                return f"WiFi toggling is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error toggling WiFi: {str(e)}"
    
    def _toggle_bluetooth(self, platform: str, state: str) -> str:
        """Toggle Bluetooth on or off."""
        try:
            if platform == "windows":
                # Using PowerShell to toggle Bluetooth
                if state == "on":
                    _run_platform_command(["powershell", "-Command", 
                                         "$bluetooth = Get-Service bthserv; if ($bluetooth.Status -ne 'Running') { Start-Service bthserv }"])
                    return "Bluetooth service has been started. You may need to enable it in Windows settings."
                elif state == "off":
                    _run_platform_command(["powershell", "-Command", 
                                         "$bluetooth = Get-Service bthserv; if ($bluetooth.Status -eq 'Running') { Stop-Service bthserv }"])
                    return "Bluetooth service has been stopped."
                else:
                    # Toggle current state
                    bt_status = _run_platform_command(["powershell", "-Command", "Get-Service bthserv | Select-Object Status"])
                    if "Running" in bt_status:
                        _run_platform_command(["powershell", "-Command", "Stop-Service bthserv"])
                        return "Bluetooth service has been stopped."
                    else:
                        _run_platform_command(["powershell", "-Command", "Start-Service bthserv"])
                        return "Bluetooth service has been started. You may need to enable it in Windows settings."
            
            elif platform == "macos":
                if state == "on":
                    _run_platform_command(["defaults", "write", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState", "1"])
                    _run_platform_command(["killall", "-HUP", "blued"])
                    return "Bluetooth has been enabled."
                elif state == "off":
                    _run_platform_command(["defaults", "write", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState", "0"])
                    _run_platform_command(["killall", "-HUP", "blued"])
                    return "Bluetooth has been disabled."
                else:
                    # Toggle current state
                    bt_status = _run_platform_command(["defaults", "read", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState"])
                    if "1" in bt_status:
                        _run_platform_command(["defaults", "write", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState", "0"])
                        _run_platform_command(["killall", "-HUP", "blued"])
                        return "Bluetooth has been disabled."
                    else:
                        _run_platform_command(["defaults", "write", "/Library/Preferences/com.apple.Bluetooth", "ControllerPowerState", "1"])
                        _run_platform_command(["killall", "-HUP", "blued"])
                        return "Bluetooth has been enabled."
            
            elif platform == "linux":
                if os.path.exists(resource_path("/usr/bin/bluetoothctl")):
                    if state == "on":
                        _run_platform_command(["bluetoothctl", "power", "on"])
                        return "Bluetooth has been enabled."
                    elif state == "off":
                        _run_platform_command(["bluetoothctl", "power", "off"])
                        return "Bluetooth has been disabled."
                    else:
                        # Toggle current state
                        bt_status = _run_platform_command(["bluetoothctl", "show"])
                        if "Powered: yes" in bt_status:
                            _run_platform_command(["bluetoothctl", "power", "off"])
                            return "Bluetooth has been disabled."
                        else:
                            _run_platform_command(["bluetoothctl", "power", "on"])
                            return "Bluetooth has been enabled."
                else:
                    return "Bluetooth management requires bluetoothctl which is not available."
            
            else:
                return f"Bluetooth toggling is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error toggling Bluetooth: {str(e)}"
    
    def _list_wifi_networks(self, platform: str) -> str:
        """List available WiFi networks."""
        try:
            if platform == "windows":
                wifi_list = _run_platform_command(["netsh", "wlan", "show", "networks", "mode=Bssid"])
                return f"Available WiFi Networks:\n{wifi_list}"
            
            elif platform == "macos":
                wifi_list = _run_platform_command(["/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport", "-s"])
                return f"Available WiFi Networks:\n{wifi_list}"
            
            elif platform == "linux":
                if os.path.exists(resource_path("/usr/sbin/nmcli")):
                    wifi_list = _run_platform_command(["nmcli", "device", "wifi", "list"])
                    return f"Available WiFi Networks:\n{wifi_list}"
                elif os.path.exists(resource_path("/usr/sbin/iwlist")):
                    # Find wireless interface name
                    interfaces = _run_platform_command(["iwconfig"])
                    interface_name = None
                    for line in interfaces.splitlines():
                        if "IEEE 802.11" in line:
                            interface_name = line.split()[0]
                            break
                    
                    if interface_name:
                        wifi_list = _run_platform_command(["iwlist", interface_name, "scan"])
                        return f"Available WiFi Networks:\n{wifi_list}"
                    else:
                        return "No wireless interface found."
                else:
                    return "WiFi network listing requires NetworkManager (nmcli) or iwlist which are not available."
            
            else:
                return f"WiFi network listing is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error listing WiFi networks: {str(e)}"

class PersonalizationTool(BaseTool):
    """Tool for personalizing system settings."""

    name: str = "personalize_system"
    description: str = """
    Personalizes system settings including wallpaper, themes, lock screen, etc.
    
    Input should be a JSON object with:
    - 'action': The personalization action to perform ('set_wallpaper', 'set_theme', 'set_lockscreen', etc.)
    - 'path': Path to image file (for wallpaper/lockscreen) or setting value, depending on action
    
    Example: {"action": "set_wallpaper", "path": "/path/to/image.jpg"}
    
    Returns confirmation or error message.
    """

    def _run(self, personalization_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Personalize system settings."""
        try:
            # Parse the input as JSON
            if not personalization_str or personalization_str.strip() == "":
                return "Error: Personalization options are required."
            
            personalization = json.loads(personalization_str)
            
            action = personalization.get("action", "").lower()
            path = personalization.get("path", "")
            
            platform_name = _get_platform()
            
            if action == "set_wallpaper":
                return self._set_wallpaper(platform_name, path)
            elif action == "set_theme":
                return self._set_theme(platform_name, path)
            elif action == "set_lockscreen":
                return self._set_lockscreen(platform_name, path)
            else:
                return f"Unknown action: {action}. Supported actions are: set_wallpaper, set_theme, set_lockscreen."
        
        except json.JSONDecodeError:
            return "Error: Input must be a valid JSON object."
        except Exception as e:
            return f"Error during system personalization: {str(e)}"
    
    def _set_wallpaper(self, platform: str, path: str) -> str:
        """Set system wallpaper."""
        if not path:
            return "Error: Image path is required to set wallpaper."
        
        if not os.path.exists(path):
            return f"Error: Image file not found at path: {path}"
        
        try:
            if platform == "windows":
                import ctypes
                SPI_SETDESKWALLPAPER = 20
                ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, path, 3)
                return f"Wallpaper has been set to: {path}"
            
            elif platform == "macos":
                command = ['osascript', '-e', f'tell application "Finder" to set desktop picture to POSIX file "{path}"']
                _run_platform_command(command)
                return f"Wallpaper has been set to: {path}"
            
            elif platform == "linux":
                # Try different commands for various desktop environments
                desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                
                if "gnome" in desktop_env or "unity" in desktop_env:
                    _run_platform_command(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{path}"])
                    return f"Wallpaper has been set to: {path}"
                elif "kde" in desktop_env:
                    # KDE Plasma 5
                    _run_platform_command([
                        "qdbus", "org.kde.plasmashell", "/PlasmaShell", 
                        "org.kde.PlasmaShell.evaluateScript", 
                        f"""
                        var allDesktops = desktops();
                        for (i=0; i < allDesktops.length; i++) {{
                            d = allDesktops[i];
                            d.wallpaperPlugin = "org.kde.image";
                            d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                            d.writeConfig("Image", "file://{path}");
                        }}
                        """
                    ])
                    return f"Wallpaper has been set to: {path}"
                elif "xfce" in desktop_env:
                    _run_platform_command(["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", path])
                    return f"Wallpaper has been set to: {path}"
                elif "mate" in desktop_env:
                    _run_platform_command(["gsettings", "set", "org.mate.background", "picture-filename", path])
                    return f"Wallpaper has been set to: {path}"
                elif "cinnamon" in desktop_env:
                    _run_platform_command(["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", f"file://{path}"])
                    return f"Wallpaper has been set to: {path}"
                else:
                    return f"Setting wallpaper for {desktop_env} is not supported. Please set it manually."
            
            else:
                return f"Setting wallpaper is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error setting wallpaper: {str(e)}"
    
    def _set_theme(self, platform: str, theme: str) -> str:
        """Set system theme."""
        if not theme:
            return "Error: Theme name or mode is required."
        
        try:
            if platform == "windows":
                import winreg
                theme_mode = theme.lower()
                if theme_mode in ["dark", "light"]:
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                    registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                    
                    # 0 for dark mode, 1 for light mode
                    value = 0 if theme_mode == "dark" else 1
                    winreg.SetValueEx(registry_key, "AppsUseLightTheme", 0, winreg.REG_DWORD, value)
                    winreg.SetValueEx(registry_key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, value)
                    winreg.CloseKey(registry_key)
                    return f"System theme has been set to {theme_mode} mode."
                else:
                    return "Only 'dark' and 'light' themes are supported on Windows. Please specify one of these."
            
            elif platform == "macos":
                theme_mode = theme.lower()
                if theme_mode in ["dark", "light"]:
                    value = "true" if theme_mode == "dark" else "false"
                    _run_platform_command(["defaults", "write", "-g", "AppleInterfaceStyle", value])
                    return f"System theme has been set to {theme_mode} mode. You may need to restart for changes to take effect."
                else:
                    return "Only 'dark' and 'light' themes are supported on macOS. Please specify one of these."
            
            elif platform == "linux":
                desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                theme_mode = theme.lower()
                
                if "gnome" in desktop_env or "unity" in desktop_env:
                    if theme_mode in ["dark", "light"]:
                        value = "prefer-dark" if theme_mode == "dark" else "prefer-light"
                        _run_platform_command(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", value])
                        return f"System theme has been set to {theme_mode} mode."
                    else:
                        # Try setting a GTK theme directly
                        _run_platform_command(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", theme])
                        return f"GTK theme has been set to: {theme}"
                elif "kde" in desktop_env:
                    # KDE theme setting
                    if theme_mode in ["dark", "light"]:
                        scheme = "BreezeDark" if theme_mode == "dark" else "Breeze"
                        _run_platform_command(["lookandfeeltool", "-a", scheme])
                        return f"KDE theme has been set to {scheme}."
                    else:
                        return "Only 'dark' and 'light' themes are supported for KDE. Please specify one of these."
                else:
                    return f"Setting theme for {desktop_env} is not supported. Please set it manually."
            
            else:
                return f"Setting theme is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error setting theme: {str(e)}"
    
    def _set_lockscreen(self, platform: str, path: str) -> str:
        """Set lock screen image."""
        if not path:
            return "Error: Image path is required to set lock screen."
        
        if not os.path.exists(path):
            return f"Error: Image file not found at path: {path}"
        
        try:
            if platform == "windows":
                import winreg
                # Register the image as lock screen
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\PersonalizationCSP"
                
                try:
                    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    winreg.SetValueEx(key, "LockScreenImagePath", 0, winreg.REG_SZ, path)
                    winreg.SetValueEx(key, "LockScreenImageUrl", 0, winreg.REG_SZ, path)
                    winreg.SetValueEx(key, "LockScreenImageStatus", 0, winreg.REG_DWORD, 1)
                    winreg.CloseKey(key)
                    return f"Lock screen image has been set to: {path}"
                except Exception as e:
                    # Alternative method using PowerShell for Windows 10/11
                    path_escaped = path.replace('\\', '\\\\')
                    command = ["powershell", "-Command", 
                              "$image = '" + path_escaped + "'; " +
                              "$key = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\PersonalizationCSP'; " +
                              "if (!(Test-Path $key)) { New-Item -Path $key -Force | Out-Null }; " +
                              "New-ItemProperty -Path $key -Name 'LockScreenImagePath' -Value $image -PropertyType String -Force | Out-Null; " +
                              "New-ItemProperty -Path $key -Name 'LockScreenImageUrl' -Value $image -PropertyType String -Force | Out-Null; " +
                              "New-ItemProperty -Path $key -Name 'LockScreenImageStatus' -Value 1 -PropertyType DWORD -Force | Out-Null"]
                    _run_platform_command(command)
                    return f"Lock screen image has been set to: {path} (may require admin privileges)"
            
            elif platform == "macos":
                return "Setting lock screen image on macOS requires system preferences access. Please use the System Preferences app."
            
            elif platform == "linux":
                desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                
                if "gnome" in desktop_env:
                    _run_platform_command(["gsettings", "set", "org.gnome.desktop.screensaver", "picture-uri", f"file://{path}"])
                    return f"Lock screen image has been set to: {path}"
                elif "kde" in desktop_env:
                    # KDE lock screen configuration
                    return "Setting lock screen image on KDE requires manual configuration. Please use System Settings."
                else:
                    return f"Setting lock screen for {desktop_env} is not supported. Please set it manually."
            
            else:
                return f"Setting lock screen is not supported on platform: {platform}"
        
        except Exception as e:
            return f"Error setting lock screen: {str(e)}"

class RunningProcessesTool(BaseTool):
    """Tool for managing running processes."""

    name: str = "manage_processes"
    description: str = """
    Views and manages running processes on the system.
    
    Input should be a JSON object with:
    - 'action': The action to perform ('list', 'kill', 'details')
    - 'process' (optional): Process ID or name for 'kill' or 'details' actions
    - 'sort_by' (optional): For 'list' action, how to sort processes ('cpu', 'memory', 'name', 'pid')
    
    Example: {"action": "list", "sort_by": "cpu"} or {"action": "kill", "process": "notepad.exe"}
    
    Returns process information or action confirmation.
    """

    def _run(self, process_request_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage running processes."""
        try:
            # Parse the input as JSON
            if not process_request_str or process_request_str.strip() == "":
                process_request = {"action": "list"}  # Default to listing processes
            else:
                process_request = json.loads(process_request_str)
            
            action = process_request.get("action", "list").lower()
            process = process_request.get("process", "")
            sort_by = process_request.get("sort_by", "cpu").lower()
            
            if action == "list":
                return self._list_processes(sort_by)
            elif action == "kill":
                return self._kill_process(process)
            elif action == "details":
                return self._get_process_details(process)
            else:
                return f"Unknown action: {action}. Supported actions are: list, kill, details."
        
        except json.JSONDecodeError:
            return "Error: Input must be a valid JSON object."
        except Exception as e:
            return f"Error managing processes: {str(e)}"
    
    def _list_processes(self, sort_by: str) -> str:
        """List running processes sorted by specified criteria."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    # Get process info
                    proc_info = proc.info
                    
                    # Update CPU and memory usage
                    proc.cpu_percent()  # First call returns 0, this just initializes it
                    proc_info['memory_percent'] = proc.memory_percent()
                    
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Wait a bit to get meaningful CPU % values
            import time
            time.sleep(0.1)
            
            # Update CPU percentages after waiting
            for i, proc_info in enumerate(processes):
                try:
                    proc = psutil.Process(proc_info['pid'])
                    processes[i]['cpu_percent'] = proc.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    processes[i]['cpu_percent'] = 0.0
            
            # Sort processes by specified criteria
            if sort_by == "cpu":
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x.get('name', '').lower())
            elif sort_by == "pid":
                processes.sort(key=lambda x: x.get('pid', 0))
            
            # Format the results
            result = f"RUNNING PROCESSES (sorted by {sort_by}):\n" + "-" * 80 + "\n"
            result += f"{'PID':<8} {'CPU %':<8} {'MEM %':<8} {'USER':<15} {'NAME':<30}\n"
            result += "-" * 80 + "\n"
            
            # Show top 50 processes
            for proc in processes[:50]:
                pid = proc.get('pid', 'N/A')
                cpu = f"{proc.get('cpu_percent', 0):.1f}"
                memory = f"{proc.get('memory_percent', 0):.1f}"
                user = proc.get('username', 'N/A')
                name = proc.get('name', 'Unknown')
                
                result += f"{pid:<8} {cpu:<8} {memory:<8} {user[:15]:<15} {name[:30]:<30}\n"
            
            result += f"\nShowing top 50 processes. Total processes: {len(processes)}"
            return result
        
        except Exception as e:
            return f"Error listing processes: {str(e)}"
    
    def _kill_process(self, process: str) -> str:
        """Kill a process by ID or name."""
        if not process:
            return "Error: Process ID or name is required to kill a process."
        
        try:
            # Check if process is a PID (number)
            if process.isdigit():
                pid = int(process)
                p = psutil.Process(pid)
                process_name = p.name()
                p.terminate()
                return f"Process terminated: {process_name} (PID: {pid})"
            
            # Process is a name
            count = 0
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process.lower():
                    proc.terminate()
                    count += 1
            
            if count > 0:
                return f"Terminated {count} process(es) with name: {process}"
            else:
                return f"No processes found with name: {process}"
        
        except psutil.NoSuchProcess:
            return f"Process with ID {process} not found."
        except psutil.AccessDenied:
            return f"Access denied when trying to terminate process: {process}. May require administrative privileges."
        except Exception as e:
            return f"Error killing process: {str(e)}"
    
    def _get_process_details(self, process: str) -> str:
        """Get detailed information about a specific process."""
        if not process:
            return "Error: Process ID or name is required to get process details."
        
        try:
            proc = None
            
            # Check if process is a PID (number)
            if process.isdigit():
                pid = int(process)
                proc = psutil.Process(pid)
            else:
                # Process is a name, find the first matching process
                for p in psutil.process_iter(['pid', 'name']):
                    if p.info['name'] and p.info['name'].lower() == process.lower():
                        proc = p
                        break
            
            if not proc:
                return f"No process found with ID or name: {process}"
            
            # Get detailed information
            info = {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_percent": proc.memory_percent(),
                "memory_info": proc.memory_info(),
                "create_time": proc.create_time(),
                "username": proc.username(),
                "exe": proc.exe() if hasattr(proc, 'exe') else "N/A",
                "cmdline": proc.cmdline(),
                "connections": proc.connections(),
                "num_threads": proc.num_threads(),
                "nice": proc.nice(),
                "io_counters": proc.io_counters() if hasattr(proc, 'io_counters') else None,
            }
            
            # Format the results
            import datetime
            
            result = f"PROCESS DETAILS: {info['name']} (PID: {info['pid']})\n" + "-" * 80 + "\n"
            result += f"Status: {info['status']}\n"
            result += f"CPU Usage: {info['cpu_percent']:.2f}%\n"
            result += f"Memory Usage: {info['memory_percent']:.2f}% ({_get_file_size_str(info['memory_info'].rss)})\n"
            result += f"Created: {datetime.datetime.fromtimestamp(info['create_time']).strftime('%Y-%m-%d %H:%M:%S')}\n"
            result += f"User: {info['username']}\n"
            result += f"Executable: {info['exe']}\n"
            
            # Command line
            result += f"Command Line: {' '.join(info['cmdline'])}\n"
            
            # Threads
            result += f"Threads: {info['num_threads']}\n"
            
            # Priority
            result += f"Priority (Nice): {info['nice']}\n"
            
            # IO Counters
            if info['io_counters']:
                result += f"IO Counters:\n"
                result += f"  Read Count: {info['io_counters'].read_count}\n"
                result += f"  Write Count: {info['io_counters'].write_count}\n"
                result += f"  Read Bytes: {_get_file_size_str(info['io_counters'].read_bytes)}\n"
                result += f"  Write Bytes: {_get_file_size_str(info['io_counters'].write_bytes)}\n"
            
            # Network Connections
            if info['connections']:
                result += f"Network Connections:\n"
                for i, conn in enumerate(info['connections'][:5]):  # Limit to first 5 connections
                    result += f"  {i+1}. {conn.laddr.ip}:{conn.laddr.port}"
                    if conn.raddr:
                        result += f" -> {conn.raddr.ip}:{conn.raddr.port}"
                    result += f" ({conn.status})\n"
                
                if len(info['connections']) > 5:
                    result += f"  ... and {len(info['connections']) - 5} more connections\n"
            
            return result
        
        except psutil.NoSuchProcess:
            return f"Process with ID {process} not found."
        except psutil.AccessDenied:
            return f"Access denied when trying to get details for process: {process}. May require administrative privileges."
        except Exception as e:
            return f"Error getting process details: {str(e)}"