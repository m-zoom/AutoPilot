"""
File Management & Processing Tools

Tools for managing files, directories, and file-related operations on Windows.
"""

import sys

import os
import shutil
import logging
import zipfile
import filecmp
import re
from typing import List, Optional, Dict, Any
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

class ZipArchiveTool(BaseTool):
    """Tool for compressing, extracting, and managing zip archives."""
    
    name: str = "zip_archive"
    description: str = """
    Compresses files into a zip archive, extracts zip archives, or lists contents of zip archives.
    
    Input should be a JSON object with the following structure:
    For compression: {"action": "compress", "source_paths": ["path1", "path2", ...], "destination": "archive.zip"}
    For extraction: {"action": "extract", "source": "archive.zip", "destination": "extract_folder"}
    For listing: {"action": "list", "source": "archive.zip"}
    
    Returns a success message or error.
    
    Example: {"action": "compress", "source_paths": ["C:\\Documents\\file1.txt", "C:\\Documents\\file2.txt"], "destination": "C:\\Documents\\archive.zip"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage zip archives."""
        try:
            import json
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if action == "compress":
                source_paths = params.get("source_paths", [])
                destination = params.get("destination", "")
                
                if not source_paths or not destination:
                    return "Error: Missing source_paths or destination parameter"
                
                # Create the zip file
                with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for source in source_paths:
                        if os.path.isfile(source):
                            # Add individual file
                            zipf.write(source, os.path.basename(source))
                        elif os.path.isdir(source):
                            # Add directory contents
                            for root, _, files in os.walk(source):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    # Save the relative path within the zip
                                    arcname = os.path.relpath(file_path, os.path.dirname(source))
                                    zipf.write(file_path, arcname)
                
                return f"Successfully compressed files to {destination}"
            
            elif action == "extract":
                source = params.get("source", "")
                destination = params.get("destination", "")
                
                if not source or not destination:
                    return "Error: Missing source or destination parameter"
                
                # Create destination directory if it doesn't exist
                os.makedirs(destination, exist_ok=True)
                
                # Extract the zip file
                with zipfile.ZipFile(source, 'r') as zipf:
                    zipf.extractall(destination)
                
                return f"Successfully extracted {source} to {destination}"
            
            elif action == "list":
                source = params.get("source", "")
                
                if not source:
                    return "Error: Missing source parameter"
                
                # List the contents of the zip file
                with zipfile.ZipFile(source, 'r') as zipf:
                    file_list = zipf.namelist()
                
                return f"Contents of {source}:\n" + "\n".join(file_list)
            
            else:
                return f"Error: Unknown action '{action}'. Use 'compress', 'extract', or 'list'."
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except zipfile.BadZipFile:
            return f"Error: {params.get('source', 'File')} is not a valid zip file"
        except FileNotFoundError as e:
            return f"Error: File not found: {str(e)}"
        except Exception as e:
            logger.error(f"Error in zip operation: {str(e)}")
            return f"Error in zip operation: {str(e)}"


