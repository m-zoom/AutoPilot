"""
Device Control Tools

Tools for managing device connections, including Bluetooth devices,
printers, and display settings.
"""

import sys

import os
import logging
import tempfile
from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

# Windows API fallback for when running on non-Windows platforms
if not sys.platform.startswith('win'):
    class WinAPIFallback:
        @staticmethod
        def GetShortPathName(path):
            return path
        @staticmethod
        def GetLongPathName(path):
            return path
    
    sys.modules['win32api'] = WinAPIFallback()


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

class BluetoothManagementTool(BaseTool):
    """Tool for managing Bluetooth connections."""
    
    name: str = "bluetooth_management"
    description: str = """
    Manages Bluetooth connections, devices, and settings.
    
    Input should be a JSON object with the following structure:
    For listing devices: {"action": "list"}
    For pairing a device: {"action": "pair", "device_id": "device_id/name"}
    For connecting to a device: {"action": "connect", "device_id": "device_id/name"}
    For disconnecting from a device: {"action": "disconnect", "device_id": "device_id/name"}
    For removing a paired device: {"action": "remove", "device_id": "device_id/name"}
    
    Returns a list of devices or a success/error message.
    
    Example: {"action": "list"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage Bluetooth connections."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            # Check Bluetooth availability - use PowerShell
            bt_check_cmd = 'powershell -Command "Get-PnpDevice -Class Bluetooth | Select-Object Status, Name"'
            bt_check = subprocess.run(bt_check_cmd, shell=True, capture_output=True, text=True)
            
            if "No matching" in bt_check.stdout or bt_check.returncode != 0:
                return "Error: Bluetooth adapter not found or not enabled"
            
            if action == "list":
                # List paired Bluetooth devices using PowerShell
                ps_cmd = 'powershell -Command "Get-PnpDevice -Class Bluetooth | Where-Object { $_.Name -notlike \'*adapter*\' -and $_.Name -notlike \'*radio*\' } | Select-Object Status, Name, DeviceID | Format-Table -AutoSize | Out-String -Width 4096"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Error listing Bluetooth devices: {result.stderr}"
                
                if not result.stdout.strip():
                    return "No Bluetooth devices found"
                
                return f"Bluetooth devices:\n{result.stdout}"
                
            elif action == "pair":
                device_id = params.get("device_id", "")
                
                if not device_id:
                    return "Error: Missing device_id parameter"
                
                # Start Bluetooth pairing wizard for the device
                ps_cmd = 'powershell -Command "Add-Type -AssemblyName System.Runtime.WindowsRuntime; ' \
                         '[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime]; ' \
                         '$btSelector = [Windows.Devices.Bluetooth.BluetoothDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]; ' \
                         'Write-Output \'Searching for Bluetooth devices...\'; ' \
                         '$aqs = $btSelector::GetDeviceSelectorFromPairingState($true); ' \
                         '$devices = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($aqs).GetResults(); ' \
                         'foreach($device in $devices) { if($device.Name -like \'*' + device_id + '*\' -or $device.Id -like \'*' + device_id + '*\') ' \
                         '{ Write-Output (\'Attempting to pair with: \' + $device.Name); ' \
                         '[Windows.Devices.Bluetooth.BluetoothDevice]::FromIdAsync($device.Id).AsTask().GetAwaiter().GetResult().DeviceInformation.Pairing.PairAsync().AsTask().GetAwaiter().GetResult(); ' \
                         'Write-Output \'Pairing attempted.\'; break; } else { Write-Output (\'No matching device: \' + $device.Name + \' (\' + $device.Id + \')\'); } }"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "No matching device" in result.stdout:
                    return f"Error: Could not find Bluetooth device with ID or name containing '{device_id}'"
                
                if "Pairing attempted" in result.stdout:
                    return f"Pairing with device '{device_id}' was attempted. Check device for confirmation prompts."
                
                return f"Result of pairing attempt:\n{result.stdout}"
                
            elif action == "connect":
                device_id = params.get("device_id", "")
                
                if not device_id:
                    return "Error: Missing device_id parameter"
                
                # Connect to a paired device
                ps_cmd = 'powershell -Command "$device = Get-PnpDevice | Where-Object { ($_.Name -like \'*' + device_id + '*\' -or $_.DeviceID -like \'*' + device_id + '*\') -and $_.Class -eq \'Bluetooth\' }; if($device) { Write-Output (\'Connecting to: \' + $device.Name); $device | Enable-PnpDevice -Confirm:$false; Write-Output \'Connection attempted.\' } else { Write-Output \'Device not found.\' }"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Device not found" in result.stdout:
                    return f"Error: Could not find Bluetooth device with ID or name containing '{device_id}'"
                
                if "Connection attempted" in result.stdout:
                    return f"Connection to device '{device_id}' was attempted. Check device status."
                
                return f"Result of connection attempt:\n{result.stdout}"
                
            elif action == "disconnect":
                device_id = params.get("device_id", "")
                
                if not device_id:
                    return "Error: Missing device_id parameter"
                
                # Disconnect from a connected device
                ps_cmd = 'powershell -Command "$device = Get-PnpDevice | Where-Object { ($_.Name -like \'*' + device_id + '*\' -or $_.DeviceID -like \'*' + device_id + '*\') -and $_.Class -eq \'Bluetooth\' }; if($device) { Write-Output (\'Disconnecting from: \' + $device.Name); $device | Disable-PnpDevice -Confirm:$false; Write-Output \'Disconnection attempted.\' } else { Write-Output \'Device not found.\' }"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Device not found" in result.stdout:
                    return f"Error: Could not find Bluetooth device with ID or name containing '{device_id}'"
                
                if "Disconnection attempted" in result.stdout:
                    return f"Disconnection from device '{device_id}' was attempted. Check device status."
                
                return f"Result of disconnection attempt:\n{result.stdout}"
                
            elif action == "remove":
                device_id = params.get("device_id", "")
                
                if not device_id:
                    return "Error: Missing device_id parameter"
                
                # Remove a paired device
                ps_cmd = 'powershell -Command "$device = Get-PnpDevice | Where-Object { ($_.Name -like \'*' + device_id + '*\' -or $_.DeviceID -like \'*' + device_id + '*\') -and $_.Class -eq \'Bluetooth\' }; if($device) { Write-Output (\'Removing device: \' + $device.Name); $device | Remove-PnpDevice -Confirm:$false; Write-Output \'Device removal attempted.\' } else { Write-Output \'Device not found.\' }"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Device not found" in result.stdout:
                    return f"Error: Could not find Bluetooth device with ID or name containing '{device_id}'"
                
                if "Device removal attempted" in result.stdout:
                    return f"Removal of device '{device_id}' was attempted. Check device status."
                
                return f"Result of device removal attempt:\n{result.stdout}"
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: list, pair, connect, disconnect, remove"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in Bluetooth management: {str(e)}")
            return f"Error in Bluetooth management: {str(e)}"


class PrinterTool(BaseTool):
    """Tool for sending documents to printer."""
    
    name: str = "printer"
    description: str = """
    Manages printers and print jobs on Windows.
    
    Input should be a JSON object with the following structure:
    For listing printers: {"action": "list"}
    For printing a file: {"action": "print", "file_path": "path/to/file", "printer_name": "printer_name", "options": {"copies": 1}}
    For showing print queue: {"action": "queue", "printer_name": "printer_name"}
    For setting a default printer: {"action": "set_default", "printer_name": "printer_name"}
    
    Returns a list of printers, print job status, or a success/error message.
    
    Example: {"action": "list"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage printers and print jobs."""
        try:
            import json
            import subprocess
            import win32print
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action == "list":
                # List installed printers
                printers = []
                
                try:
                    # Get a list of installed printers
                    for flags, _, printer_name, _ in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                        # Check if this is the default printer
                        is_default = (printer_name == win32print.GetDefaultPrinter())
                        
                        # Get printer info
                        try:
                            printer_handle = win32print.OpenPrinter(printer_name)
                            printer_info = win32print.GetPrinter(printer_handle, 2)
                            status = printer_info['Status']
                            status_str = "Ready" if status == 0 else f"Status code: {status}"
                            win32print.ClosePrinter(printer_handle)
                        except Exception:
                            status_str = "Unknown"
                        
                        printers.append({
                            "name": printer_name,
                            "default": is_default,
                            "status": status_str
                        })
                except Exception as e:
                    return f"Error retrieving printers: {str(e)}"
                
                if not printers:
                    return "No printers found on this system"
                
                # Format the output
                printer_list = ["Installed Printers:"]
                
                for printer in printers:
                    default_str = " (Default)" if printer["default"] else ""
                    printer_list.append(f"- {printer['name']}{default_str} - {printer['status']}")
                
                return "\n".join(printer_list)
                
            elif action == "print":
                file_path = params.get("file_path", "")
                printer_name = params.get("printer_name", "")
                options = params.get("options", {})
                
                if not file_path:
                    return "Error: Missing file_path parameter"
                
                if not os.path.exists(file_path):
                    return f"Error: File not found: {file_path}"
                
                # If printer_name is not specified, use the default printer
                if not printer_name:
                    printer_name = win32print.GetDefaultPrinter()
                    if not printer_name:
                        return "Error: No default printer found"
                
                # Check if the specified printer exists
                printer_exists = False
                for _, _, name, _ in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                    if name.lower() == printer_name.lower():
                        printer_name = name  # Use the exact name with correct case
                        printer_exists = True
                        break
                
                if not printer_exists:
                    return f"Error: Printer '{printer_name}' not found"
                
                # Get file extension to determine print method
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                
                # Different file types may need different printing methods
                if ext in ['.txt', '.log', '.py', '.js', '.html', '.css', '.json']:
                    # Text files using Notepad print
                    cmd = f'notepad /p "{file_path}"'
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error printing file: {result.stderr}"
                    
                    return f"File {file_path} sent to printer {printer_name}"
                
                elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                    # Use ShellExecute for documents
                    try:
                        import win32api
                        import win32con
                        
                        # Set the default printer first
                        original_printer = win32print.GetDefaultPrinter()
                        win32print.SetDefaultPrinter(printer_name)
                        
                        # Print with ShellExecute
                        win32api.ShellExecute(
                            0,
                            "print",
                            file_path,
                            None,
                            ".",
                            win32con.SW_HIDE
                        )
                        
                        # Restore original default printer
                        win32print.SetDefaultPrinter(original_printer)
                        
                        return f"File {file_path} sent to printer {printer_name}"
                    
                    except Exception as e:
                        return f"Error printing document: {str(e)}"
                
                else:
                    # For other file types, try generic Windows print
                    cmd = f'powershell -Command "Start-Process -FilePath \'{file_path}\' -Verb Print -PassThru | %{{Start-Sleep -Seconds 2; $_ | Stop-Process}}"'
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return f"Error printing file: {result.stderr}"
                    
                    return f"File {file_path} sent to printer {printer_name}"
                
            elif action == "queue":
                printer_name = params.get("printer_name", "")
                
                # If printer_name is not specified, use the default printer
                if not printer_name:
                    printer_name = win32print.GetDefaultPrinter()
                    if not printer_name:
                        return "Error: No default printer found"
                
                # Get print queue for the specified printer
                ps_cmd = f'powershell -Command "Get-PrintJob -PrinterName \'{printer_name}\' | Format-Table ID, JobName, JobStatus, Pages, TotalPages -AutoSize | Out-String -Width 4096"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Cannot find any printer" in result.stdout or "Cannot find any printer" in result.stderr:
                    return f"Error: Printer '{printer_name}' not found"
                
                if not result.stdout.strip():
                    return f"No active print jobs for printer '{printer_name}'"
                
                return f"Print queue for printer '{printer_name}':\n{result.stdout}"
                
            elif action == "set_default":
                printer_name = params.get("printer_name", "")
                
                if not printer_name:
                    return "Error: Missing printer_name parameter"
                
                # Check if the specified printer exists
                printer_exists = False
                for _, _, name, _ in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                    if name.lower() == printer_name.lower():
                        printer_name = name  # Use the exact name with correct case
                        printer_exists = True
                        break
                
                if not printer_exists:
                    return f"Error: Printer '{printer_name}' not found"
                
                # Set the default printer
                try:
                    win32print.SetDefaultPrinter(printer_name)
                    return f"Successfully set '{printer_name}' as the default printer"
                except Exception as e:
                    return f"Error setting default printer: {str(e)}"
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: list, print, queue, set_default"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in printer operation: {str(e)}")
            return f"Error in printer operation: {str(e)}"


class DisplayManagementTool(BaseTool):
    """Tool for controlling display settings."""
    
    name: str = "display_management"
    description: str = """
    Controls display settings like resolution, brightness, and orientation.
    
    Input should be a JSON object with the following structure:
    For getting display info: {"action": "info"}
    For setting resolution: {"action": "set_resolution", "display": 0, "width": 1920, "height": 1080}
    For setting brightness: {"action": "set_brightness", "level": 75}
    For changing orientation: {"action": "set_orientation", "display": 0, "orientation": "landscape/portrait/flipped_landscape/flipped_portrait"}
    
    Display is the monitor index (0 = primary monitor).
    Level is the brightness percentage (0-100).
    
    Returns display information or a success/error message.
    
    Example: {"action": "info"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Control display settings."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action == "info":
                # Get display information using PowerShell
                ps_cmd = 'powershell -Command "$displays = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBasicDisplayParams; $resolutions = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorListedSupportedSourceModes; foreach ($i in 0..($displays.Count-1)) { $currentDisplay = $displays[$i]; Write-Output (\'Display \' + $i); Write-Output (\'  Active: \' + $currentDisplay.Active); Write-Output (\'  Display Dimensions: \' + $currentDisplay.MaxHorizontalImageSize + \'cm x \' + $currentDisplay.MaxVerticalImageSize + \'cm\'); $currentRes = $resolutions[$i]; $maxRes = $currentRes.MonitorSourceModes | Sort-Object -Property { $_.HorizontalActivePixels * $_.VerticalActivePixels } -Descending | Select-Object -First 1; Write-Output (\'  Max Resolution: \' + $maxRes.HorizontalActivePixels + \'x\' + $maxRes.VerticalActivePixels); Write-Output \'\'; }"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Error getting display information: {result.stderr}"
                
                if not result.stdout.strip():
                    return "Could not retrieve display information"
                
                # Get current display settings
                current_settings_cmd = 'powershell -Command "Get-WmiObject -Class Win32_VideoController | Select-Object -Property Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, AdapterCompatibility | Format-List | Out-String -Width 4096"'
                
                current_result = subprocess.run(current_settings_cmd, shell=True, capture_output=True, text=True)
                
                if current_result.returncode == 0 and current_result.stdout.strip():
                    display_info = result.stdout + "\nCurrent Video Controllers:\n" + current_result.stdout
                else:
                    display_info = result.stdout
                
                return display_info
                
            elif action == "set_resolution":
                display = params.get("display", 0)
                width = params.get("width")
                height = params.get("height")
                
                if width is None or height is None:
                    return "Error: Missing width or height parameters"
                
                try:
                    display = int(display)
                    width = int(width)
                    height = int(height)
                except ValueError:
                    return "Error: Display, width, and height must be numbers"
                
                # Use PowerShell to change display resolution
                ps_cmd = f'powershell -Command "$ErrorActionPreference = \'Stop\'; Add-Type -AssemblyName System.Windows.Forms; $displays = [System.Windows.Forms.Screen]::AllScreens; if ($displays.Count -le {display}) {{ Write-Output \'Error: Display index out of range\' }} else {{ $bounds = $displays[{display}].Bounds; $device = $displays[{display}].DeviceName; Add-Type -TypeDefinition \'@using System; using System.Runtime.InteropServices; public class PInvoke {{ [DllImport(\\"user32.dll\\")] public static extern int ChangeDisplaySettingsEx(string lpszDeviceName, ref DEVMODE lpDevMode, IntPtr hwnd, int dwflags, IntPtr lParam); [StructLayout(LayoutKind.Sequential)] public struct DEVMODE {{ [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName; public short dmSpecVersion; public short dmDriverVersion; public short dmSize; public short dmDriverExtra; public int dmFields; public int dmPositionX; public int dmPositionY; public int dmDisplayOrientation; public int dmDisplayFixedOutput; public short dmColor; public short dmDuplex; public short dmYResolution; public short dmTTOption; public short dmCollate; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName; public short dmLogPixels; public int dmBitsPerPel; public int dmPelsWidth; public int dmPelsHeight; public int dmDisplayFlags; public int dmDisplayFrequency; public int dmICMMethod; public int dmICMIntent; public int dmMediaType; public int dmDitherType; public int dmReserved1; public int dmReserved2; public int dmPanningWidth; public int dmPanningHeight; }}\'; $dm = New-Object PInvoke+DEVMODE; $dm.dmDeviceName = $device; $dm.dmSize = [System.Runtime.InteropServices.Marshal]::SizeOf($dm); $dm.dmPelsWidth = {width}; $dm.dmPelsHeight = {height}; $dm.dmFields = 0x00800000 -bor 0x00080000; $result = [PInvoke]::ChangeDisplaySettingsEx($device, [ref]$dm, [IntPtr]::Zero, 0, [IntPtr]::Zero); if ($result -eq 0) {{ Write-Output \'Successfully changed resolution\' }} else {{ Write-Output (\'Failed to change resolution, code: \' + $result) }} }}"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Error: Display index out of range" in result.stdout:
                    return f"Error: Display index {display} out of range"
                
                if "Successfully changed resolution" in result.stdout:
                    return f"Successfully changed resolution of display {display} to {width}x{height}"
                
                return f"Result of resolution change attempt:\n{result.stdout}"
                
            elif action == "set_brightness":
                level = params.get("level")
                
                if level is None:
                    return "Error: Missing brightness level parameter"
                
                try:
                    level = int(level)
                    if not (0 <= level <= 100):
                        return "Error: Brightness level must be between 0 and 100"
                except ValueError:
                    return "Error: Brightness level must be a number"
                
                # Use PowerShell to set display brightness
                ps_cmd = f'powershell -Command "Import-Module Microsoft.PowerShell.Management; $monitors = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods; if ($monitors.Count -eq 0) {{ Write-Output \'Error: No monitors support brightness control\' }} else {{ foreach ($monitor in $monitors) {{ $monitor.WmiSetBrightness(0, {level}) }}; Write-Output (\'Set brightness to {level}%\') }}"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Error: No monitors support brightness control" in result.stdout:
                    return "Error: No monitors support brightness control"
                
                if f"Set brightness to {level}%" in result.stdout:
                    return f"Successfully set brightness to {level}%"
                
                return f"Result of brightness change attempt:\n{result.stdout}"
                
            elif action == "set_orientation":
                display = params.get("display", 0)
                orientation = params.get("orientation", "").lower()
                
                if not orientation:
                    return "Error: Missing orientation parameter"
                
                try:
                    display = int(display)
                except ValueError:
                    return "Error: Display must be a number"
                
                # Map orientation to values
                orientation_map = {
                    "landscape": 0,
                    "portrait": 1,
                    "flipped_landscape": 2,
                    "flipped_portrait": 3
                }
                
                if orientation not in orientation_map:
                    return f"Error: Invalid orientation '{orientation}'. Valid orientations are: {', '.join(orientation_map.keys())}"
                
                orientation_value = orientation_map[orientation]
                
                # Use PowerShell to change display orientation
                ps_cmd = f'powershell -Command "$ErrorActionPreference = \'Stop\'; Add-Type -AssemblyName System.Windows.Forms; $displays = [System.Windows.Forms.Screen]::AllScreens; if ($displays.Count -le {display}) {{ Write-Output \'Error: Display index out of range\' }} else {{ $device = $displays[{display}].DeviceName; Add-Type -TypeDefinition \'@using System; using System.Runtime.InteropServices; public class PInvoke {{ [DllImport(\\"user32.dll\\")] public static extern int ChangeDisplaySettingsEx(string lpszDeviceName, ref DEVMODE lpDevMode, IntPtr hwnd, int dwflags, IntPtr lParam); [StructLayout(LayoutKind.Sequential)] public struct DEVMODE {{ [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName; public short dmSpecVersion; public short dmDriverVersion; public short dmSize; public short dmDriverExtra; public int dmFields; public int dmPositionX; public int dmPositionY; public int dmDisplayOrientation; public int dmDisplayFixedOutput; public short dmColor; public short dmDuplex; public short dmYResolution; public short dmTTOption; public short dmCollate; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName; public short dmLogPixels; public int dmBitsPerPel; public int dmPelsWidth; public int dmPelsHeight; public int dmDisplayFlags; public int dmDisplayFrequency; public int dmICMMethod; public int dmICMIntent; public int dmMediaType; public int dmDitherType; public int dmReserved1; public int dmReserved2; public int dmPanningWidth; public int dmPanningHeight; }}\'; $dm = New-Object PInvoke+DEVMODE; $dm.dmDeviceName = $device; $dm.dmSize = [System.Runtime.InteropServices.Marshal]::SizeOf($dm); $dm.dmDisplayOrientation = {orientation_value}; $dm.dmFields = 0x00000080; $result = [PInvoke]::ChangeDisplaySettingsEx($device, [ref]$dm, [IntPtr]::Zero, 0, [IntPtr]::Zero); if ($result -eq 0) {{ Write-Output \'Successfully changed orientation\' }} else {{ Write-Output (\'Failed to change orientation, code: \' + $result) }} }}"'
                
                result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
                
                if "Error: Display index out of range" in result.stdout:
                    return f"Error: Display index {display} out of range"
                
                if "Successfully changed orientation" in result.stdout:
                    return f"Successfully changed orientation of display {display} to {orientation}"
                
                return f"Result of orientation change attempt:\n{result.stdout}"
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: info, set_resolution, set_brightness, set_orientation"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in display management: {str(e)}")
            return f"Error in display management: {str(e)}"
