"""
Notifications & Alerts Tools

Tools for sending desktop notifications, scheduling alerts,
and listening for system events.
"""

import sys

import os
import logging
import tempfile
import time
from datetime import datetime, timedelta
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

class NotificationTool(BaseTool):
    """Tool for sending desktop notifications."""
    
    name: str = "notification"
    description: str = """
    Sends desktop notifications to the Windows notification center.
    
    Input should be a JSON object with the following structure:
    {"title": "Notification Title", "message": "Notification message text", "icon": "path/to/icon.ico", "duration": 5}
    
    Title and message are required.
    Icon path is optional.
    Duration is in seconds and defaults to 5 seconds.
    
    Returns a success message or error.
    
    Example: {"title": "Task Complete", "message": "Your file download has finished"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Send a desktop notification."""
        try:
            import json
            from win10toast import ToastNotifier
            
            params = json.loads(input_str)
            
            title = params.get("title", "")
            message = params.get("message", "")
            icon_path = params.get("icon", None)
            duration = params.get("duration", 5)
            
            if not title:
                return "Error: Missing notification title"
                
            if not message:
                return "Error: Missing notification message"
            
            # Validate duration
            try:
                duration = int(duration)
                if duration < 1:
                    duration = 5
            except ValueError:
                duration = 5
            
            # Create toaster
            toaster = ToastNotifier()
            
            # Show notification
            toaster.show_toast(
                title=title,
                msg=message,
                icon_path=icon_path,
                duration=duration,
                threaded=True
            )
            
            return f"Notification '{title}' sent successfully"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError:
            return "Error: win10toast module is not installed. Install it with 'pip install win10toast'"
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return f"Error sending notification: {str(e)}"