class FilePermissionsTool(BaseTool):
    """Tool for viewing and modifying file/folder permissions."""
    
    name: str = "file_permissions"
    description: str = """
    Views or modifies file and folder permissions on Windows.
    
    Input should be a JSON object with the following structure:
    For viewing: {"action": "view", "path": "file_or_folder_path"}
    For modifying: {"action": "modify", "path": "file_or_folder_path", "permissions": {"read": true/false, "write": true/false, "execute": true/false}}
    
    Returns the current permissions or a success message after modification.
    
    Example: {"action": "view", "path": "C:\\Documents\\file.txt"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """View or modify file permissions."""
        try:
            import json
            import stat
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            path = params.get("path", "")
            
            if not path:
                return "Error: Missing path parameter"
                
            if not os.path.exists(path):
                return f"Error: Path does not exist: {path}"
            
            if action == "view":
                # Use icacls command to get Windows permissions
                result = subprocess.run(["icacls", path], capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Error getting permissions: {result.stderr}"
                    
                return f"Permissions for {path}:\n{result.stdout}"
                
            elif action == "modify":
                permissions = params.get("permissions", {})
                
                if not permissions:
                    return "Error: Missing permissions parameter"
                
                # Map permissions to icacls format
                icacls_commands = []
                
                if "read" in permissions:
                    if permissions["read"]:
                        icacls_commands.append(f'icacls "{path}" /grant:r Everyone:(R)')
                    else:
                        icacls_commands.append(f'icacls "{path}" /deny Everyone:(R)')
                
                if "write" in permissions:
                    if permissions["write"]:
                        icacls_commands.append(f'icacls "{path}" /grant:r Everyone:(W)')
                    else:
                        icacls_commands.append(f'icacls "{path}" /deny Everyone:(W)')
                
                if "execute" in permissions:
                    if permissions["execute"]:
                        icacls_commands.append(f'icacls "{path}" /grant:r Everyone:(X)')
                    else:
                        icacls_commands.append(f'icacls "{path}" /deny Everyone:(X)')
                
                # Execute each icacls command
                results = []
                for cmd in icacls_commands:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        results.append(f"Error: {result.stderr}")
                    else:
                        results.append("Success")
                
                # Get updated permissions
                result = subprocess.run(["icacls", path], capture_output=True, text=True)
                
                if result.returncode != 0:
                    return f"Modified permissions but failed to retrieve new permissions: {result.stderr}"
                
                return f"Updated permissions for {path}:\n{result.stdout}"
            
            else:
                return f"Error: Unknown action '{action}'. Use 'view' or 'modify'."
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in file permissions operation: {str(e)}")
            return f"Error in file permissions operation: {str(e)}"


class FileDiffTool(BaseTool):
    """Tool for comparing contents of two files."""
    
    name: str = "file_diff"
    description: str = """
    Compares the contents of two files and reports differences.
    
    Input should be a JSON object with the following structure:
    {"file1": "path_to_file1", "file2": "path_to_file2"}
    
    Returns a report of the differences between the files or confirms they are identical.
    
    Example: {"file1": "C:\\Documents\\file1.txt", "file2": "C:\\Documents\\file2.txt"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Compare contents of two files."""
        try:
            import json
            import difflib
            
            params = json.loads(input_str)
            
            file1 = params.get("file1", "")
            file2 = params.get("file2", "")
            
            if not file1 or not file2:
                return "Error: Missing file1 or file2 parameter"
                
            if not os.path.exists(file1):
                return f"Error: File does not exist: {file1}"
                
            if not os.path.exists(file2):
                return f"Error: File does not exist: {file2}"
            
            # Quick check if files are identical
            if filecmp.cmp(file1, file2, shallow=False):
                return f"Files {file1} and {file2} are identical."
            
            # Get file contents
            with open(file1, 'r', encoding='utf-8', errors='replace') as f:
                file1_lines = f.readlines()
            
            with open(file2, 'r', encoding='utf-8', errors='replace') as f:
                file2_lines = f.readlines()
            
            # Generate diff
            diff = difflib.unified_diff(
                file1_lines, 
                file2_lines,
                fromfile=file1,
                tofile=file2,
                lineterm=''
            )
            
            diff_output = '\n'.join(list(diff))
            
            if diff_output:
                return f"Differences between {file1} and {file2}:\n\n{diff_output}"
            else:
                return f"Files {file1} and {file2} have the same content but metadata may differ."
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except UnicodeDecodeError:
            return "Error: One or both files contain binary data that cannot be compared as text"
        except Exception as e:
            logger.error(f"Error comparing files: {str(e)}")
            return f"Error comparing files: {str(e)}"


class FileTypeSortingTool(BaseTool):
    """Tool for organizing files by type into folders."""
    
    name: str = "file_type_sorting"
    description: str = """
    Organizes files in a directory by their file type, moving them into type-specific subfolders.
    
    Input should be a JSON object with the following structure:
    {"source_dir": "path_to_directory", "recursive": true/false}
    
    Returns a report of how many files were organized into which folders.
    
    Example: {"source_dir": "C:\\Downloads", "recursive": false}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Organize files by type into folders."""
        try:
            import json
            
            params = json.loads(input_str)
            
            source_dir = params.get("source_dir", "")
            recursive = params.get("recursive", False)
            
            if not source_dir:
                return "Error: Missing source_dir parameter"
                
            if not os.path.exists(source_dir):
                return f"Error: Directory does not exist: {source_dir}"
                
            if not os.path.isdir(source_dir):
                return f"Error: {source_dir} is not a directory"
            
            # Dictionary to track file counts by type
            file_counts = {}
            
            # Collect files to process
            files_to_process = []
            
            if recursive:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        files_to_process.append(os.path.join(root, file))
            else:
                # Just get files from the top directory
                for item in os.listdir(source_dir):
                    item_path = os.path.join(source_dir, item)
                    if os.path.isfile(item_path):
                        files_to_process.append(item_path)
            
            # Process each file
            for file_path in files_to_process:
                # Get the file extension (lowercase)
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                
                if not ext:
                    ext = "no_extension"
                else:
                    # Remove the dot
                    ext = ext[1:]
                
                # Create the type folder if it doesn't exist
                type_folder = os.path.join(source_dir, ext)
                os.makedirs(type_folder, exist_ok=True)
                
                # Get the filename
                filename = os.path.basename(file_path)
                
                # New path for the file
                new_path = os.path.join(type_folder, filename)
                
                # Handle file name conflicts
                if os.path.exists(new_path):
                    base, extension = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(new_path):
                        new_filename = f"{base}_{counter}{extension}"
                        new_path = os.path.join(type_folder, new_filename)
                        counter += 1
                
                # Move the file
                shutil.move(file_path, new_path)
                
                # Update count
                if ext in file_counts:
                    file_counts[ext] += 1
                else:
                    file_counts[ext] = 1
            
            # Generate report
            if not file_counts:
                return f"No files were found to organize in {source_dir}"
                
            report = [f"Organized {sum(file_counts.values())} files in {source_dir} by type:"]
            
            for ext, count in sorted(file_counts.items()):
                report.append(f"  - {ext}: {count} file(s)")
                
            return "\n".join(report)
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except PermissionError:
            return "Error: Permission denied while moving files"
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            return f"Error organizing files: {str(e)}"


class BatchRenameFilesTool(BaseTool):
    """Tool for renaming multiple files using patterns."""
    
    name: str = "batch_rename_files"
    description: str = """
    Renames multiple files in a directory using search/replace patterns or templates.
    
    Input should be a JSON object with the following structure:
    For search/replace: {"directory": "path_to_dir", "pattern": "search_pattern", "replacement": "replacement_text", "use_regex": true/false}
    For numbered sequence: {"directory": "path_to_dir", "template": "prefix_{num}_suffix", "start_num": 1, "padding": 3}
    
    Returns a report of the files that were renamed.
    
    Example search/replace: {"directory": "C:\\Photos", "pattern": "IMG_", "replacement": "Vacation_", "use_regex": false}
    Example numbered sequence: {"directory": "C:\\Photos", "template": "Photo_{num}", "start_num": 1, "padding": 3}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Batch rename files using patterns."""
        try:
            import json
            
            params = json.loads(input_str)
            
            directory = params.get("directory", "")
            
            if not directory:
                return "Error: Missing directory parameter"
                
            if not os.path.exists(directory):
                return f"Error: Directory does not exist: {directory}"
                
            if not os.path.isdir(directory):
                return f"Error: {directory} is not a directory"
            
            # Check if this is a search/replace operation or a template operation
            pattern = params.get("pattern")
            template = params.get("template")
            
            if pattern is not None:
                # This is a search/replace operation
                replacement = params.get("replacement", "")
                use_regex = params.get("use_regex", False)
                
                # Get all files in the directory
                files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
                
                renamed_files = []
                
                for filename in files:
                    # Get the new filename
                    if use_regex:
                        # Use regex for replacement
                        new_filename = re.sub(pattern, replacement, filename)
                    else:
                        # Use simple string replacement
                        new_filename = filename.replace(pattern, replacement)
                    
                    # Skip if no change
                    if new_filename == filename:
                        continue
                    
                    # Get the full paths
                    old_path = os.path.join(directory, filename)
                    new_path = os.path.join(directory, new_filename)
                    
                    # Handle file name conflicts
                    if os.path.exists(new_path):
                        base, extension = os.path.splitext(new_filename)
                        counter = 1
                        while os.path.exists(new_path):
                            conflict_filename = f"{base}_{counter}{extension}"
                            new_path = os.path.join(directory, conflict_filename)
                            counter += 1
                        new_filename = os.path.basename(new_path)
                    
                    # Rename the file
                    os.rename(old_path, new_path)
                    renamed_files.append((filename, new_filename))
                
                # Generate report
                if not renamed_files:
                    return f"No files were renamed in {directory}"
                    
                report = [f"Renamed {len(renamed_files)} files in {directory}:"]
                
                for old_name, new_name in renamed_files:
                    report.append(f"  - {old_name} → {new_name}")
                    
                return "\n".join(report)
                
            elif template is not None:
                # This is a template operation
                start_num = params.get("start_num", 1)
                padding = params.get("padding", 3)
                
                # Get all files in the directory
                files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
                
                # Sort files (usually by name, but could be by other attributes if needed)
                files.sort()
                
                renamed_files = []
                counter = start_num
                
                for filename in files:
                    # Get file extension
                    _, extension = os.path.splitext(filename)
                    
                    # Format the number with padding
                    num_str = str(counter).zfill(padding)
                    
                    # Replace {num} in template with the formatted number
                    new_filename = template.replace("{num}", num_str)
                    
                    # Add extension if template doesn't include it
                    if not new_filename.endswith(extension):
                        new_filename += extension
                    
                    # Get the full paths
                    old_path = os.path.join(directory, filename)
                    new_path = os.path.join(directory, new_filename)
                    
                    # Handle file name conflicts
                    if os.path.exists(new_path) and old_path != new_path:
                        base, ext = os.path.splitext(new_filename)
                        conflict_counter = 1
                        while os.path.exists(new_path):
                            conflict_filename = f"{base}_{conflict_counter}{ext}"
                            new_path = os.path.join(directory, conflict_filename)
                            conflict_counter += 1
                        new_filename = os.path.basename(new_path)
                    
                    # Rename the file
                    os.rename(old_path, new_path)
                    renamed_files.append((filename, new_filename))
                    
                    # Increment the counter
                    counter += 1
                
                # Generate report
                if not renamed_files:
                    return f"No files were renamed in {directory}"
                    
                report = [f"Renamed {len(renamed_files)} files in {directory} using template '{template}':"]
                
                for old_name, new_name in renamed_files:
                    report.append(f"  - {old_name} → {new_name}")
                    
                return "\n".join(report)
            
            else:
                return "Error: Missing pattern or template parameter"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except PermissionError:
            return "Error: Permission denied while renaming files"
        except Exception as e:
            logger.error(f"Error renaming files: {str(e)}")
            return f"Error renaming files: {str(e)}"
