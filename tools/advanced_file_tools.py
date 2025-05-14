"""
Advanced tools for the AI agent to interact with files.
Includes operations for analyzing files, searching file content, and manipulating file formats.
"""

import sys

import os
import json
import logging
import platform
import datetime
import mimetypes
import re
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
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

class SearchFileContentTool(BaseTool):
    """Tool for searching for a pattern within files in a directory."""
    
    name: str = "search_file_content"
    description: str = """
    Searches for a pattern in files within a specified directory.
    
    Input should be a JSON object with:
    - 'directory': path of the directory to search in
    - 'pattern': search pattern (can be a substring or regex pattern)
    - 'recursive' (optional): whether to search recursively in subdirectories (default is false)
    
    Example: {"directory": "project/src", "pattern": "TODO", "recursive": true}
    
    Returns a list of files containing the pattern along with the matching lines, or an error message.
    """
    
    def _run(self, search_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Search for a pattern in files within a directory."""
        try:
            # Parse the input
            import json
            try:
                search_info = json.loads(search_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                dir_match = re.search(r"directory['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", search_info_str)
                pattern_match = re.search(r"pattern['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", search_info_str)
                recursive_match = re.search(r"recursive['\"]?\s*[:=]\s*(true|false)", search_info_str)
                
                if dir_match and pattern_match:
                    search_info = {
                        "directory": dir_match.group(1),
                        "pattern": pattern_match.group(1)
                    }
                    if recursive_match:
                        search_info["recursive"] = recursive_match.group(1).lower() == "true"
                else:
                    return "Error: Invalid input format. Expected JSON with 'directory' and 'pattern'"
            
            if not isinstance(search_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "directory" not in search_info or "pattern" not in search_info:
                return "Error: Input must contain 'directory' and 'pattern'"
            
            directory = search_info["directory"]
            pattern = search_info["pattern"]
            recursive = search_info.get("recursive", False)
            
            # Expand user directory if needed
            expanded_dir = os.path.expanduser(directory)
            
            # Check if directory exists
            if not os.path.exists(expanded_dir):
                return f"Error: Directory '{directory}' does not exist"
            
            if not os.path.isdir(expanded_dir):
                return f"Error: '{directory}' is not a directory"
            
            # Compile the regex pattern
            try:
                regex = re.compile(pattern)
            except re.error:
                # If pattern is not a valid regex, treat it as a literal string
                regex = re.compile(re.escape(pattern))
            
            # Search for the pattern in files
            results = []
            
            def search_in_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        matching_lines = []
                        for i, line in enumerate(file, 1):
                            if regex.search(line):
                                matching_lines.append((i, line.strip()))
                        
                        if matching_lines:
                            return {
                                "file": file_path,
                                "matches": matching_lines
                            }
                except Exception as e:
                    logger.warning(f"Error reading file {file_path}: {str(e)}")
                return None
            
            # Walk through the directory
            if recursive:
                for root, _, files in os.walk(expanded_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        result = search_in_file(file_path)
                        if result:
                            results.append(result)
            else:
                for file in os.listdir(expanded_dir):
                    file_path = os.path.join(expanded_dir, file)
                    if os.path.isfile(file_path):
                        result = search_in_file(file_path)
                        if result:
                            results.append(result)
            
            # Format the results
            if not results:
                return f"No matches found for pattern '{pattern}' in directory '{directory}'"
            
            output = [f"Found {len(results)} files with pattern '{pattern}' in directory '{directory}':"]
            
            for result in results:
                file_path = result["file"]
                matches = result["matches"]
                
                rel_path = os.path.relpath(file_path, expanded_dir)
                output.append(f"\nFile: {rel_path}")
                
                # Limit number of matches displayed per file
                max_matches = 5
                shown_matches = matches[:max_matches]
                
                for line_num, line in shown_matches:
                    output.append(f"  Line {line_num}: {line}")
                
                if len(matches) > max_matches:
                    output.append(f"  ... and {len(matches) - max_matches} more matches")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error searching file content: {str(e)}")
            return f"Error searching file content: {str(e)}"


class AnalyzeFileTool(BaseTool):
    """Tool for analyzing a file and returning metadata."""
    
    name: str = "analyze_file"
    description: str = """
    Analyzes a file and returns metadata such as file size, creation time, modification time, and file type.
    
    Input should be the path of the file to analyze.
    Returns file metadata or an error message.
    
    Example: "documents/report.pdf" or "/home/user/documents/report.pdf"
    """
    
    def _run(self, file_path: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Analyze a file and return metadata."""
        try:
            # Expand user directory if needed
            expanded_path = os.path.expanduser(file_path)
            
            # Check if file exists
            if not os.path.exists(expanded_path):
                return f"Error: File '{file_path}' does not exist"
            
            if not os.path.isfile(expanded_path):
                return f"Error: '{file_path}' is not a file"
            
            # Get file info
            file_stats = os.stat(expanded_path)
            
            # Get file size in readable format
            size_bytes = file_stats.st_size
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB ({size_bytes:,} bytes)"
            elif size_kb >= 1:
                size_str = f"{size_kb:.2f} KB ({size_bytes:,} bytes)"
            else:
                size_str = f"{size_bytes:,} bytes"
            
            # Get file times
            creation_time = datetime.datetime.fromtimestamp(file_stats.st_ctime)
            modification_time = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            access_time = datetime.datetime.fromtimestamp(file_stats.st_atime)
            
            # Get file type
            file_type, encoding = mimetypes.guess_type(expanded_path)
            if not file_type:
                file_type = "Unknown"
            
            # Get file extension
            _, extension = os.path.splitext(expanded_path)
            if extension:
                extension = extension[1:]  # Remove the dot
            else:
                extension = "None"
            
            # Format the output
            output = [
                f"File Analysis for: {file_path}",
                f"Size: {size_str}",
                f"Type: {file_type}",
                f"Extension: {extension}",
                f"Creation Time: {creation_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Last Modified: {modification_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Last Accessed: {access_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Permissions: {oct(file_stats.st_mode)[-3:]}"  # Last 3 digits of octal representation
            ]
            
            # Add more specific info based on file type
            if file_type and "text" in file_type:
                # For text files, show a preview
                try:
                    with open(expanded_path, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = file.readlines()
                        preview_lines = [line.strip() for line in lines[:5]]
                        
                        output.append("\nPreview (first 5 lines):")
                        for i, line in enumerate(preview_lines, 1):
                            output.append(f"  {i}: {line}")
                        
                        if len(lines) > 5:
                            output.append(f"  ... and {len(lines) - 5} more lines")
                except Exception as e:
                    output.append(f"\nCould not read file content: {str(e)}")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            return f"Error analyzing file: {str(e)}"


class ModifyJsonFileTool(BaseTool):
    """Tool for modifying a JSON file by updating or adding fields."""
    
    name: str = "modify_json_file"
    description: str = """
    Modifies a JSON file by updating or adding fields.
    
    Input should be a JSON object with:
    - 'file_path': path of the JSON file to modify
    - 'updates': an object containing the fields to update or add (keys are field names, values are the new values)
    
    Example: {"file_path": "config.json", "updates": {"version": "2.0", "debug": true}}
    
    Returns confirmation or error message.
    """
    
    def _run(self, json_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Modify a JSON file by updating or adding fields."""
        try:
            # Parse the input
            import json
            try:
                json_info = json.loads(json_info_str)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input. Expected a JSON object with 'file_path' and 'updates'"
            
            if not isinstance(json_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "file_path" not in json_info or "updates" not in json_info:
                return "Error: Input must contain 'file_path' and 'updates'"
            
            file_path = json_info["file_path"]
            updates = json_info["updates"]
            
            if not isinstance(updates, dict):
                return "Error: 'updates' must be a dictionary/JSON object"
            
            # Expand user directory if needed
            expanded_path = os.path.expanduser(file_path)
            
            # Check if file exists
            if not os.path.exists(expanded_path):
                return f"Error: File '{file_path}' does not exist"
            
            # Read the current JSON data
            try:
                with open(expanded_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                return f"Error: The file '{file_path}' does not contain valid JSON"
            except Exception as e:
                return f"Error reading file '{file_path}': {str(e)}"
            
            if not isinstance(data, dict):
                return f"Error: The content of '{file_path}' is not a JSON object"
            
            # Create a backup
            backup_path = f"{expanded_path}.bak"
            try:
                with open(backup_path, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=2)
            except Exception as e:
                return f"Error creating backup file: {str(e)}"
            
            # Update the data
            def update_nested(d, updates):
                for k, v in updates.items():
                    if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                        # Recursive update for nested dictionaries
                        update_nested(d[k], v)
                    else:
                        # Direct update for other cases
                        d[k] = v
            
            update_nested(data, updates)
            
            # Write the updated data back to the file
            try:
                with open(expanded_path, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=2)
            except Exception as e:
                return f"Error writing updated data to file: {str(e)}"
            
            # Format the output
            updated_fields = ", ".join(f"'{k}'" for k in updates.keys())
            return f"Successfully updated JSON file '{file_path}'. Updated fields: {updated_fields}."
            
        except Exception as e:
            logger.error(f"Error modifying JSON file: {str(e)}")
            return f"Error modifying JSON file: {str(e)}"