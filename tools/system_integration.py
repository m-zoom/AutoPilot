"""
System Integration Tools

Tools for integrating with the Windows operating system, including scheduled
tasks, environment variables, system monitoring, and service management.
"""

import sys

import os
import logging
import tempfile
from typing import Optional, Dict, Any
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


logger = logging.getLogger(__name__)

class ScheduleTaskTool(BaseTool):
    """Tool for creating and managing scheduled tasks."""
    
    name: str = "schedule_task"
    description: str = """
    Creates and manages scheduled tasks on Windows.
    
    Input should be a JSON object with the following structure:
    For creating tasks: {"action": "create", "name": "TaskName", "program": "C:\\path\\to\\program.exe", "arguments": "args", "schedule": "daily/weekly/monthly", "time": "HH:MM", "day": "MON/TUE/1-31"}
    For listing tasks: {"action": "list"}
    For deleting tasks: {"action": "delete", "name": "TaskName"}
    
    Returns a success message or the list of scheduled tasks.
    
    Example: {"action": "create", "name": "DailyBackup", "program": "C:\\backup.bat", "schedule": "daily", "time": "22:00"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Create or manage scheduled tasks."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action == "create":
                # Create a new scheduled task
                name = params.get("name", "")
                program = params.get("program", "")
                arguments = params.get("arguments", "")
                schedule = params.get("schedule", "").lower()
                time = params.get("time", "")
                day = params.get("day", "")
                
                if not name:
                    return "Error: Missing task name parameter"
                    
                if not program:
                    return "Error: Missing program parameter"
                    
                if not schedule:
                    return "Error: Missing schedule parameter"
                    
                if not time:
                    return "Error: Missing time parameter"
                
                # Validate schedule
                valid_schedules = ["once", "daily", "weekly", "monthly"]
                if schedule not in valid_schedules:
                    return f"Error: Invalid schedule '{schedule}'. Valid schedules are: {', '.join(valid_schedules)}"
                
                # Build the schtasks command
                cmd = f'schtasks /create /tn "{name}" /tr "\'{program}\' {arguments}" /sc {schedule}'
                
                # Add time
                cmd += f" /st {time}"
                
                # Add day for weekly/monthly schedules
                if schedule == "weekly" and day:
                    cmd += f" /d {day}"
                elif schedule == "monthly" and day:
                    cmd += f" /d {day}"
                
                # Run the command
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error creating scheduled task: {result.stderr}"
                    
                    return f"Successfully created scheduled task '{name}'"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing schtasks command: {str(e)}"
            
            elif action == "list":
                # List scheduled tasks
                try:
                    result = subprocess.run("schtasks /query /fo LIST", shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error listing scheduled tasks: {result.stderr}"
                    
                    return f"Scheduled tasks:\n{result.stdout}"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing schtasks command: {str(e)}"
            
            elif action == "delete":
                # Delete a scheduled task
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing task name parameter"
                
                try:
                    result = subprocess.run(f'schtasks /delete /tn "{name}" /f', shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error deleting scheduled task: {result.stderr}"
                    
                    return f"Successfully deleted scheduled task '{name}'"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing schtasks command: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: create, list, delete"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in scheduled task operation: {str(e)}")
            return f"Error in scheduled task operation: {str(e)}"


class EnvironmentVariableTool(BaseTool):
    """Tool for getting and setting environment variables."""
    
    name: str = "environment_variable"
    description: str = """
    Gets or sets environment variables on Windows.
    
    Input should be a JSON object with the following structure:
    For getting a variable: {"action": "get", "name": "VARIABLE_NAME"}
    For setting a variable: {"action": "set", "name": "VARIABLE_NAME", "value": "value", "scope": "user/system"}
    For listing all variables: {"action": "list"}
    
    Returns the variable value, a success message, or list of all variables.
    
    Example: {"action": "get", "name": "PATH"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get or set environment variables."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action == "get":
                # Get an environment variable
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing variable name parameter"
                
                value = os.environ.get(name)
                
                if value is None:
                    return f"Environment variable '{name}' not found"
                
                return f"{name} = {value}"
            
            elif action == "set":
                # Set an environment variable
                name = params.get("name", "")
                value = params.get("value", "")
                scope = params.get("scope", "user").lower()
                
                if not name:
                    return "Error: Missing variable name parameter"
                
                if scope not in ["user", "system"]:
                    return "Error: Scope must be 'user' or 'system'"
                
                # Set for the current process (temporary)
                os.environ[name] = value
                
                # Set permanently using setx
                try:
                    cmd = ["setx", name, value]
                    
                    if scope == "system":
                        cmd.append("/M")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error setting environment variable: {result.stderr}"
                    
                    return f"Successfully set environment variable {name}={value} for {scope} scope"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing setx command: {str(e)}"
            
            elif action == "list":
                # List all environment variables
                variables = dict(os.environ)
                
                # Sort by name
                sorted_vars = sorted(variables.items())
                
                result = ["Environment Variables:"]
                
                for name, value in sorted_vars:
                    result.append(f"{name} = {value}")
                
                return "\n".join(result)
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: get, set, list"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in environment variable operation: {str(e)}")
            return f"Error in environment variable operation: {str(e)}"