class AlertSchedulerTool(BaseTool):
    """Tool for setting reminders and alerts."""
    
    name: str = "alert_scheduler"
    description: str = """
    Sets reminders and alerts to be displayed at a specific time.
    
    Input should be a JSON object with the following structure:
    {"message": "Alert message", "time": "HH:MM", "date": "YYYY-MM-DD", "repeat": "daily/weekly/monthly/none"}
    
    Message and time are required.
    Date defaults to today if not specified.
    Repeat can be "daily", "weekly", "monthly", or "none" (default).
    
    Returns a confirmation message or error.
    
    Example: {"message": "Team meeting", "time": "14:30", "repeat": "weekly"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Schedule a reminder or alert."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            message = params.get("message", "")
            time_str = params.get("time", "")
            date_str = params.get("date", "")
            repeat = params.get("repeat", "none").lower()
            
            if not message:
                return "Error: Missing alert message"
                
            if not time_str:
                return "Error: Missing alert time"
            
            # Validate time format (HH:MM)
            try:
                hours, minutes = map(int, time_str.split(':'))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    return "Error: Invalid time format. Use HH:MM (24-hour format)"
            except ValueError:
                return "Error: Invalid time format. Use HH:MM (24-hour format)"
            
            # Process date (default to today if not specified)
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return "Error: Invalid date format. Use YYYY-MM-DD"
            else:
                target_date = datetime.now().date()
            
            # Validate repeat option
            valid_repeat_options = ["none", "daily", "weekly", "monthly"]
            if repeat not in valid_repeat_options:
                return f"Error: Invalid repeat option. Valid options are: {', '.join(valid_repeat_options)}"
            
            # Creating a scheduled task is the most reliable way on Windows
            # Generate a unique task name
            task_name = f"Alert_{target_date.strftime('%Y%m%d')}_{time_str.replace(':', '')}_{hash(message) % 10000}"
            
            # Build the time string for the scheduled task
            time_parts = time_str.split(':')
            task_time = f"{time_parts[0]}:{time_parts[1]}"
            
            # Determine the schedule type
            if repeat == "none":
                schedule_type = "once"
                # If date is in the past, return an error
                if target_date < datetime.now().date() or (target_date == datetime.now().date() and 
                                                          datetime.strptime(time_str, "%H:%M").time() < datetime.now().time()):
                    return "Error: Cannot schedule alerts in the past"
            else:
                schedule_type = repeat
            
            # Build the command to display the alert
            # Using PowerShell to show a notification
            alert_script = f"""
            $title = 'Reminder'
            $message = '{message}'
            
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = $title
            $notification.BalloonTipText = $message
            $notification.Visible = $true
            $notification.ShowBalloonTip(10000)
            
            Start-Sleep -Seconds 10
            $notification.Dispose()
            """
            
            # Create a temporary PowerShell script file
            with tempfile.NamedTemporaryFile(suffix='.ps1', delete=False) as script_file:
                script_file.write(alert_script.encode('utf-8'))
                script_path = script_file.name
            
            # Build the schtasks command
            cmd = f'schtasks /create /tn "{task_name}" /tr "powershell -ExecutionPolicy Bypass -File {script_path}" /sc {schedule_type} /st {task_time}'
            
            # Add date for one-time tasks
            if schedule_type == "once":
                cmd += f" /sd {target_date.strftime('%m/%d/%Y')}"
            
            # Add day for weekly tasks
            if schedule_type == "weekly":
                # Get the day of week for the target date
                day_of_week = target_date.strftime("%a").upper()
                cmd += f" /d {day_of_week}"
            
            # Add day for monthly tasks
            if schedule_type == "monthly":
                # Get the day of month for the target date
                day_of_month = target_date.day
                cmd += f" /d {day_of_month}"
            
            # Add /f to force creation without prompting
            cmd += " /f"
            
            # Execute the command
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Error creating alert: {result.stderr or result.stdout}"
                
                if repeat == "none":
                    schedule_desc = f"at {time_str} on {target_date.strftime('%Y-%m-%d')}"
                else:
                    schedule_desc = f"{repeat} at {time_str}"
                
                return f"Alert '{message}' scheduled {schedule_desc}"
            
            except subprocess.SubprocessError as e:
                return f"Error scheduling alert: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error scheduling alert: {str(e)}")
            return f"Error scheduling alert: {str(e)}"


class EventListenerTool(BaseTool):
    """Tool for listening for system events."""
    
    name: str = "event_listener"
    description: str = """
    Listens for system events like file changes, USB connections, etc.
    
    Input should be a JSON object with the following structure:
    {"event_type": "file_change/usb/process/log", "target": "path_or_info", "duration": 60, "callback": {"action": "notification", "message": "Event detected"}}
    
    Event_type and target are required.
    Duration is in seconds (default: 60, max: 300).
    Callback defines what happens when the event is detected.
    
    Returns the events detected or an error.
    
    Example: {"event_type": "file_change", "target": "C:\\Users\\Documents", "duration": 30, "callback": {"action": "notification", "message": "File changed: {file}"}}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Listen for system events."""
        try:
            import json
            
            params = json.loads(input_str)
            
            event_type = params.get("event_type", "").lower()
            target = params.get("target", "")
            duration = params.get("duration", 60)
            callback = params.get("callback", {})
            
            if not event_type:
                return "Error: Missing event_type parameter"
                
            if not target:
                return "Error: Missing target parameter"
            
            # Validate duration (max 5 minutes)
            try:
                duration = int(duration)
                if duration < 1:
                    duration = 60
                if duration > 300:
                    duration = 300
            except ValueError:
                duration = 60
            
            # Handle different event types
            if event_type == "file_change":
                return self._listen_for_file_changes(target, duration, callback)
            elif event_type == "usb":
                return self._listen_for_usb_events(duration, callback)
            elif event_type == "process":
                return self._listen_for_process_events(target, duration, callback)
            elif event_type == "log":
                return self._listen_for_log_events(target, duration, callback)
            else:
                return f"Error: Unsupported event type '{event_type}'. Supported types are: file_change, usb, process, log"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in event listener: {str(e)}")
            return f"Error in event listener: {str(e)}"
    
    def _listen_for_file_changes(self, path: str, duration: int, callback: Dict[str, Any]) -> str:
        """Listen for file changes in a directory."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            if not os.path.exists(path):
                return f"Error: Path does not exist: {path}"
            
            # Initialize event tracking
            events_detected = []
            
            # Create event handler
            class FileChangeHandler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory:
                        event_info = f"File created: {event.src_path}"
                        events_detected.append(event_info)
                        self._handle_callback(event_info, event.src_path)
                
                def on_deleted(self, event):
                    if not event.is_directory:
                        event_info = f"File deleted: {event.src_path}"
                        events_detected.append(event_info)
                        self._handle_callback(event_info, event.src_path)
                
                def on_modified(self, event):
                    if not event.is_directory:
                        event_info = f"File modified: {event.src_path}"
                        events_detected.append(event_info)
                        self._handle_callback(event_info, event.src_path)
                
                def on_moved(self, event):
                    if not event.is_directory:
                        event_info = f"File moved: {event.src_path} -> {event.dest_path}"
                        events_detected.append(event_info)
                        self._handle_callback(event_info, event.dest_path)
                
                def _handle_callback(self, event_info, file_path):
                    if callback:
                        action = callback.get("action", "").lower()
                        
                        if action == "notification":
                            try:
                                from win10toast import ToastNotifier
                                
                                message = callback.get("message", "File change detected")
                                # Replace {file} placeholder with actual file
                                message = message.replace("{file}", os.path.basename(file_path))
                                
                                toaster = ToastNotifier()
                                toaster.show_toast(
                                    title="File Change Detected",
                                    msg=message,
                                    duration=5,
                                    threaded=True
                                )
                            except ImportError:
                                logger.error("win10toast module not installed")
            
            # Set up observer
            event_handler = FileChangeHandler()
            observer = Observer()
            observer.schedule(event_handler, path, recursive=True)
            observer.start()
            
            try:
                # Monitor for the specified duration
                start_time = time.time()
                while time.time() - start_time < duration:
                    time.sleep(1)
            finally:
                observer.stop()
                observer.join()
            
            # Report results
            if events_detected:
                return f"Detected {len(events_detected)} file changes in {path} during {duration} seconds:\n" + "\n".join(events_detected)
            else:
                return f"No file changes detected in {path} during {duration} seconds"
            
        except ImportError:
            return "Error: watchdog module not installed. Install it with 'pip install watchdog'"
        except Exception as e:
            return f"Error monitoring file changes: {str(e)}"
    
    def _listen_for_usb_events(self, duration: int, callback: Dict[str, Any]) -> str:
        """Listen for USB device connection events."""
        try:
            import win32com.client
            
            # Initialize WMI
            wmi = win32com.client.GetObject("winmgmts:")
            
            # Initial state - get list of USB devices
            initial_devices = {}
            for device in wmi.InstancesOf("Win32_USBHub"):
                initial_devices[device.DeviceID] = device.Description
            
            # Monitor for USB events
            events_detected = []
            
            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(1)
                
                current_devices = {}
                for device in wmi.InstancesOf("Win32_USBHub"):
                    current_devices[device.DeviceID] = device.Description
                
                # Check for new devices
                for device_id, description in current_devices.items():
                    if device_id not in initial_devices:
                        event_info = f"USB device connected: {description} ({device_id})"
                        events_detected.append(event_info)
                        
                        # Handle callback
                        if callback:
                            action = callback.get("action", "").lower()
                            
                            if action == "notification":
                                try:
                                    from win10toast import ToastNotifier
                                    
                                    message = callback.get("message", "USB device connected")
                                    # Replace {device} placeholder with actual device name
                                    message = message.replace("{device}", description)
                                    
                                    toaster = ToastNotifier()
                                    toaster.show_toast(
                                        title="USB Device Connected",
                                        msg=message,
                                        duration=5,
                                        threaded=True
                                    )
                                except ImportError:
                                    logger.error("win10toast module not installed")
                
                # Check for removed devices
                for device_id, description in initial_devices.items():
                    if device_id not in current_devices:
                        event_info = f"USB device disconnected: {description} ({device_id})"
                        events_detected.append(event_info)
                        
                        # Handle callback
                        if callback:
                            action = callback.get("action", "").lower()
                            
                            if action == "notification":
                                try:
                                    from win10toast import ToastNotifier
                                    
                                    message = callback.get("message", "USB device disconnected")
                                    # Replace {device} placeholder with actual device name
                                    message = message.replace("{device}", description)
                                    
                                    toaster = ToastNotifier()
                                    toaster.show_toast(
                                        title="USB Device Disconnected",
                                        msg=message,
                                        duration=5,
                                        threaded=True
                                    )
                                except ImportError:
                                    logger.error("win10toast module not installed")
                
                # Update the initial state for the next check
                initial_devices = current_devices
            
            # Report results
            if events_detected:
                return f"Detected {len(events_detected)} USB events during {duration} seconds:\n" + "\n".join(events_detected)
            else:
                return f"No USB events detected during {duration} seconds"
            
        except ImportError:
            return "Error: pywin32 module not installed. Install it with 'pip install pywin32'"
        except Exception as e:
            return f"Error monitoring USB events: {str(e)}"
    
    def _listen_for_process_events(self, process_name: str, duration: int, callback: Dict[str, Any]) -> str:
        """Listen for process start/stop events."""
        try:
            import psutil
            
            # Initial state - check if process is running
            initial_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if process_name.lower() in proc.info['name'].lower():
                    initial_running = True
                    break
            
            # Monitor for process events
            events_detected = []
            
            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(1)
                
                current_running = False
                for proc in psutil.process_iter(['pid', 'name']):
                    if process_name.lower() in proc.info['name'].lower():
                        current_running = True
                        if not initial_running:
                            event_info = f"Process started: {proc.info['name']} (PID: {proc.info['pid']})"
                            events_detected.append(event_info)
                            
                            # Handle callback
                            if callback:
                                action = callback.get("action", "").lower()
                                
                                if action == "notification":
                                    try:
                                        from win10toast import ToastNotifier
                                        
                                        message = callback.get("message", "Process started")
                                        # Replace {process} placeholder with actual process name
                                        message = message.replace("{process}", proc.info['name'])
                                        
                                        toaster = ToastNotifier()
                                        toaster.show_toast(
                                            title="Process Started",
                                            msg=message,
                                            duration=5,
                                            threaded=True
                                        )
                                    except ImportError:
                                        logger.error("win10toast module not installed")
                        break
                
                if initial_running and not current_running:
                    event_info = f"Process stopped: {process_name}"
                    events_detected.append(event_info)
                    
                    # Handle callback
                    if callback:
                        action = callback.get("action", "").lower()
                        
                        if action == "notification":
                            try:
                                from win10toast import ToastNotifier
                                
                                message = callback.get("message", "Process stopped")
                                # Replace {process} placeholder with actual process name
                                message = message.replace("{process}", process_name)
                                
                                toaster = ToastNotifier()
                                toaster.show_toast(
                                    title="Process Stopped",
                                    msg=message,
                                    duration=5,
                                    threaded=True
                                )
                            except ImportError:
                                logger.error("win10toast module not installed")
                
                # Update the initial state for the next check
                initial_running = current_running
            
            # Report results
            if events_detected:
                return f"Detected {len(events_detected)} process events for {process_name} during {duration} seconds:\n" + "\n".join(events_detected)
            else:
                return f"No process events detected for {process_name} during {duration} seconds"
            
        except ImportError:
            return "Error: psutil module not installed. Install it with 'pip install psutil'"
        except Exception as e:
            return f"Error monitoring process events: {str(e)}"
    
    def _listen_for_log_events(self, log_name: str, duration: int, callback: Dict[str, Any]) -> str:
        """Listen for Windows Event Log events."""
        try:
            import win32evtlog
            import win32con
            
            # Validate log name
            valid_logs = ["System", "Application", "Security"]
            if log_name not in valid_logs:
                return f"Error: Invalid log name '{log_name}'. Valid log names are: {', '.join(valid_logs)}"
            
            # Get initial position in the log
            hand = win32evtlog.OpenEventLog(None, log_name)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            total_records = win32evtlog.GetNumberOfEventLogRecords(hand)
            win32evtlog.CloseEventLog(hand)
            
            # Monitor for new events
            events_detected = []
            
            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(2)  # Check less frequently to reduce system load
                
                hand = win32evtlog.OpenEventLog(None, log_name)
                new_total = win32evtlog.GetNumberOfEventLogRecords(hand)
                
                if new_total > total_records:
                    # New events have been added
                    events_to_read = new_total - total_records
                    
                    events = win32evtlog.ReadEventLog(
                        hand, flags, 0, events_to_read
                    )
                    
                    for event in events:
                        event_time = event.TimeGenerated.Format()
                        event_id = event.EventID
                        event_type = {
                            win32con.EVENTLOG_ERROR_TYPE: "Error",
                            win32con.EVENTLOG_WARNING_TYPE: "Warning",
                            win32con.EVENTLOG_INFORMATION_TYPE: "Information",
                            win32con.EVENTLOG_AUDIT_SUCCESS: "Audit Success",
                            win32con.EVENTLOG_AUDIT_FAILURE: "Audit Failure"
                        }.get(event.EventType, "Unknown")
                        
                        event_info = f"{event_time} - {event_type} (ID: {event_id}): {event.SourceName}"
                        events_detected.append(event_info)
                        
                        # Handle callback
                        if callback:
                            action = callback.get("action", "").lower()
                            
                            if action == "notification" and event_type in ["Error", "Warning"]:
                                try:
                                    from win10toast import ToastNotifier
                                    
                                    message = callback.get("message", "New event log entry")
                                    # Replace placeholders with actual values
                                    message = message.replace("{type}", event_type)
                                    message = message.replace("{source}", event.SourceName)
                                    
                                    toaster = ToastNotifier()
                                    toaster.show_toast(
                                        title=f"{log_name} Log: {event_type}",
                                        msg=message,
                                        duration=5,
                                        threaded=True
                                    )
                                except ImportError:
                                    logger.error("win10toast module not installed")
                
                total_records = new_total
                win32evtlog.CloseEventLog(hand)
            
            # Report results
            if events_detected:
                return f"Detected {len(events_detected)} new events in {log_name} log during {duration} seconds:\n" + "\n".join(events_detected)
            else:
                return f"No new events detected in {log_name} log during {duration} seconds"
            
        except ImportError:
            return "Error: pywin32 module not installed. Install it with 'pip install pywin32'"
        except Exception as e:
            return f"Error monitoring log events: {str(e)}"
