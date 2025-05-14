"""
Automation Tools

Tools for automating keyboard and mouse operations, recording macros,
and creating workflow sequences.
"""

import sys

import os
import logging
import time
import json
import tempfile
from typing import Optional, Dict, Any, List
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

class KeyboardSimulationTool(BaseTool):
    """Tool for simulating keyboard inputs."""
    
    name: str = "keyboard_simulation"
    description: str = """
    Simulates keyboard keystrokes and text entry.
    
    Input should be a JSON object with the following structure:
    For typing text: {"action": "type", "text": "Text to type"}
    For key combinations: {"action": "hotkey", "keys": ["ctrl", "c"]}
    For pressing a single key: {"action": "press", "key": "enter"}
    For sequential key presses: {"action": "sequence", "keys": ["alt", "tab", "tab"]}
    
    Returns a success message or error.
    
    Example: {"action": "hotkey", "keys": ["win", "r"]}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Simulate keyboard inputs."""
        try:
            import pyautogui
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            # Sleep briefly to give user time to prepare
            time.sleep(0.5)
            
            if action == "type":
                text = params.get("text", "")
                
                if not text:
                    return "Error: Missing text parameter"
                
                # Type the text
                pyautogui.write(text)
                
                return f"Successfully typed text: '{text}'"
                
            elif action == "hotkey":
                keys = params.get("keys", [])
                
                if not keys:
                    return "Error: Missing keys parameter"
                
                # Validate keys
                for key in keys:
                    if not self._is_valid_key(key):
                        return f"Error: Invalid key '{key}'"
                
                # Press the hotkey combination
                pyautogui.hotkey(*keys)
                
                return f"Successfully pressed hotkey: {' + '.join(keys)}"
                
            elif action == "press":
                key = params.get("key", "")
                
                if not key:
                    return "Error: Missing key parameter"
                
                # Validate key
                if not self._is_valid_key(key):
                    return f"Error: Invalid key '{key}'"
                
                # Press the key
                pyautogui.press(key)
                
                return f"Successfully pressed key: {key}"
                
            elif action == "sequence":
                keys = params.get("keys", [])
                
                if not keys:
                    return "Error: Missing keys parameter"
                
                # Validate keys
                for key in keys:
                    if not self._is_valid_key(key):
                        return f"Error: Invalid key '{key}'"
                
                # Press the keys in sequence
                for key in keys:
                    pyautogui.press(key)
                    time.sleep(0.1)  # Small delay between key presses
                
                return f"Successfully pressed keys in sequence: {', '.join(keys)}"
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: type, hotkey, press, sequence"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError:
            return "Error: pyautogui module not installed. Install it with 'pip install pyautogui'"
        except Exception as e:
            logger.error(f"Error in keyboard simulation: {str(e)}")
            return f"Error in keyboard simulation: {str(e)}"
    
    def _is_valid_key(self, key: str) -> bool:
        """Check if a key is valid for pyautogui."""
        # List of common valid keys in pyautogui
        valid_keys = [
            # Letters
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            
            # Numbers
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            
            # Special keys
            'alt', 'ctrl', 'shift', 'win', 'command', 'option',
            'enter', 'return', 'tab', 'space', 'backspace', 'delete', 'esc',
            'escape', 'up', 'down', 'left', 'right', 'home', 'end', 'pageup',
            'pagedown', 'insert', 'printscreen',
            
            # Function keys
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            
            # Punctuation
            '`', '-', '=', '[', ']', '\\', ';', '\'', ',', '.', '/',
            '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+',
            '{', '}', '|', ':', '"', '<', '>', '?'
        ]
        
        return key.lower() in valid_keys


