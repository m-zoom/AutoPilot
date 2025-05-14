"""
Tools for the AI agent to interact with the terminal.
Includes operations for executing shell commands.
"""

import sys

import os
import subprocess
import logging
from typing import Optional
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

class ExecuteShellCommandTool(BaseTool):
    """Tool for executing shell commands."""
    
    name: str = "execute_shell_command"
    description: str = """
    Executes a shell command on the system and returns the output.
    Use with caution as this has full access to the system.
    
    Input should be the shell command to execute.
    Returns the command output or error message.
    
    Example: "ls -la" or "echo Hello World"
    """
    
    def _run(self, command: str, run_manager: Optional[CallbackManagerForToolRun] = None, **kwargs) -> str:
        """Execute a shell command."""
        try:
            logger.info(f"Executing shell command: {command}")
            
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero return code
            )
            
            # Format the output
            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
                
            if result.returncode != 0:
                output.append(f"Command exited with return code: {result.returncode}")
                
            if not output:
                return "Command executed successfully with no output."
            else:
                return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error executing shell command: {str(e)}")
            return f"Error executing shell command: {str(e)}"