class SystemMonitoringTool(BaseTool):
    """Tool for monitoring CPU, memory, disk usage."""
    
    name: str = "system_monitoring"
    description: str = """
    Monitors CPU, memory, disk usage, and processes on Windows.
    
    Input should be a JSON object with the following structure:
    For system overview: {"action": "overview"}
    For CPU info: {"action": "cpu"}
    For memory info: {"action": "memory"}
    For disk info: {"action": "disk"}
    For process info: {"action": "processes", "count": 10, "sort_by": "memory/cpu"}
    
    Returns information about the specified system resources.
    
    Example: {"action": "overview"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Monitor system resources."""
        try:
            import json
            import psutil
            import platform
            from datetime import datetime
            
            params = json.loads(input_str) if input_str else {}
            
            action = params.get("action", "overview").lower()
            
            if action == "overview":
                # Get system overview
                uname = platform.uname()
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                
                cpu_usage = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count(logical=True)
                
                memory = psutil.virtual_memory()
                memory_total_gb = memory.total / (1024 ** 3)
                memory_used_gb = memory.used / (1024 ** 3)
                memory_percent = memory.percent
                
                disk = psutil.disk_usage('/')
                disk_total_gb = disk.total / (1024 ** 3)
                disk_used_gb = disk.used / (1024 ** 3)
                disk_percent = disk.percent
                
                overview = [
                    "=== System Information ===",
                    f"System: {uname.system} {uname.release}",
                    f"Computer Name: {uname.node}",
                    f"Processor: {uname.processor}",
                    f"Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "=== CPU Information ===",
                    f"Physical Cores: {psutil.cpu_count(logical=False)}",
                    f"Total Cores: {cpu_count}",
                    f"CPU Usage: {cpu_usage}%",
                    "",
                    "=== Memory Information ===",
                    f"Total Memory: {memory_total_gb:.2f} GB",
                    f"Available Memory: {(memory_total_gb - memory_used_gb):.2f} GB",
                    f"Used Memory: {memory_used_gb:.2f} GB ({memory_percent}%)",
                    "",
                    "=== Disk Information ===",
                    f"Total Disk Space: {disk_total_gb:.2f} GB",
                    f"Used Disk Space: {disk_used_gb:.2f} GB ({disk_percent}%)",
                    f"Free Disk Space: {(disk_total_gb - disk_used_gb):.2f} GB"
                ]
                
                return "\n".join(overview)
            
            elif action == "cpu":
                # Get detailed CPU information
                cpu_freq = psutil.cpu_freq()
                cpu_stats = psutil.cpu_stats()
                
                cpu_times_percent = psutil.cpu_times_percent(interval=1)
                
                # Get per-core usage
                per_core = psutil.cpu_percent(interval=1, percpu=True)
                
                cpu_info = [
                    "=== CPU Information ===",
                    f"Physical Cores: {psutil.cpu_count(logical=False)}",
                    f"Total Cores: {psutil.cpu_count(logical=True)}",
                    f"CPU Frequency: Current={cpu_freq.current:.2f} MHz, Min={cpu_freq.min:.2f} MHz, Max={cpu_freq.max:.2f} MHz",
                    f"CPU Usage: {psutil.cpu_percent(interval=1)}%",
                    "",
                    "=== CPU Time Breakdown ===",
                    f"User: {cpu_times_percent.user}%",
                    f"System: {cpu_times_percent.system}%",
                    f"Idle: {cpu_times_percent.idle}%",
                    "",
                    "=== CPU Stats ===",
                    f"Context Switches: {cpu_stats.ctx_switches}",
                    f"Interrupts: {cpu_stats.interrupts}",
                    f"Soft Interrupts: {cpu_stats.soft_interrupts}",
                    f"System Calls: {cpu_stats.syscalls}",
                    "",
                    "=== Per-Core Usage ==="
                ]
                
                for i, usage in enumerate(per_core):
                    cpu_info.append(f"Core {i}: {usage}%")
                
                return "\n".join(cpu_info)
            
            elif action == "memory":
                # Get detailed memory information
                virtual_mem = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                memory_info = [
                    "=== Memory Information ===",
                    f"Total: {virtual_mem.total / (1024 ** 3):.2f} GB",
                    f"Available: {virtual_mem.available / (1024 ** 3):.2f} GB",
                    f"Used: {virtual_mem.used / (1024 ** 3):.2f} GB ({virtual_mem.percent}%)",
                    f"Free: {virtual_mem.free / (1024 ** 3):.2f} GB",
                    "",
                    "=== Swap Information ===",
                    f"Total: {swap.total / (1024 ** 3):.2f} GB",
                    f"Used: {swap.used / (1024 ** 3):.2f} GB ({swap.percent}%)",
                    f"Free: {swap.free / (1024 ** 3):.2f} GB"
                ]
                
                return "\n".join(memory_info)
            
            elif action == "disk":
                # Get disk information
                partitions = psutil.disk_partitions()
                
                disk_info = ["=== Disk Information ==="]
                
                for partition in partitions:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        
                        disk_info.append(f"\nDrive {partition.device} ({partition.mountpoint}):")
                        disk_info.append(f"  File System: {partition.fstype}")
                        disk_info.append(f"  Total Size: {usage.total / (1024 ** 3):.2f} GB")
                        disk_info.append(f"  Used: {usage.used / (1024 ** 3):.2f} GB ({usage.percent}%)")
                        disk_info.append(f"  Free: {usage.free / (1024 ** 3):.2f} GB")
                    except PermissionError:
                        disk_info.append(f"\nDrive {partition.device} ({partition.mountpoint}): Permission denied")
                
                # Add disk IO statistics
                disk_io = psutil.disk_io_counters()
                
                if disk_io:
                    disk_info.append("\n=== Disk I/O Statistics (since boot) ===")
                    disk_info.append(f"Read Count: {disk_io.read_count}")
                    disk_info.append(f"Write Count: {disk_io.write_count}")
                    disk_info.append(f"Read Bytes: {disk_io.read_bytes / (1024 ** 3):.2f} GB")
                    disk_info.append(f"Write Bytes: {disk_io.write_bytes / (1024 ** 3):.2f} GB")
                
                return "\n".join(disk_info)
            
            elif action == "processes":
                # Get process information
                count = params.get("count", 10)
                sort_by = params.get("sort_by", "memory").lower()
                
                try:
                    count = int(count)
                except ValueError:
                    return "Error: Count must be a number"
                
                if sort_by not in ["memory", "cpu"]:
                    return "Error: sort_by must be 'memory' or 'cpu'"
                
                processes = []
                
                for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                    try:
                        # Get process info
                        proc_info = proc.info
                        
                        # Get CPU percent
                        proc_info['cpu_percent'] = proc.cpu_percent(interval=0.1)
                        
                        # Add memory in MB
                        proc_info['memory_mb'] = proc.memory_info().rss / (1024 * 1024)
                        
                        processes.append(proc_info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                # Sort processes
                if sort_by == "memory":
                    processes.sort(key=lambda x: x['memory_percent'], reverse=True)
                else:  # sort_by == "cpu"
                    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
                
                # Limit to requested count
                processes = processes[:count]
                
                # Format output
                process_info = [f"=== Top {count} Processes by {sort_by.upper()} ==="]
                process_info.append("PID   | CPU %  | MEM %  | MEM (MB) | USER           | NAME")
                process_info.append("-" * 70)
                
                for proc in processes:
                    process_info.append(
                        f"{proc['pid']:<6} | "
                        f"{proc['cpu_percent']:6.1f} | "
                        f"{proc['memory_percent']:6.1f} | "
                        f"{proc['memory_mb']:9.1f} | "
                        f"{(proc['username'] or 'N/A')[:15]:<15} | "
                        f"{proc['name']}"
                    )
                
                return "\n".join(process_info)
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: overview, cpu, memory, disk, processes"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in system monitoring: {str(e)}")
            return f"Error in system monitoring: {str(e)}"