class MouseOperationTool(BaseTool):
    """Tool for controlling mouse movements and clicks."""
    
    name: str = "mouse_operation"
    description: str = """
    Controls mouse movements, clicks, and scrolling.
    
    Input should be a JSON object with the following structure:
    For moving: {"action": "move", "x": 100, "y": 200, "duration": 0.5}
    For clicking: {"action": "click", "button": "left/right/middle", "x": 100, "y": 200}
    For double-clicking: {"action": "doubleclick", "x": 100, "y": 200}
    For dragging: {"action": "drag", "start_x": 100, "start_y": 200, "end_x": 300, "end_y": 400, "duration": 0.5}
    For scrolling: {"action": "scroll", "amount": -10}
    
    Returns a success message or error.
    
    Example: {"action": "click", "button": "left", "x": 500, "y": 500}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Control mouse operations."""
        try:
            import pyautogui
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            # Sleep briefly to give user time to prepare
            time.sleep(0.5)
            
            # Get screen size for validation
            screen_width, screen_height = pyautogui.size()
            
            if action == "move":
                x = params.get("x")
                y = params.get("y")
                duration = params.get("duration", 0.5)
                
                if x is None or y is None:
                    return "Error: Missing x or y parameter"
                
                # Validate coordinates
                if not (0 <= x <= screen_width and 0 <= y <= screen_height):
                    return f"Error: Coordinates ({x}, {y}) are outside screen boundaries ({screen_width}x{screen_height})"
                
                # Move the mouse
                pyautogui.moveTo(x, y, duration=duration)
                
                return f"Successfully moved mouse to coordinates ({x}, {y})"
                
            elif action == "click":
                button = params.get("button", "left").lower()
                x = params.get("x")
                y = params.get("y")
                
                # Validate button
                if button not in ["left", "right", "middle"]:
                    return f"Error: Invalid button '{button}'. Valid buttons are: left, right, middle"
                
                if x is not None and y is not None:
                    # Validate coordinates
                    if not (0 <= x <= screen_width and 0 <= y <= screen_height):
                        return f"Error: Coordinates ({x}, {y}) are outside screen boundaries ({screen_width}x{screen_height})"
                    
                    # Click at specific coordinates
                    pyautogui.click(x, y, button=button)
                    
                    return f"Successfully clicked {button} button at coordinates ({x}, {y})"
                else:
                    # Click at current position
                    pyautogui.click(button=button)
                    
                    current_x, current_y = pyautogui.position()
                    return f"Successfully clicked {button} button at current position ({current_x}, {current_y})"
                
            elif action == "doubleclick":
                x = params.get("x")
                y = params.get("y")
                
                if x is not None and y is not None:
                    # Validate coordinates
                    if not (0 <= x <= screen_width and 0 <= y <= screen_height):
                        return f"Error: Coordinates ({x}, {y}) are outside screen boundaries ({screen_width}x{screen_height})"
                    
                    # Double-click at specific coordinates
                    pyautogui.doubleClick(x, y)
                    
                    return f"Successfully double-clicked at coordinates ({x}, {y})"
                else:
                    # Double-click at current position
                    pyautogui.doubleClick()
                    
                    current_x, current_y = pyautogui.position()
                    return f"Successfully double-clicked at current position ({current_x}, {current_y})"
                
            elif action == "drag":
                start_x = params.get("start_x")
                start_y = params.get("start_y")
                end_x = params.get("end_x")
                end_y = params.get("end_y")
                duration = params.get("duration", 0.5)
                
                if start_x is None or start_y is None or end_x is None or end_y is None:
                    return "Error: Missing start or end coordinates"
                
                # Validate coordinates
                if not (0 <= start_x <= screen_width and 0 <= start_y <= screen_height):
                    return f"Error: Start coordinates ({start_x}, {start_y}) are outside screen boundaries ({screen_width}x{screen_height})"
                
                if not (0 <= end_x <= screen_width and 0 <= end_y <= screen_height):
                    return f"Error: End coordinates ({end_x}, {end_y}) are outside screen boundaries ({screen_width}x{screen_height})"
                
                # Perform drag operation
                pyautogui.moveTo(start_x, start_y)
                pyautogui.dragTo(end_x, end_y, duration=duration)
                
                return f"Successfully dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
                
            elif action == "scroll":
                amount = params.get("amount")
                
                if amount is None:
                    return "Error: Missing amount parameter"
                
                # Scroll the mouse wheel
                pyautogui.scroll(amount)
                
                direction = "down" if amount < 0 else "up"
                return f"Successfully scrolled {direction} by {abs(amount)} units"
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: move, click, doubleclick, drag, scroll"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError:
            return "Error: pyautogui module not installed. Install it with 'pip install pyautogui'"
        except Exception as e:
            logger.error(f"Error in mouse operation: {str(e)}")
            return f"Error in mouse operation: {str(e)}"


