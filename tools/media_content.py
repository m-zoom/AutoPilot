"""
Media & Content Tools

Tools for handling media content such as screenshots, media playback,
text-to-speech, speech recognition, and OCR.
"""

import sys

import os
import logging
import base64
import tempfile
from typing import Optional, Dict, Any
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
import os
import json
import pyautogui
from PIL import Image
import io
import base64
import logging

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

class ScreenshotTool(BaseTool):
    """Tool for capturing screen images."""

    name: str = "screenshot"
    description: str = """
    Captures a screenshot of the screen or a specific region.

    Input should be a JSON object with the following structure:
    {
        "region": {"left": int, "top": int, "width": int, "height": int},
        "filename": "optional_path.png",
        "return_base64": true | false  # optional, defaults to false
    }

    - If "region" is not specified, captures the entire screen.
    - If "filename" is specified, saves the image to disk.
    - If "return_base64" is true, returns the image as a base64-encoded string.
      (Warning: base64 output can consume a lot of tokens.)

    Returns the path to the saved screenshot or a base64-encoded image string.
    """

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Capture a screenshot."""
        try:
            params = json.loads(input_str) if input_str else {}

            # Extract parameters
            region = params.get("region")
            filename = params.get("filename")
            return_base64 = params.get("return_base64", False)

            # Take the screenshot
            if region:
                left = region.get("left", 0)
                top = region.get("top", 0)
                width = region.get("width")
                height = region.get("height")

                if width is None or height is None:
                    return "Error: Width and height must be specified in the region"

                screenshot = pyautogui.screenshot(region=(left, top, width, height))
            else:
                screenshot = pyautogui.screenshot()

            # Save to file if requested
            if filename:
                os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
                screenshot.save(filename)

            # Return base64 if requested
            if return_base64:
                buffer = io.BytesIO()
                screenshot.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/png;base64,{img_str}"

            if filename:
                return f"Screenshot saved to {filename}"
            else:
                return "Screenshot captured (not saved and base64 not requested)."

        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return f"Error capturing screenshot: {str(e)}"

class MediaPlaybackTool(BaseTool):
    """Tool for controlling media playback functions."""
    
    name: str = "media_playback"
    description: str = """
    Controls media playback functions like play, pause, stop, volume, and media keys.
    
    Input should be a JSON object with the following structure:
    {"action": "play/pause/stop/next/previous/volume_up/volume_down/mute"}
    Or for volume control: {"action": "set_volume", "level": 0-100}
    
    Returns a confirmation message or error.
    
    Example: {"action": "play"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Control media playback."""
        try:
            import json
            import pyautogui
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            # Map actions to keys
            action_keys = {
                "play": "playpause",
                "pause": "playpause",
                "stop": "stop",
                "next": "nexttrack",
                "previous": "prevtrack",
                "volume_up": "volumeup",
                "volume_down": "volumedown",
                "mute": "volumemute"
            }
            
            if action in action_keys:
                try:
                    pyautogui.press(action_keys[action])
                    return f"Successfully performed {action} action"
                except Exception as e:
                    return f"Error executing media key command: {str(e)}"
            
            elif action == "set_volume":
                level = params.get("level")
                
                if level is None:
                    return "Error: Missing volume level parameter"
                
                try:
                    # Validate volume level
                    level = int(level)
                    if level < 0 or level > 100:
                        return "Error: Volume level must be between 0 and 100"
                    
                    # Windows-specific volume control using PowerShell
                    import subprocess
                    
                    # Convert level to value between 0 and 1
                    volume_value = level / 100
                    
                    # Use PowerShell to set volume
                    powershell_cmd = f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]0xAD); Start-Sleep -Milliseconds 50; $volume = New-Object -ComObject WScript.Shell; for($i=0;$i -lt 50;$i++){{$volume.SendKeys([char]0xAE)}}; Start-Sleep -Milliseconds 50; $level = [math]::Round({volume_value} * 50); for($i=0;$i -lt $level;$i++){{$volume.SendKeys([char]0xAF)}}"'
                    
                    subprocess.run(powershell_cmd, shell=True, check=True)
                    
                    return f"Volume set to {level}%"
                except ValueError:
                    return "Error: Volume level must be a number"
                except Exception as e:
                    return f"Error setting volume: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: {', '.join(list(action_keys.keys()) + ['set_volume'])}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error controlling media playback: {str(e)}")
            return f"Error controlling media playback: {str(e)}"


class TextToSpeechTool(BaseTool):
    """Tool for converting text to spoken audio."""
    
    name: str = "text_to_speech"
    description: str = """
    Converts text to spoken audio using the default Windows voice.
    
    Input should be a JSON object with the following structure:
    {"text": "Text to speak", "rate": 150, "volume": 1.0, "voice": "voice_name", "save_to": "optional_output.mp3"}
    
    Rate is in words per minute (default: 150).
    Volume is between 0.0 and 1.0 (default: 1.0).
    Voice is optional and will use the default voice if not specified.
    If save_to is specified, saves the audio to that file.
    
    Returns a confirmation message or error.
    
    Example: {"text": "Hello, world!", "rate": 150, "volume": 0.8}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Convert text to speech."""
        try:
            import json
            import pyttsx3
            
            params = json.loads(input_str)
            
            text = params.get("text", "")
            rate = params.get("rate", 150)
            volume = params.get("volume", 1.0)
            voice_name = params.get("voice")
            save_to = params.get("save_to")
            
            if not text:
                return "Error: Missing text parameter"
            
            # Initialize the TTS engine
            engine = pyttsx3.init()
            
            # Set properties
            engine.setProperty('rate', rate)
            engine.setProperty('volume', volume)
            
            # Set voice if specified
            if voice_name:
                voices = engine.getProperty('voices')
                for voice in voices:
                    if voice_name.lower() in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            
            if save_to:
                # Save to file
                try:
                    engine.save_to_file(text, save_to)
                    engine.runAndWait()
                    return f"Successfully saved speech to {save_to}"
                except Exception as e:
                    return f"Error saving speech to file: {str(e)}"
            else:
                # Speak the text
                engine.say(text)
                engine.runAndWait()
                return f"Successfully spoke the text: '{text}'"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in text-to-speech conversion: {str(e)}")
            return f"Error in text-to-speech conversion: {str(e)}"


class SpeechRecognitionTool(BaseTool):
    """Tool for converting spoken audio to text."""
    
    name: str = "speech_recognition"
    description: str = """
    Converts spoken audio to text using speech recognition.
    
    Input should be a JSON object with the following structure:
    {"source": "microphone/file", "duration": 5, "file_path": "path_to_audio_file", "language": "en-US"}
    
    Source can be "microphone" to listen from the microphone or "file" to use an audio file.
    Duration (in seconds) is only used when source is "microphone" (default: 5).
    File_path is only used when source is "file".
    Language specifies the recognition language (default: "en-US").
    
    Returns the recognized text or an error.
    
    Example: {"source": "microphone", "duration": 10, "language": "en-US"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Convert speech to text."""
        try:
            import json
            import speech_recognition as sr
            
            params = json.loads(input_str)
            
            source = params.get("source", "").lower()
            duration = params.get("duration", 5)
            file_path = params.get("file_path", "")
            language = params.get("language", "en-US")
            
            if not source:
                return "Error: Missing source parameter"
            
            if source not in ["microphone", "file"]:
                return "Error: Source must be 'microphone' or 'file'"
            
            if source == "file" and not file_path:
                return "Error: Missing file_path parameter for file source"
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            if source == "microphone":
                # Recognize from microphone
                try:
                    with sr.Microphone() as mic:
                        recognizer.adjust_for_ambient_noise(mic, duration=0.5)
                        return f"Listening for {duration} seconds..."
                        audio = recognizer.listen(mic, timeout=duration)
                except sr.RequestError as e:
                    return f"API unavailable: {str(e)}"
                except sr.WaitTimeoutError:
                    return "No speech detected within the timeout period"
                except Exception as e:
                    return f"Error accessing microphone: {str(e)}"
            else:
                # Recognize from file
                try:
                    with sr.AudioFile(file_path) as source:
                        audio = recognizer.record(source)
                except FileNotFoundError:
                    return f"Error: Audio file not found: {file_path}"
                except Exception as e:
                    return f"Error reading audio file: {str(e)}"
            
            # Perform the recognition
            try:
                text = recognizer.recognize_google(audio, language=language)
                return f"Recognized text: {text}"
            except sr.UnknownValueError:
                return "Could not understand audio"
            except sr.RequestError as e:
                return f"Could not request results from Google Speech Recognition service: {str(e)}"
            except Exception as e:
                return f"Error in speech recognition: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in speech recognition: {str(e)}")
            return f"Error in speech recognition: {str(e)}"


class OCRTool(BaseTool):
    """Tool for extracting text from images."""
    
    name: str = "ocr"
    description: str = """
    Extracts text from images using Optical Character Recognition (OCR).
    
    Input should be a JSON object with the following structure:
    {"image_path": "path_to_image", "language": "eng", "preprocess": true/false}
    
    Language specifies the OCR language (default: "eng").
    Preprocess improves recognition for certain types of images (default: true).
    
    Returns the extracted text or an error.
    
    Example: {"image_path": "C:\\Images\\document.png", "language": "eng"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Extract text from image."""
        try:
            import json
            import pytesseract
            from PIL import Image
            import cv2
            import numpy as np
            
            params = json.loads(input_str)
            
            image_path = params.get("image_path", "")
            language = params.get("language", "eng")
            preprocess = params.get("preprocess", True)
            
            if not image_path:
                return "Error: Missing image_path parameter"
            
            if not os.path.exists(image_path):
                return f"Error: Image file not found: {image_path}"
            
            # Set the path to the Tesseract executable if not in PATH
            # Uncomment and modify the line below if needed
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            try:
                # Load the image
                if preprocess:
                    # Use OpenCV for preprocessing
                    image = cv2.imread(image_path)
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    
                    # Apply thresholding to remove noise
                    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                    
                    # Save preprocessed image to a temporary file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                        temp_filename = temp.name
                    
                    cv2.imwrite(temp_filename, binary)
                    
                    # Use the preprocessed image for OCR
                    text = pytesseract.image_to_string(Image.open(temp_filename), lang=language)
                    
                    # Clean up
                    os.unlink(temp_filename)
                else:
                    # Use PIL directly without preprocessing
                    text = pytesseract.image_to_string(Image.open(image_path), lang=language)
                
                if not text.strip():
                    return "No text found in the image"
                
                return f"Extracted text:\n{text}"
            
            except Exception as e:
                return f"Error processing image: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in OCR processing: {str(e)}")
            return f"Error in OCR processing: {str(e)}"

import cv2
import time
import numpy as np

class ScreenRecordTool(BaseTool):
    """Tool for recording the screen to a video file."""

    name: str = "screen_record"
    description: str = """
    Records the screen for a specified duration and saves the result as a video file (MP4 format).

    Input should be a JSON string with the following structure:
    {
        "duration": 5,  // Duration in seconds
        "filename": "path/to/output.mp4",  // Optional, default: 'screen_record.mp4'
        "fps": 10       // Optional frames per second (default: 10)
    }

    Returns the path to the saved video file.
    """

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            # Handle different types of quotation marks that might be present
            input_str = input_str.replace("'", '"')
            
            # Parse the input as a JSON string
            params = json.loads(input_str)

            # Get parameters from JSON
            duration = float(params.get("duration", 5))
            filename = params.get("filename", "screen_record.mp4")
            fps = int(params.get("fps", 10))

            # Normalize path separators (allow both / and \)
            filename = os.path.normpath(filename)

            # Validate parameters
            if duration <= 0:
                return "Error: Duration must be greater than 0."

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            # Get screen size for recording
            screen_size = pyautogui.size()

            # Video output setup using OpenCV
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(filename, fourcc, fps, screen_size)

            if not out.isOpened():
                return f"Error: Could not open video writer for file {filename}"

            # Start recording the screen
            start_time = time.time()
            frames_captured = 0
            
            print(f"Recording screen for {duration} seconds at {fps} FPS...")
            
            while (time.time() - start_time) < duration:
                # Capture screenshot
                img = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                out.write(frame)
                frames_captured += 1
                
                # Sleep to maintain FPS
                time.sleep(1 / fps)

            # Release the video writer
            out.release()
            
            return f"Screen recording completed. {frames_captured} frames captured and saved to {filename}"

        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input. Details: {str(e)}"
        except Exception as e:
            import traceback
            return f"Error during screen recording: {str(e)}\n{traceback.format_exc()}"
    """Tool for recording the screen to a video file."""

    name: str = "screen_record"
    description: str = """
    Records the screen for a specified duration and saves the result as a video file (MP4 format).

    Input should be a JSON object like:
    {
        "duration": 5,  // Duration in seconds
        "filename": "C:\\Videos\\screen_record.mp4",  // Optional, default: 'screen_record.mp4'
        "fps": 10       // Optional frames per second (default: 10)
    }

    Returns the path to the saved video.
    """

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            # Parse the input as a JSON string
            params = json.loads(input_str)

            # Get parameters from JSON
            duration = float(params.get("duration", 5))
            filename = params.get("filename", "screen_record.mp4")
            fps = int(params.get("fps", 10))

            # Validate parameters
            if duration <= 0:
                return "Error: Duration must be greater than 0."

            # Get screen size for recording
            screen_size = pyautogui.size()

            # Video output setup using OpenCV
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            out = cv2.VideoWriter(filename, fourcc, fps, screen_size)

            # Start recording the screen
            start_time = time.time()
            while (time.time() - start_time) < duration:
                img = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                out.write(frame)
                time.sleep(1 / fps)

            # Release the video writer
            out.release()

            # Return the path to the saved video
            return f"Screen recording saved to {filename}"

        except json.JSONDecodeError:
            return "Error: Invalid JSON input."
        except Exception as e:
            return f"Error during screen recording: {str(e)}"
    """ Tool for recording the screen to a video file."""

    name: str = "screen_record"
    description: str = """
    Records the screen for a specified duration and saves the result as a video file (MP4 format).

    Input should be a JSON object like:
    {
        "duration": 5,  // Duration in seconds
        "filename": "C:\\Videos\\screen_record.mp4",  // Optional, default: 'screen_record.mp4'
        "fps": 10       // Optional frames per second (default: 10)
    }

    Returns the path to the saved video.
    """

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            params = json.loads(input_str)
            duration = float(params.get("duration", 5))
            filename = params.get("filename", "screen_record.mp4")
            fps = int(params.get("fps", 10))

            if duration <= 0:
                return "Error: Duration must be greater than 0."

            screen_size = pyautogui.size()
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            out = cv2.VideoWriter(filename, fourcc, fps, screen_size)

            start_time = time.time()
            while (time.time() - start_time) < duration:
                img = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                out.write(frame)
                time.sleep(1 / fps)

            out.release()
            return f"Screen recording saved to {filename}"

        except json.JSONDecodeError:
            return "Error: Invalid JSON input."
        except Exception as e:
            return f"Error during screen recording: {str(e)}"