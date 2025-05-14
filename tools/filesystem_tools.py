"""
Tools for the AI agent to interact with the file system.
Includes operations for creating, reading, writing, renaming, moving and deleting files,
as well as listing directory contents.
"""

import sys

import os
import json
import shutil
import logging
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

class CreateFileTool(BaseTool):
    """Tool for creating files."""
    
    name: str = "create_file"
    description: str = """
    Creates a file with specified content at the current directory or at a specified path.
    
    Input should be a JSON object with:
    - 'file_path': path where the file should be created (can be relative to current directory)
    - 'content': the content to write to the file
    
    Example: {"file_path": "example.txt", "content": "Hello, world!"}
    
    Returns confirmation or error message.
    """
    
    def _run(self, file_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Create a file with the specified content."""
        try:
            # Parse the input as a dictionary
            import json
            try:
                file_info = json.loads(file_info_str)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract file_path and content from the string
                import re
                path_match = re.search(r"file_path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                content_match = re.search(r"content['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                
                if path_match and content_match:
                    file_info = {
                        "file_path": path_match.group(1),
                        "content": content_match.group(1)
                    }
                else:
                    return "Error: Invalid input format. Expected JSON with 'file_path' and 'content'"
            
            if not isinstance(file_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "file_path" not in file_info or "content" not in file_info:
                return "Error: Input must contain 'file_path' and 'content'"
            
            file_path = file_info["file_path"]
            content = file_info["content"]
            
            # Expand user directory if needed
            expanded_path = os.path.expanduser(file_path)
            
            # Create parent directories if they don't exist
            directory = os.path.dirname(expanded_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # Write content to file
            with open(expanded_path, 'w') as file:
                file.write(content)
            
            abs_path = os.path.abspath(expanded_path)
            return f"Successfully created file at: {abs_path}"
            
        except Exception as e:
            logger.error(f"Error creating file: {str(e)}")
            return f"Error creating file: {str(e)}"

class ReadFileTool(BaseTool):
    """Tool for reading file content."""
    
    name: str = "read_file"
    description: str = """
    Reads the content of a file and returns it.
    
    Input should be the path to the file (absolute or relative to current directory).
    Returns the content of the file or error message.
    
    Example: "path/to/file.txt" or "C:\\Users\\username\\Documents\\file.txt"
    """
    
    def _run(self, file_path: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Read the content of a file."""
        try:
            # Expand user directory if needed
            expanded_path = os.path.expanduser(file_path)
            
            # Check if file exists
            if not os.path.exists(expanded_path):
                return f"Error: File '{file_path}' does not exist"
            
            if not os.path.isfile(expanded_path):
                return f"Error: '{file_path}' is not a file"
            
            # Read file content
            with open(expanded_path, 'r') as file:
                content = file.read()
            
            return f"Content of {file_path}:\n\n{content}"
            
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' appears to be a binary file and cannot be read as text"
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return f"Error reading file: {str(e)}"

class WriteFileTool(BaseTool):
    """Tool for writing content to existing files."""
    
    name: str = "write_file"
    description: str = """
    Writes content to an existing file, overwriting its current content.
    
    Input should be a JSON object with:
    - 'file_path': path to the existing file (absolute or relative to current directory)
    - 'content': the new content to write
    - 'append' (optional): boolean indicating whether to append content (default is false)
    
    Example: {"file_path": "example.txt", "content": "Updated content", "append": false}
    
    Returns confirmation or error message.
    """
    
    def _run(self, file_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Write content to an existing file."""
        try:
            # Parse the input
            try:
                file_info = json.loads(file_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                path_match = re.search(r"file_path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                content_match = re.search(r"content['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                append_match = re.search(r"append['\"]?\s*[:=]\s*(true|false)", file_info_str)
                
                if path_match and content_match:
                    file_info = {
                        "file_path": path_match.group(1),
                        "content": content_match.group(1)
                    }
                    if append_match:
                        file_info["append"] = append_match.group(1).lower() == "true"
                else:
                    return "Error: Invalid input format. Expected JSON with 'file_path' and 'content'"
            
            if not isinstance(file_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "file_path" not in file_info or "content" not in file_info:
                return "Error: Input must contain 'file_path' and 'content'"
            
            file_path = file_info["file_path"]
            content = file_info["content"]
            append = file_info.get("append", False)
            
            # Expand user directory if needed
            expanded_path = os.path.expanduser(file_path)
            
            # Check if file exists
            if not os.path.exists(expanded_path):
                return f"Error: File '{file_path}' does not exist"
            
            if not os.path.isfile(expanded_path):
                return f"Error: '{file_path}' is not a file"
            
            # Write or append content to file
            mode = 'a' if append else 'w'
            with open(expanded_path, mode) as file:
                file.write(content)
            
            action = "appended to" if append else "updated"
            return f"Successfully {action} file at: {file_path}"
            
        except Exception as e:
            logger.error(f"Error writing to file: {str(e)}")
            return f"Error writing to file: {str(e)}"

class RenameFileTool(BaseTool):
    """Tool for renaming files and folders."""
    
    name: str = "rename_file"
    description: str = """
    Renames a file or folder.
    
    Input should be a JSON object with:
    - 'source_path': path to the file or folder to rename
    - 'new_name': the new name (not the full path, just the name)
    
    Example: {"source_path": "old_name.txt", "new_name": "new_name.txt"}
    
    Returns confirmation or error message.
    """
    
    def _run(self, file_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Rename a file or folder."""
        try:
            # Parse the input
            try:
                file_info = json.loads(file_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                source_match = re.search(r"source_path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                new_match = re.search(r"new_name['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                
                if source_match and new_match:
                    file_info = {
                        "source_path": source_match.group(1),
                        "new_name": new_match.group(1)
                    }
                else:
                    return "Error: Invalid input format. Expected JSON with 'source_path' and 'new_name'"
            
            if not isinstance(file_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "source_path" not in file_info or "new_name" not in file_info:
                return "Error: Input must contain 'source_path' and 'new_name'"
            
            source_path = file_info["source_path"]
            new_name = file_info["new_name"]
            
            # Expand user directory if needed
            expanded_source = os.path.expanduser(source_path)
            
            # Check if source exists
            if not os.path.exists(expanded_source):
                return f"Error: '{source_path}' does not exist"
            
            # Get directory of source
            source_dir = os.path.dirname(expanded_source)
            if not source_dir:  # If in current directory
                source_dir = os.getcwd()
                
            # Create the new path with the new name
            new_path = os.path.join(source_dir, new_name)
            
            # Check if destination already exists
            if os.path.exists(new_path):
                return f"Error: '{new_name}' already exists in the directory"
            
            # Rename the file or folder
            os.rename(expanded_source, new_path)
            
            file_type = "folder" if os.path.isdir(new_path) else "file"
            return f"Successfully renamed {file_type} from '{source_path}' to '{new_name}'"
            
        except Exception as e:
            logger.error(f"Error renaming file/folder: {str(e)}")
            return f"Error renaming file/folder: {str(e)}"

class MoveFileTool(BaseTool):
    """Tool for moving files and folders."""
    
    name: str = "move_file"
    description: str = """
    Moves a file or folder to a different location.
    
    Input should be a JSON object with:
    - 'source_path': path to the file or folder to move
    - 'destination_path': path where the file or folder should be moved to
    
    Example: {"source_path": "file.txt", "destination_path": "folder/file.txt"}
    
    Returns confirmation or error message.
    """
    
    def _run(self, file_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Move a file or folder."""
        try:
            # Parse the input
            try:
                file_info = json.loads(file_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                source_match = re.search(r"source_path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                dest_match = re.search(r"destination_path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                
                if source_match and dest_match:
                    file_info = {
                        "source_path": source_match.group(1),
                        "destination_path": dest_match.group(1)
                    }
                else:
                    return "Error: Invalid input format. Expected JSON with 'source_path' and 'destination_path'"
            
            if not isinstance(file_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "source_path" not in file_info or "destination_path" not in file_info:
                return "Error: Input must contain 'source_path' and 'destination_path'"
            
            source_path = file_info["source_path"]
            destination_path = file_info["destination_path"]
            
            # Expand user directory if needed
            expanded_source = os.path.expanduser(source_path)
            expanded_destination = os.path.expanduser(destination_path)
            
            # Check if source exists
            if not os.path.exists(expanded_source):
                return f"Error: '{source_path}' does not exist"
            
            # Create destination directory if it doesn't exist (for nested moves)
            dest_dir = os.path.dirname(expanded_destination)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            # Move the file or folder
            shutil.move(expanded_source, expanded_destination)
            
            file_type = "folder" if os.path.isdir(expanded_destination) else "file"
            return f"Successfully moved {file_type} from '{source_path}' to '{destination_path}'"
            
        except Exception as e:
            logger.error(f"Error moving file/folder: {str(e)}")
            return f"Error moving file/folder: {str(e)}"

class DeleteFileTool(BaseTool):
    """Tool for deleting files and folders."""
    
    name: str = "delete_file"
    description: str = """
    Deletes a file or folder.
    
    Input should be a JSON object with:
    - 'path': path to the file or folder to delete
    - 'recursive' (optional): boolean indicating whether to recursively delete folders (default is false)
    
    Example: {"path": "folder/to/delete", "recursive": true}
    
    Returns confirmation or error message.
    """
    
    def _run(self, file_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Delete a file or folder."""
        try:
            # Parse the input
            try:
                file_info = json.loads(file_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                path_match = re.search(r"path['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", file_info_str)
                recursive_match = re.search(r"recursive['\"]?\s*[:=]\s*(true|false)", file_info_str)
                
                if path_match:
                    file_info = {
                        "path": path_match.group(1)
                    }
                    if recursive_match:
                        file_info["recursive"] = recursive_match.group(1).lower() == "true"
                else:
                    return "Error: Invalid input format. Expected JSON with 'path'"
            
            if not isinstance(file_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "path" not in file_info:
                return "Error: Input must contain 'path'"
            
            path = file_info["path"]
            recursive = file_info.get("recursive", False)
            
            # Expand user directory if needed
            expanded_path = os.path.expanduser(path)
            
            # Check if path exists
            if not os.path.exists(expanded_path):
                return f"Error: '{path}' does not exist"
            
            # Delete file or folder
            if os.path.isfile(expanded_path):
                os.remove(expanded_path)
                return f"Successfully deleted file: '{path}'"
            else:
                if recursive:
                    shutil.rmtree(expanded_path)
                    return f"Successfully deleted folder and its contents: '{path}'"
                else:
                    try:
                        os.rmdir(expanded_path)
                        return f"Successfully deleted empty folder: '{path}'"
                    except OSError:
                        return f"Error: Folder '{path}' is not empty. Use recursive=true to delete it and its contents."
            
        except Exception as e:
            logger.error(f"Error deleting file/folder: {str(e)}")
            return f"Error deleting file/folder: {str(e)}"

class ListDirectoryTool(BaseTool):
    """Tool for listing directory contents."""
    
    name: str = "list_directory"
    description: str = """
    Lists the contents of a directory.
    
    Input should be the path to the directory (absolute or relative). If no path is provided,
    it will list the contents of the current directory.
    
    Returns a list of files and folders in the directory or error message.
    
    Example: "path/to/directory" or leave empty for current directory
    """
    
    def _run(self, directory_path: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """List the contents of a directory."""
        try:
            # If no path provided, use current directory
            if not directory_path.strip():
                directory_path = os.getcwd()
            
            # Expand user directory if needed
            expanded_path = os.path.expanduser(directory_path)
            
            # Check if directory exists
            if not os.path.exists(expanded_path):
                return f"Error: Directory '{directory_path}' does not exist"
            
            if not os.path.isdir(expanded_path):
                return f"Error: '{directory_path}' is not a directory"
            
            # List directory contents
            contents = os.listdir(expanded_path)
            
            # Separate files and directories
            directories = []
            files = []
            
            for item in contents:
                item_path = os.path.join(expanded_path, item)
                if os.path.isdir(item_path):
                    directories.append(f"{item}/")
                else:
                    files.append(item)
            
            # Sort alphabetically
            directories.sort()
            files.sort()
            
            # Format the output
            output = f"Contents of '{directory_path}':\n\n"
            
            if directories:
                output += "Directories:\n"
                for d in directories:
                    output += f"- {d}\n"
                output += "\n"
            
            if files:
                output += "Files:\n"
                for f in files:
                    output += f"- {f}\n"
            
            if not directories and not files:
                output += "Directory is empty."
            
            return output
            
        except Exception as e:
            logger.error(f"Error listing directory: {str(e)}")
            return f"Error listing directory: {str(e)}"


class BulkMoveFilesTool(BaseTool):
    """Tool for moving multiple files between directories."""
    
    name: str = "bulk_move_files"
    description: str = """
    Moves multiple files from one directory to another.
    
    Input should be a JSON object with:
    - 'source_directory': Directory containing the files to move
    - 'destination_directory': Directory where files should be moved to
    - 'file_pattern' (optional): Pattern to match files (e.g., "*.txt" for all text files)
    - 'file_list' (optional): List of specific filenames to move from the source directory
    
    Note: Either 'file_pattern' or 'file_list' must be provided.
    
    Example: {"source_directory": "downloads", "destination_directory": "documents", "file_pattern": "*.pdf"}
    Example: {"source_directory": "temp", "destination_directory": "archive", "file_list": ["report1.xlsx", "report2.xlsx"]}
    
    Returns confirmation of successful moves or error message.
    """
    
    def _run(self, move_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Move multiple files between directories."""
        try:
            # Parse the input
            try:
                move_info = json.loads(move_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text if not valid JSON
                import re
                src_dir_match = re.search(r"source_directory['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", move_info_str)
                dest_dir_match = re.search(r"destination_directory['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", move_info_str)
                pattern_match = re.search(r"file_pattern['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", move_info_str)
                
                # Simple extraction of file_list if present (this is basic and might not work for complex lists)
                file_list_match = re.search(r"file_list['\"]?\s*[:=]\s*\[(.*?)\]", move_info_str)
                
                if src_dir_match and dest_dir_match and (pattern_match or file_list_match):
                    move_info = {
                        "source_directory": src_dir_match.group(1),
                        "destination_directory": dest_dir_match.group(1)
                    }
                    
                    if pattern_match:
                        move_info["file_pattern"] = pattern_match.group(1)
                    
                    if file_list_match:
                        # Very basic parsing of the list items
                        file_list_str = file_list_match.group(1)
                        file_list = [item.strip().strip('"\'') for item in file_list_str.split(',')]
                        move_info["file_list"] = file_list
                else:
                    return "Error: Invalid input format. Expected JSON with 'source_directory', 'destination_directory', and either 'file_pattern' or 'file_list'"
            
            if not isinstance(move_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            # Validate required fields
            if "source_directory" not in move_info or "destination_directory" not in move_info:
                return "Error: Input must contain 'source_directory' and 'destination_directory'"
            
            if "file_pattern" not in move_info and "file_list" not in move_info:
                return "Error: Input must contain either 'file_pattern' or 'file_list'"
            
            source_directory = move_info["source_directory"]
            destination_directory = move_info["destination_directory"]
            file_pattern = move_info.get("file_pattern", None)
            file_list = move_info.get("file_list", None)
            
            # Expand user directories if needed
            expanded_source = os.path.expanduser(source_directory)
            expanded_destination = os.path.expanduser(destination_directory)
            
            # Check if source directory exists
            if not os.path.exists(expanded_source):
                return f"Error: Source directory '{source_directory}' does not exist"
            
            if not os.path.isdir(expanded_source):
                return f"Error: '{source_directory}' is not a directory"
            
            # Create destination directory if it doesn't exist
            if not os.path.exists(expanded_destination):
                os.makedirs(expanded_destination)
            elif not os.path.isdir(expanded_destination):
                return f"Error: Destination '{destination_directory}' exists but is not a directory"
            
            # Get the list of files to move
            files_to_move = []
            
            if file_pattern:
                import glob
                # Use glob to match files with the pattern
                pattern_path = os.path.join(expanded_source, file_pattern)
                matched_files = glob.glob(pattern_path)
                
                # Only include files (not directories)
                files_to_move = [f for f in matched_files if os.path.isfile(f)]
                
                # Extract just the filenames to display in the results
                filenames = [os.path.basename(f) for f in files_to_move]
                
            elif file_list:
                # Verify each file exists
                for filename in file_list:
                    file_path = os.path.join(expanded_source, filename)
                    if os.path.isfile(file_path):
                        files_to_move.append(file_path)
                    else:
                        return f"Error: File '{filename}' not found in '{source_directory}'"
                
                filenames = file_list
            
            if not files_to_move:
                if file_pattern:
                    return f"No files matching pattern '{file_pattern}' found in '{source_directory}'"
                else:
                    return f"No files from the provided list found in '{source_directory}'"
            
            # Move each file
            moved_files = []
            for source_file in files_to_move:
                filename = os.path.basename(source_file)
                destination_file = os.path.join(expanded_destination, filename)
                
                # Check if destination file already exists
                if os.path.exists(destination_file):
                    return f"Error: File '{filename}' already exists in destination directory"
                
                # Move the file
                shutil.move(source_file, destination_file)
                moved_files.append(filename)
            
            # Format the result message
            if len(moved_files) == 1:
                return f"Successfully moved file '{moved_files[0]}' from '{source_directory}' to '{destination_directory}'"
            else:
                moved_files_str = "', '".join(moved_files)
                return f"Successfully moved {len(moved_files)} files from '{source_directory}' to '{destination_directory}':\n- '{moved_files_str}'"
            
        except Exception as e:
            logger.error(f"Error in bulk file move operation: {str(e)}")
            return f"Error in bulk file move operation: {str(e)}"