class MacroRecorderTool(BaseTool):
    """Tool for recording and playing sequences of actions."""
    
    name: str = "macro_recorder"
    description: str = """
    Records and plays sequences of keyboard and mouse actions.
    
    Input should be a JSON object with the following structure:
    For recording: {"action": "record", "duration": 10, "file_path": "path/to/save.macro"}
    For playback: {"action": "play", "file_path": "path/to/save.macro", "repeat": 1}
    For listing actions in a macro: {"action": "list", "file_path": "path/to/save.macro"}
    
    Returns a success message or error.
    
    Example: {"action": "record", "duration": 5, "file_path": "C:\\Macros\\my_macro.json"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Record or play macros."""
        try:
            import pyautogui
            import keyboard
            import mouse
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            file_path = params.get("file_path", "")
            
            if not action:
                return "Error: Missing action parameter"
                
            if not file_path:
                return "Error: Missing file_path parameter"
            
            if action == "record":
                duration = params.get("duration", 10)
                
                try:
                    duration = int(duration)
                    if duration < 1:
                        return "Error: Duration must be at least 1 second"
                    if duration > 60:
                        return "Error: Duration cannot exceed 60 seconds for safety reasons"
                except ValueError:
                    return "Error: Duration must be a number"
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                # Record the macro
                return self._record_macro(duration, file_path)
                
            elif action == "play":
                repeat = params.get("repeat", 1)
                
                try:
                    repeat = int(repeat)
                    if repeat < 1:
                        return "Error: Repeat count must be at least 1"
                    if repeat > 10:
                        return "Error: Repeat count cannot exceed 10 for safety reasons"
                except ValueError:
                    return "Error: Repeat count must be a number"
                
                if not os.path.exists(file_path):
                    return f"Error: Macro file not found: {file_path}"
                
                # Play the macro
                return self._play_macro(file_path, repeat)
                
            elif action == "list":
                if not os.path.exists(file_path):
                    return f"Error: Macro file not found: {file_path}"
                
                # List the macro actions
                return self._list_macro(file_path)
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: record, play, list"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}. Install with 'pip install pyautogui keyboard mouse'"
        except Exception as e:
            logger.error(f"Error in macro recorder: {str(e)}")
            return f"Error in macro recorder: {str(e)}"
    
    def _record_macro(self, duration: int, file_path: str) -> str:
        """Record keyboard and mouse events."""
        try:
            import keyboard
            import mouse
            import time
            
            print(f"Recording will start in 3 seconds and last for {duration} seconds...")
            time.sleep(3)
            print("Recording started! Perform the actions you want to record.")
            
            recorded_events = []
            start_time = time.time()
            
            # Setup event recording
            keyboard_events = []
            mouse_events = []
            
            # Record keyboard events
            keyboard.start_recording()
            
            # Record mouse events
            mouse.hook(mouse_events.append)
            
            # Wait for the specified duration
            time.sleep(duration)
            
            # Stop recording
            keyboard_events = keyboard.stop_recording()
            mouse.unhook(mouse_events.append)
            
            print("Recording finished!")
            
            # Process keyboard events
            for event in keyboard_events:
                if event.event_type in ['down', 'up']:
                    recorded_events.append({
                        'type': 'keyboard',
                        'event_type': event.event_type,
                        'key': event.name,
                        'time': event.time - start_time
                    })
            
            # Process mouse events
            for event in mouse_events:
                if hasattr(event, 'event_type'):
                    event_data = {
                        'type': 'mouse',
                        'event_type': event.event_type,
                        'time': event.time - start_time
                    }
                    
                    if hasattr(event, 'button'):
                        event_data['button'] = event.button
                    
                    if hasattr(event, 'x') and hasattr(event, 'y'):
                        event_data['x'] = event.x
                        event_data['y'] = event.y
                    
                    if hasattr(event, 'wheel_delta'):
                        event_data['wheel_delta'] = event.wheel_delta
                    
                    recorded_events.append(event_data)
            
            # Sort events by time
            recorded_events.sort(key=lambda e: e['time'])
            
            # Save the recorded macro
            with open(file_path, 'w') as f:
                json.dump(recorded_events, f, indent=2)
            
            return f"Successfully recorded {len(recorded_events)} events to {file_path}"
            
        except Exception as e:
            return f"Error recording macro: {str(e)}"
    
    def _play_macro(self, file_path: str, repeat: int) -> str:
        """Play back recorded macro events."""
        try:
            import pyautogui
            import keyboard
            import mouse
            import time
            
            # Load the macro
            with open(file_path, 'r') as f:
                events = json.load(f)
            
            print(f"Playback will start in 3 seconds and repeat {repeat} times...")
            time.sleep(3)
            print("Playback started!")
            
            for i in range(repeat):
                if i > 0:
                    print(f"Starting repetition {i+1}...")
                    time.sleep(1)
                
                last_event_time = 0
                
                for event in events:
                    # Wait for the appropriate time
                    event_time = event['time']
                    time_to_wait = event_time - last_event_time
                    
                    if time_to_wait > 0:
                        time.sleep(time_to_wait)
                    
                    # Execute the event
                    if event['type'] == 'keyboard':
                        if event['event_type'] == 'down':
                            keyboard.press(event['key'])
                        elif event['event_type'] == 'up':
                            keyboard.release(event['key'])
                    
                    elif event['type'] == 'mouse':
                        if event['event_type'] == 'move':
                            pyautogui.moveTo(event['x'], event['y'])
                        elif event['event_type'] == 'click':
                            if 'x' in event and 'y' in event:
                                pyautogui.click(event['x'], event['y'], button=event['button'])
                            else:
                                pyautogui.click(button=event['button'])
                        elif event['event_type'] == 'scroll':
                            pyautogui.scroll(event['wheel_delta'])
                    
                    last_event_time = event_time
            
            print("Playback finished!")
            
            return f"Successfully played back {len(events)} events from {file_path} ({repeat} repetitions)"
            
        except json.JSONDecodeError:
            return f"Error: The macro file {file_path} contains invalid JSON"
        except Exception as e:
            return f"Error playing macro: {str(e)}"
    
    def _list_macro(self, file_path: str) -> str:
        """List actions in a macro file."""
        try:
            # Load the macro
            with open(file_path, 'r') as f:
                events = json.load(f)
            
            if not events:
                return f"The macro file {file_path} contains no events"
            
            # Format the events for display
            event_descriptions = []
            
            for i, event in enumerate(events):
                time_str = f"{event['time']:.2f}s"
                
                if event['type'] == 'keyboard':
                    action = f"Key {event['event_type']}: {event['key']}"
                elif event['type'] == 'mouse':
                    if event['event_type'] == 'move':
                        action = f"Mouse move to ({event['x']}, {event['y']})"
                    elif event['event_type'] == 'click':
                        if 'x' in event and 'y' in event:
                            action = f"Mouse {event['button']} click at ({event['x']}, {event['y']})"
                        else:
                            action = f"Mouse {event['button']} click"
                    elif event['event_type'] == 'scroll':
                        direction = "down" if event['wheel_delta'] < 0 else "up"
                        action = f"Mouse scroll {direction}"
                    else:
                        action = f"Mouse {event['event_type']}"
                else:
                    action = f"Unknown event: {event}"
                
                event_descriptions.append(f"{i+1}. [{time_str}] {action}")
            
            return f"Macro events in {file_path} ({len(events)} events):\n" + "\n".join(event_descriptions)
            
        except json.JSONDecodeError:
            return f"Error: The macro file {file_path} contains invalid JSON"
        except Exception as e:
            return f"Error listing macro: {str(e)}"


