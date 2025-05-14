"""
Base functionality for file system tools.
"""

import sys

import os
import logging
import platform
import subprocess
from typing import Optional, Any, Dict, List, Union, Callable
import json
from pathlib import Path

# Assuming you're using LangChain's BaseTool
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


# Configure logger
logger = logging.getLogger("langchain_fs_tools")

def setup_fs_logger(level=logging.INFO):
    """Setup the file system tools logger with the specified level."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

def safe_path_join(base_path: str, *paths: str) -> str:
    """
    Safely join paths to prevent directory traversal attacks.
    
    Args:
        base_path: The base directory
        paths: Additional path components to join
        
    Returns:
        The joined path restricted to base_path or its subdirectories
    """
    base_path = os.path.abspath(os.path.expanduser(base_path))
    joined_path = os.path.normpath(os.path.join(base_path, *paths))
    
    # Ensure the resulting path is within the base_path
    if not joined_path.startswith(base_path):
        raise ValueError(f"Security error: Path would escape base directory: {joined_path}")
        
    return joined_path

def is_binary_file(file_path: str) -> bool:
    """
    Check if a file is binary by reading its first few kilobytes.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(file_path, 'rb') as file:
            chunk = file.read(4096)
            return b'\x00' in chunk  # A simple heuristic for binary files
    except Exception as e:
        logger.error(f"Error checking if file is binary: {str(e)}")
        return False

def handle_file_operation_error(operation: str) -> Callable:
    """
    Decorator for handling file operation errors.
    
    Args:
        operation: String describing the operation being performed
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.error(f"File not found during {operation}: {str(e)}")
                return f"Error: File not found - {str(e)}"
            except PermissionError as e:
                logger.error(f"Permission error during {operation}: {str(e)}")
                return f"Error: Permission denied - {str(e)}"
            except IsADirectoryError as e:
                logger.error(f"Directory error during {operation}: {str(e)}")
                return f"Error: Expected a file but found a directory - {str(e)}"
            except OSError as e:
                logger.error(f"OS error during {operation}: {str(e)}")
                return f"Error: Operating system error - {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error during {operation}: {str(e)}")
                return f"Error during {operation}: {str(e)}"
        return wrapper
    return decorator

def parse_json_input(input_str: str, required_fields: List[str]) -> Dict[str, Any]:
    """
    Parse JSON input string and validate required fields.
    
    Args:
        input_str: JSON string to parse
        required_fields: List of required field names
        
    Returns:
        Dictionary with parsed input
        
    Raises:
        ValueError: If input is invalid or missing required fields
    """
    try:
        # Try parsing as JSON
        try:
            data = json.loads(input_str)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract fields from string
            import re
            data = {}
            for field in required_fields:
                match = re.search(rf"{field}['\"]?\s*[:=]\s*['\"]?([^'\",:}}\]]+)['\"]?", input_str)
                if match:
                    data[field] = match.group(1).strip()
        
        # Validate required fields
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary/JSON object")
            
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Input must contain '{field}'")
                
        return data
    except Exception as e:
        raise ValueError(f"Error parsing input: {str(e)}")