class ServiceManagementTool(BaseTool):
    """Tool for managing Windows services."""
    
    name: str = "service_management"
    description: str = """
    Starts, stops, and manages Windows services.
    
    Input should be a JSON object with the following structure:
    For listing services: {"action": "list", "status": "running/stopped/all"}
    For getting service info: {"action": "info", "name": "service_name"}
    For starting a service: {"action": "start", "name": "service_name"}
    For stopping a service: {"action": "stop", "name": "service_name"}
    For restarting a service: {"action": "restart", "name": "service_name"}
    
    Returns the service information or a status message.
    
    Example: {"action": "info", "name": "wuauserv"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage Windows services."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action == "list":
                # List services
                status = params.get("status", "all").lower()
                
                if status not in ["running", "stopped", "all"]:
                    return "Error: Status must be 'running', 'stopped', or 'all'"
                
                # Build the command
                if status == "all":
                    cmd = "sc query type= service"
                else:
                    cmd = f"sc query type= service state= {status}"
                
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error listing services: {result.stderr}"
                    
                    # Process the output to make it more readable
                    output = result.stdout
                    services = []
                    
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith("SERVICE_NAME:"):
                            service_name = line.split(":", 1)[1].strip()
                            services.append(service_name)
                    
                    status_text = status if status != "all" else "all"
                    
                    return f"Found {len(services)} {status_text} services:\n" + "\n".join(services)
                
                except subprocess.SubprocessError as e:
                    return f"Error executing sc command: {str(e)}"
            
            elif action == "info":
                # Get service info
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing service name parameter"
                
                try:
                    result = subprocess.run(f"sc qc {name} && sc query {name}", shell=True, capture_output=True, text=True)
                    
                    if "The specified service does not exist" in result.stdout:
                        return f"Error: Service '{name}' does not exist"
                    
                    if result.returncode != 0:
                        return f"Error getting service info: {result.stderr}"
                    
                    return f"Service information for '{name}':\n{result.stdout}"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing sc command: {str(e)}"
            
            elif action == "start":
                # Start a service
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing service name parameter"
                
                try:
                    result = subprocess.run(f"sc start {name}", shell=True, capture_output=True, text=True)
                    
                    if "The specified service does not exist" in result.stdout:
                        return f"Error: Service '{name}' does not exist"
                    
                    if "1056" in result.stdout:  # Already running
                        return f"Service '{name}' is already running"
                    
                    if "1053" in result.stdout:  # Service not responding
                        return f"Service '{name}' did not respond to the start request"
                    
                    if result.returncode != 0:
                        return f"Error starting service: {result.stdout}"
                    
                    return f"Service '{name}' started successfully"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing sc command: {str(e)}"
            
            elif action == "stop":
                # Stop a service
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing service name parameter"
                
                try:
                    result = subprocess.run(f"sc stop {name}", shell=True, capture_output=True, text=True)
                    
                    if "The specified service does not exist" in result.stdout:
                        return f"Error: Service '{name}' does not exist"
                    
                    if "1062" in result.stdout:  # Already stopped
                        return f"Service '{name}' is not running"
                    
                    if result.returncode != 0:
                        return f"Error stopping service: {result.stdout}"
                    
                    return f"Service '{name}' stopped successfully"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing sc command: {str(e)}"
            
            elif action == "restart":
                # Restart a service
                name = params.get("name", "")
                
                if not name:
                    return "Error: Missing service name parameter"
                
                try:
                    # Stop the service first
                    stop_result = subprocess.run(f"sc stop {name}", shell=True, capture_output=True, text=True)
                    
                    if "The specified service does not exist" in stop_result.stdout:
                        return f"Error: Service '{name}' does not exist"
                    
                    # Wait a moment for the service to stop
                    import time
                    time.sleep(2)
                    
                    # Start the service
                    start_result = subprocess.run(f"sc start {name}", shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error restarting service: {start_result.stdout}"
                    
                    return f"Service '{name}' restarted successfully"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing sc command: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: list, info, start, stop, restart"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in service management: {str(e)}")
            return f"Error in service management: {str(e)}"