class WorkflowAutomationTool(BaseTool):
    """Tool for creating and executing workflow sequences."""
    
    name: str = "workflow_automation"
    description: str = """
    Creates and executes sequences of automation actions.
    
    Input should be a JSON object with the following structure:
    For creating a workflow: {"action": "create", "file_path": "path/to/workflow.json", "steps": [{"tool": "keyboard_simulation", "params": {"action": "type", "text": "Hello"}}, ...]}
    For executing a workflow: {"action": "execute", "file_path": "path/to/workflow.json"}
    For listing steps in a workflow: {"action": "list", "file_path": "path/to/workflow.json"}
    
    Returns a success message or error.
    
    Example: {"action": "create", "file_path": "C:\\Workflows\\my_workflow.json", "steps": [{"tool": "keyboard_simulation", "params": {"action": "hotkey", "keys": ["win", "r"]}}, {"tool": "keyboard_simulation", "params": {"action": "type", "text": "notepad"}}]}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Create or execute workflow sequences."""
        try:
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            file_path = params.get("file_path", "")
            
            if not action:
                return "Error: Missing action parameter"
                
            if not file_path:
                return "Error: Missing file_path parameter"
            
            if action == "create":
                steps = params.get("steps", [])
                
                if not steps:
                    return "Error: Missing or empty steps parameter"
                
                # Validate steps
                for i, step in enumerate(steps):
                    if "tool" not in step:
                        return f"Error: Missing tool name in step {i+1}"
                    if "params" not in step:
                        return f"Error: Missing params in step {i+1}"
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                # Save the workflow
                with open(file_path, 'w') as f:
                    json.dump(steps, f, indent=2)
                
                return f"Successfully created workflow with {len(steps)} steps in {file_path}"
                
            elif action == "execute":
                if not os.path.exists(file_path):
                    return f"Error: Workflow file not found: {file_path}"
                
                # Load the workflow
                with open(file_path, 'r') as f:
                    steps = json.load(f)
                
                if not steps:
                    return f"Error: Workflow file {file_path} contains no steps"
                
                # Import necessary tools
                import importlib
                from langchain.tools import BaseTool
                
                # Get all tool classes from the windows_agent_tools modules
                tool_classes = {}
                
                # Import modules dynamically
                modules = [
                    "windows_agent_tools.file_management",
                    "windows_agent_tools.media_content",
                    "windows_agent_tools.network_web",
                    "windows_agent_tools.data_processing",
                    "windows_agent_tools.system_integration",
                    "windows_agent_tools.development",
                    "windows_agent_tools.notifications",
                    "windows_agent_tools.security",
                    "windows_agent_tools.automation",
                    "windows_agent_tools.device_control"
                ]
                
                for module_name in modules:
                    try:
                        module = importlib.import_module(module_name)
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BaseTool) and attr != BaseTool:
                                tool_classes[attr().name] = attr
                    except ImportError:
                        pass
                
                # Execute each step
                results = []
                
                for i, step in enumerate(steps):
                    tool_name = step.get("tool")
                    params = step.get("params", {})
                    
                    # Check if we have the tool
                    if tool_name not in tool_classes:
                        results.append(f"Error in step {i+1}: Tool '{tool_name}' not found")
                        continue
                    
                    # Create an instance of the tool
                    tool_instance = tool_classes[tool_name]()
                    
                    # Execute the tool
                    try:
                        result = tool_instance._run(json.dumps(params))
                        results.append(f"Step {i+1}: {result}")
                    except Exception as e:
                        results.append(f"Error in step {i+1}: {str(e)}")
                
                return f"Workflow execution results for {file_path}:\n\n" + "\n\n".join(results)
                
            elif action == "list":
                if not os.path.exists(file_path):
                    return f"Error: Workflow file not found: {file_path}"
                
                # Load the workflow
                with open(file_path, 'r') as f:
                    steps = json.load(f)
                
                if not steps:
                    return f"The workflow file {file_path} contains no steps"
                
                # Format the steps for display
                step_descriptions = []
                
                for i, step in enumerate(steps):
                    tool_name = step.get("tool", "unknown")
                    params = step.get("params", {})
                    
                    step_descriptions.append(f"{i+1}. Tool: {tool_name}\n   Parameters: {json.dumps(params, indent=3)}")
                
                return f"Workflow steps in {file_path} ({len(steps)} steps):\n\n" + "\n\n".join(step_descriptions)
                
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: create, execute, list"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in workflow automation: {str(e)}")
            return f"Error in workflow automation: {str(e)}"
