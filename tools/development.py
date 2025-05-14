"""
Development Tools

Tools for software development operations including Git, package management,
code linting, and build/compile processes.
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

class GitOperationsTool(BaseTool):
    """Tool for basic git commands."""
    
    name: str = "git_operations"
    description: str = """
    Performs basic Git operations like pull, push, commit, clone, etc.
    
    Input should be a JSON object with the following structure:
    For pull: {"action": "pull", "repo_path": "C:\\path\\to\\repo"}
    For push: {"action": "push", "repo_path": "C:\\path\\to\\repo", "remote": "origin", "branch": "main"}
    For commit: {"action": "commit", "repo_path": "C:\\path\\to\\repo", "message": "Commit message"}
    For clone: {"action": "clone", "url": "https://github.com/user/repo.git", "destination": "C:\\path\\to\\destination"}
    For status: {"action": "status", "repo_path": "C:\\path\\to\\repo"}
    
    Returns the command output or an error message.
    
    Example: {"action": "status", "repo_path": "C:\\Projects\\myrepo"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute Git commands."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            
            if not action:
                return "Error: Missing action parameter"
            
            if action in ["pull", "push", "commit", "status", "add"]:
                # These commands require a repo path
                repo_path = params.get("repo_path", "")
                
                if not repo_path:
                    return "Error: Missing repo_path parameter"
                
                if not os.path.exists(repo_path):
                    return f"Error: Repository path does not exist: {repo_path}"
                
                # Change to repo directory for the command
                current_dir = os.getcwd()
                os.chdir(repo_path)
                
                try:
                    if action == "pull":
                        cmd = ["git", "pull"]
                    elif action == "push":
                        remote = params.get("remote", "origin")
                        branch = params.get("branch", "")
                        
                        cmd = ["git", "push", remote]
                        if branch:
                            cmd.append(branch)
                    elif action == "commit":
                        message = params.get("message", "")
                        
                        if not message:
                            return "Error: Missing commit message parameter"
                        
                        cmd = ["git", "commit", "-m", message]
                    elif action == "status":
                        cmd = ["git", "status"]
                    elif action == "add":
                        files = params.get("files", ".")
                        
                        if isinstance(files, list):
                            cmd = ["git", "add"] + files
                        else:
                            cmd = ["git", "add", files]
                    
                    # Execute the command
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0 and result.stderr:
                        return f"Git error: {result.stderr}"
                    
                    output = result.stdout or result.stderr
                    
                    return f"Git {action} completed:\n{output}"
                
                finally:
                    # Restore original directory
                    os.chdir(current_dir)
            
            elif action == "clone":
                # Clone a repository
                url = params.get("url", "")
                destination = params.get("destination", "")
                
                if not url:
                    return "Error: Missing repository URL parameter"
                
                cmd = ["git", "clone", url]
                
                if destination:
                    # Ensure destination directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
                    cmd.append(destination)
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0 and result.stderr:
                        return f"Git clone error: {result.stderr}"
                    
                    output = result.stdout or result.stderr
                    
                    return f"Git clone completed:\n{output}"
                
                except subprocess.SubprocessError as e:
                    return f"Error executing git clone command: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: pull, push, commit, clone, status, add"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in Git operations: {str(e)}")
            return f"Error in Git operations: {str(e)}"


class PackageManagerTool(BaseTool):
    """Tool for installing and updating software packages."""
    
    name: str = "package_manager"
    description: str = """
    Installs, updates, and manages software packages using pip, npm, or Windows package managers.
    
    Input should be a JSON object with the following structure:
    For pip: {"manager": "pip", "action": "install/uninstall/list", "package": "package_name", "version": "version_spec"}
    For npm: {"manager": "npm", "action": "install/uninstall/list", "package": "package_name", "global": true/false}
    For chocolatey: {"manager": "choco", "action": "install/uninstall/list", "package": "package_name"}
    
    Returns the command output or an error message.
    
    Example: {"manager": "pip", "action": "install", "package": "requests"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Manage software packages."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            manager = params.get("manager", "").lower()
            action = params.get("action", "").lower()
            
            if not manager:
                return "Error: Missing package manager parameter"
                
            if not action:
                return "Error: Missing action parameter"
            
            # Validate manager
            valid_managers = ["pip", "npm", "choco"]
            if manager not in valid_managers:
                return f"Error: Unsupported package manager '{manager}'. Supported managers are: {', '.join(valid_managers)}"
            
            # Validate action
            valid_actions = ["install", "uninstall", "list", "update", "search"]
            if action not in valid_actions:
                return f"Error: Unsupported action '{action}'. Supported actions are: {', '.join(valid_actions)}"
            
            # Check if action requires a package
            if action in ["install", "uninstall", "update", "search"] and not params.get("package"):
                return f"Error: Missing package parameter for {action} action"
            
            # Build and execute the command based on the package manager
            if manager == "pip":
                return self._pip_command(action, params)
            elif manager == "npm":
                return self._npm_command(action, params)
            elif manager == "choco":
                return self._choco_command(action, params)
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in package management: {str(e)}")
            return f"Error in package management: {str(e)}"
    
    def _pip_command(self, action: str, params: Dict[str, Any]) -> str:
        """Execute pip commands."""
        try:
            package = params.get("package", "")
            version = params.get("version", "")
            
            if action == "install":
                cmd = ["pip", "install"]
                
                if version:
                    cmd.append(f"{package}=={version}")
                else:
                    cmd.append(package)
            
            elif action == "uninstall":
                cmd = ["pip", "uninstall", "-y", package]
            
            elif action == "list":
                cmd = ["pip", "list"]
            
            elif action == "search":
                cmd = ["pip", "search", package]
                # Note: pip search is deprecated in newer versions
                return "Warning: pip search is deprecated in newer versions of pip. Consider using PyPI website instead."
            
            elif action == "update":
                cmd = ["pip", "install", "--upgrade", package]
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Pip error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Pip {action} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing pip command: {str(e)}"
    
    def _npm_command(self, action: str, params: Dict[str, Any]) -> str:
        """Execute npm commands."""
        try:
            package = params.get("package", "")
            is_global = params.get("global", False)
            
            if action == "install":
                cmd = ["npm", "install"]
                
                if is_global:
                    cmd.append("-g")
                
                cmd.append(package)
            
            elif action == "uninstall":
                cmd = ["npm", "uninstall"]
                
                if is_global:
                    cmd.append("-g")
                
                cmd.append(package)
            
            elif action == "list":
                cmd = ["npm", "list"]
                
                if is_global:
                    cmd.append("-g")
                
                # Add depth for shorter output
                cmd.extend(["--depth", "0"])
            
            elif action == "update":
                cmd = ["npm", "update"]
                
                if is_global:
                    cmd.append("-g")
                
                if package:
                    cmd.append(package)
            
            elif action == "search":
                cmd = ["npm", "search", package]
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"NPM error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"NPM {action} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing npm command: {str(e)}"
    
    def _choco_command(self, action: str, params: Dict[str, Any]) -> str:
        """Execute Chocolatey commands."""
        try:
            package = params.get("package", "")
            
            if action == "install":
                cmd = ["choco", "install", package, "-y"]
            
            elif action == "uninstall":
                cmd = ["choco", "uninstall", package, "-y"]
            
            elif action == "list":
                if package:
                    cmd = ["choco", "list", package]
                else:
                    cmd = ["choco", "list"]
            
            elif action == "update":
                if package:
                    cmd = ["choco", "upgrade", package, "-y"]
                else:
                    cmd = ["choco", "upgrade", "all", "-y"]
            
            elif action == "search":
                cmd = ["choco", "search", package]
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Chocolatey error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Chocolatey {action} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing Chocolatey command: {str(e)}"


class CodeLintingTool(BaseTool):
    """Tool for checking code for errors or style issues."""
    
    name: str = "code_linting"
    description: str = """
    Checks code for errors, style issues, and quality problems using various linters.
    
    Input should be a JSON object with the following structure:
    {"language": "python/javascript/csharp", "linter": "pylint/flake8/eslint/jshint/dotnet", "file_path": "path/to/file", "code": "code_content_if_no_file"}
    
    Either file_path or code must be provided.
    
    Returns the linting results or an error message.
    
    Example: {"language": "python", "linter": "pylint", "file_path": "C:\\Projects\\script.py"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Check code for errors and style issues."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            language = params.get("language", "").lower()
            linter = params.get("linter", "").lower()
            file_path = params.get("file_path", "")
            code = params.get("code", "")
            
            if not language:
                return "Error: Missing language parameter"
                
            if not linter:
                # Assign default linter based on language
                if language == "python":
                    linter = "pylint"
                elif language == "javascript":
                    linter = "eslint"
                elif language == "csharp":
                    linter = "dotnet"
                else:
                    return f"Error: No default linter available for language '{language}'. Please specify a linter."
            
            if not file_path and not code:
                return "Error: Either file_path or code must be provided"
            
            # If code is provided but no file, create a temporary file
            temp_file = None
            if code and not file_path:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(language))
                with open(temp_file.name, "w", encoding="utf-8") as f:
                    f.write(code)
                file_path = temp_file.name
            
            try:
                # Execute the appropriate linter
                if language == "python":
                    return self._python_lint(linter, file_path)
                elif language == "javascript":
                    return self._javascript_lint(linter, file_path)
                elif language == "csharp":
                    return self._csharp_lint(linter, file_path)
                else:
                    return f"Error: Unsupported language '{language}'"
            
            finally:
                # Clean up temp file if created
                if temp_file:
                    os.unlink(temp_file.name)
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in code linting: {str(e)}")
            return f"Error in code linting: {str(e)}"
    
    def _get_file_extension(self, language: str) -> str:
        """Get the appropriate file extension for a language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "csharp": ".cs"
        }
        return extensions.get(language, ".txt")
    
    def _python_lint(self, linter: str, file_path: str) -> str:
        """Run Python linters."""
        try:
            if linter == "pylint":
                cmd = ["pylint", file_path]
            elif linter == "flake8":
                cmd = ["flake8", file_path]
            elif linter == "mypy":
                cmd = ["mypy", file_path]
            else:
                return f"Error: Unsupported Python linter '{linter}'. Supported linters are: pylint, flake8, mypy"
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # pylint returns non-zero for warnings/errors, which is normal
            output = result.stdout or result.stderr
            
            if not output.strip():
                return f"No issues found in {file_path} using {linter}"
            
            return f"{linter} results for {file_path}:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing {linter}: {str(e)}"
    
    def _javascript_lint(self, linter: str, file_path: str) -> str:
        """Run JavaScript linters."""
        try:
            if linter == "eslint":
                cmd = ["eslint", file_path]
            elif linter == "jshint":
                cmd = ["jshint", file_path]
            else:
                return f"Error: Unsupported JavaScript linter '{linter}'. Supported linters are: eslint, jshint"
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            output = result.stdout or result.stderr
            
            if not output.strip():
                return f"No issues found in {file_path} using {linter}"
            
            return f"{linter} results for {file_path}:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing {linter}: {str(e)}"
    
    def _csharp_lint(self, linter: str, file_path: str) -> str:
        """Run C# linters."""
        try:
            if linter == "dotnet":
                cmd = ["dotnet", "format", "--verify-no-changes", file_path]
            else:
                return f"Error: Unsupported C# linter '{linter}'. Supported linters are: dotnet"
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"No formatting issues found in {file_path}"
            
            output = result.stdout or result.stderr
            
            return f"dotnet format results for {file_path}:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing dotnet format: {str(e)}"


class BuildCompileTool(BaseTool):
    """Tool for building and compiling code projects."""
    
    name: str = "build_compile"
    description: str = """
    Builds and compiles code projects using various build systems.
    
    Input should be a JSON object with the following structure:
    {"type": "dotnet/nodejs/python/maven/gradle", "project_path": "path/to/project", "command": "build/run/test/clean", "args": "additional arguments"}
    
    Returns the build output or an error message.
    
    Example: {"type": "dotnet", "project_path": "C:\\Projects\\MyApp", "command": "build"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Build and compile code projects."""
        try:
            import json
            import subprocess
            
            params = json.loads(input_str)
            
            project_type = params.get("type", "").lower()
            project_path = params.get("project_path", "")
            command = params.get("command", "build").lower()
            args = params.get("args", "")
            
            if not project_type:
                return "Error: Missing project type parameter"
                
            if not project_path:
                return "Error: Missing project path parameter"
                
            if not os.path.exists(project_path):
                return f"Error: Project path does not exist: {project_path}"
            
            # Change to project directory for the command
            current_dir = os.getcwd()
            os.chdir(project_path)
            
            try:
                # Execute the appropriate build command
                if project_type == "dotnet":
                    return self._dotnet_build(command, args)
                elif project_type == "nodejs":
                    return self._nodejs_build(command, args)
                elif project_type == "python":
                    return self._python_build(command, args)
                elif project_type == "maven":
                    return self._maven_build(command, args)
                elif project_type == "gradle":
                    return self._gradle_build(command, args)
                else:
                    return f"Error: Unsupported project type '{project_type}'"
            
            finally:
                # Restore original directory
                os.chdir(current_dir)
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in build/compile operation: {str(e)}")
            return f"Error in build/compile operation: {str(e)}"
    
    def _dotnet_build(self, command: str, args: str) -> str:
        """Run .NET build commands."""
        try:
            if command == "build":
                cmd = ["dotnet", "build"]
            elif command == "run":
                cmd = ["dotnet", "run"]
            elif command == "test":
                cmd = ["dotnet", "test"]
            elif command == "clean":
                cmd = ["dotnet", "clean"]
            elif command == "publish":
                cmd = ["dotnet", "publish"]
            else:
                return f"Error: Unsupported .NET command '{command}'. Supported commands are: build, run, test, clean, publish"
            
            # Add additional arguments if provided
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Build error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f".NET {command} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing dotnet command: {str(e)}"
    
    def _nodejs_build(self, command: str, args: str) -> str:
        """Run Node.js build commands."""
        try:
            npm_commands = {
                "build": "run build",
                "start": "start",
                "test": "test",
                "clean": "run clean",
                "install": "install"
            }
            
            npm_command = npm_commands.get(command)
            
            if not npm_command:
                return f"Error: Unsupported Node.js command '{command}'. Supported commands are: {', '.join(npm_commands.keys())}"
            
            cmd = ["npm", *npm_command.split()]
            
            # Add additional arguments if provided
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Build error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Node.js {command} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing npm command: {str(e)}"
    
    def _python_build(self, command: str, args: str) -> str:
        """Run Python build commands."""
        try:
            if command == "build":
                # Use setuptools for build
                cmd = ["python", "setup.py", "build"]
            elif command == "install":
                cmd = ["pip", "install", "."]
            elif command == "test":
                # Try pytest first, fallback to unittest
                if os.path.exists(resource_path("pytest.ini")) or os.path.exists(resource_path("conftest.py")):
                    cmd = ["pytest"]
                else:
                    cmd = ["python", "-m", "unittest", "discover"]
            elif command == "clean":
                # Clean common build artifacts
                for folder in ["build", "dist", "*.egg-info", "__pycache__"]:
                    try:
                        import glob
                        for path in glob.glob(folder):
                            if os.path.isdir(path):
                                import shutil
                                shutil.rmtree(path)
                    except Exception as e:
                        return f"Error cleaning {folder}: {str(e)}"
                return "Python clean completed"
            else:
                return f"Error: Unsupported Python command '{command}'. Supported commands are: build, install, test, clean"
            
            # Add additional arguments if provided
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Build error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Python {command} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing Python build command: {str(e)}"
    
    def _maven_build(self, command: str, args: str) -> str:
        """Run Maven build commands."""
        try:
            maven_commands = {
                "build": "package",
                "compile": "compile",
                "test": "test",
                "clean": "clean",
                "install": "install"
            }
            
            maven_command = maven_commands.get(command)
            
            if not maven_command:
                return f"Error: Unsupported Maven command '{command}'. Supported commands are: {', '.join(maven_commands.keys())}"
            
            cmd = ["mvn", maven_command]
            
            # Add additional arguments if provided
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Build error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Maven {command} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing Maven command: {str(e)}"
    
    def _gradle_build(self, command: str, args: str) -> str:
        """Run Gradle build commands."""
        try:
            gradle_commands = {
                "build": "build",
                "compile": "compileJava",
                "test": "test",
                "clean": "clean",
                "run": "run"
            }
            
            gradle_command = gradle_commands.get(command)
            
            if not gradle_command:
                return f"Error: Unsupported Gradle command '{command}'. Supported commands are: {', '.join(gradle_commands.keys())}"
            
            # Check if Gradle wrapper exists
            if os.path.exists(resource_path("gradlew")) or os.path.exists(resource_path("gradlew.bat")):
                gradle_exe = "gradlew.bat" if os.name == "nt" else "./gradlew"
            else:
                gradle_exe = "gradle"
            
            cmd = [gradle_exe, gradle_command]
            
            # Add additional arguments if provided
            if args:
                cmd.extend(args.split())
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 and result.stderr:
                return f"Build error: {result.stderr}"
            
            output = result.stdout or result.stderr
            
            return f"Gradle {command} completed:\n{output}"
        
        except subprocess.SubprocessError as e:
            return f"Error executing Gradle command: {str(e)}"
