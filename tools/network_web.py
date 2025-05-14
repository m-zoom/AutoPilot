"""
Network & Web Tools

Tools for network operations, web requests, and email functionality.
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

class DownloadFileTool(BaseTool):
    """Tool for downloading files from URLs."""
    
    name: str = "download_file"
    description: str = """
    Downloads a file from a URL to a local path.
    
    Input should be a JSON object with the following structure:
    {"url": "https://example.com/file.pdf", "destination": "C:\\Downloads\\file.pdf", "headers": {"User-Agent": "..."}}
    
    Headers are optional. If destination is not provided, the file will be saved to a temporary location.
    
    Returns the path to the downloaded file or an error.
    
    Example: {"url": "https://example.com/file.pdf", "destination": "C:\\Downloads\\file.pdf"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Download a file from a URL."""
        try:
            import json
            import requests
            from urllib.parse import urlparse
            
            params = json.loads(input_str)
            
            url = params.get("url", "")
            destination = params.get("destination", "")
            headers = params.get("headers", {})
            
            if not url:
                return "Error: Missing URL parameter"
            
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return f"Error: Invalid URL format: {url}"
            
            # If destination not provided, create a temp file
            if not destination:
                # Get filename from URL or use a default name
                filename = os.path.basename(parsed_url.path)
                if not filename:
                    filename = "downloaded_file"
                
                # Create temp file with the same extension if possible
                _, extension = os.path.splitext(filename)
                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
                    destination = temp.name
            else:
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
            
            # Download the file
            try:
                with requests.get(url, headers=headers, stream=True) as r:
                    r.raise_for_status()  # Raise an exception for HTTP errors
                    
                    # Get file size if available
                    total_size = int(r.headers.get('content-length', 0))
                    
                    # Write to file
                    with open(destination, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                
                return f"Successfully downloaded file to {destination}"
            except requests.exceptions.HTTPError as e:
                return f"HTTP Error: {str(e)}"
            except requests.exceptions.ConnectionError:
                return f"Error: Could not connect to {url}"
            except requests.exceptions.Timeout:
                return f"Error: Request to {url} timed out"
            except requests.exceptions.RequestException as e:
                return f"Error downloading file: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return f"Error downloading file: {str(e)}"


class WebAPIRequestTool(BaseTool):
    """Tool for making HTTP requests to APIs."""
    
    name: str = "web_api_request"
    description: str = """
    Makes HTTP requests to web APIs and returns the response.
    
    Input should be a JSON object with the following structure:
    {
        "method": "GET/POST/PUT/DELETE",
        "url": "https://api.example.com/endpoint",
        "headers": {"Content-Type": "application/json", "Authorization": "Bearer token"},
        "params": {"param1": "value1"},
        "json": {"key": "value"},
        "data": "raw string data",
        "timeout": 30
    }
    
    Headers, params, json, data and timeout are optional. Json and data are mutually exclusive.
    
    Returns the API response or an error.
    
    Example: {"method": "GET", "url": "https://api.example.com/users", "headers": {"Authorization": "Bearer token"}}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Make HTTP request to an API."""
        try:
            import json
            import requests
            from urllib.parse import urlparse
            
            params = json.loads(input_str)
            
            method = params.get("method", "").upper()
            url = params.get("url", "")
            headers = params.get("headers", {})
            query_params = params.get("params", {})
            json_data = params.get("json")
            data = params.get("data")
            timeout = params.get("timeout", 30)
            
            if not method:
                return "Error: Missing method parameter"
                
            if not url:
                return "Error: Missing URL parameter"
                
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                return f"Error: Invalid HTTP method: {method}"
            
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return f"Error: Invalid URL format: {url}"
            
            # Check if both json and data are provided
            if json_data is not None and data is not None:
                return "Error: Cannot provide both 'json' and 'data' parameters"
            
            # Make the request
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=json_data,
                    data=data,
                    timeout=timeout
                )
                
                # Try to get JSON response
                try:
                    response_data = response.json()
                    # Format JSON nicely
                    formatted_response = json.dumps(response_data, indent=2)
                except ValueError:
                    # Not JSON, return text
                    formatted_response = response.text
                
                return f"Status Code: {response.status_code}\nResponse:\n{formatted_response}"
            
            except requests.exceptions.HTTPError as e:
                return f"HTTP Error: {str(e)}"
            except requests.exceptions.ConnectionError:
                return f"Error: Could not connect to {url}"
            except requests.exceptions.Timeout:
                return f"Error: Request to {url} timed out"
            except requests.exceptions.RequestException as e:
                return f"Error making request: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            return f"Error making API request: {str(e)}"


class NetworkDiagnosticsTool(BaseTool):
    """Tool for running network diagnostics."""
    
    name: str = "network_diagnostics"
    description: str = """
    Runs network diagnostic commands like ping, traceroute, nslookup, etc.
    
    Input should be a JSON object with the following structure:
    {"command": "ping/tracert/nslookup/ipconfig", "target": "example.com", "options": "-n 5"}
    
    Target is required for ping, tracert, and nslookup commands.
    Options are optional command-line parameters.
    
    Returns the output of the command or an error.
    
    Example: {"command": "ping", "target": "example.com", "options": "-n 4"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run network diagnostic commands."""
        try:
            import json
            import subprocess
            import re
            
            params = json.loads(input_str)
            
            command = params.get("command", "").lower()
            target = params.get("target", "")
            options = params.get("options", "")
            
            if not command:
                return "Error: Missing command parameter"
            
            # Commands that require a target
            target_commands = ["ping", "tracert", "nslookup"]
            
            if command in target_commands and not target:
                return f"Error: Missing target parameter for {command} command"
            
            # Map commands to actual executables
            command_map = {
                "ping": "ping",
                "tracert": "tracert",
                "traceroute": "tracert",  # Alias for tracert on Windows
                "nslookup": "nslookup",
                "ipconfig": "ipconfig",
                "netstat": "netstat",
                "route": "route",
                "arp": "arp",
                "dns": "nslookup"  # Alias for nslookup
            }
            
            # Validate command
            if command not in command_map:
                return f"Error: Unknown command '{command}'. Valid commands are: {', '.join(command_map.keys())}"
            
            # Build the command string
            cmd_str = command_map[command]
            
            # Add target for commands that need it
            if command in target_commands:
                # Validate target with regex
                # Allow only alphanumeric, dash, underscore, dot, and colon for IP:port
                if not re.match(r'^[a-zA-Z0-9\-_.:/]+$', target):
                    return f"Error: Invalid target format: {target}"
                cmd_str += f" {target}"
            
            # Add options if provided
            if options:
                cmd_str += f" {options}"
            
            # Run the command
            try:
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60  # Timeout after 60 seconds
                )
                
                if result.returncode != 0 and result.stderr:
                    return f"Command error: {result.stderr}"
                
                output = result.stdout or result.stderr
                
                return f"Command: {cmd_str}\nOutput:\n{output}"
            
            except subprocess.TimeoutExpired:
                return f"Error: Command timed out after 60 seconds"
            except subprocess.SubprocessError as e:
                return f"Error executing command: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in network diagnostics: {str(e)}")
            return f"Error in network diagnostics: {str(e)}"


class EmailSendTool(BaseTool):
    """Tool for composing and sending emails."""
    
    name: str = "email_send"
    description: str = """
    Composes and sends emails.
    
    Input should be a JSON object with the following structure:
    {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username": "your_email@example.com",
        "password": "your_password",
        "from": "your_email@example.com",
        "to": ["recipient@example.com"],
        "cc": ["cc_recipient@example.com"],
        "bcc": ["bcc_recipient@example.com"],
        "subject": "Email Subject",
        "body": "Email body text",
        "html_body": "<p>HTML email body</p>",
        "attachments": ["C:\\path\\to\\file.pdf"]
    }
    
    SMTP server, port, username, password, from, to, and subject are required.
    CC, BCC, and attachments are optional.
    Either body or html_body must be provided.
    
    Returns a success message or error.
    
    Example: {"smtp_server": "smtp.gmail.com", "smtp_port": 587, "username": "your_email@gmail.com", "password": "your_password", "from": "your_email@gmail.com", "to": ["recipient@example.com"], "subject": "Test Email", "body": "This is a test email."}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Compose and send an email."""
        try:
            import json
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.application import MIMEApplication
            from email.utils import formataddr
            
            params = json.loads(input_str)
            
            # Required parameters
            smtp_server = params.get("smtp_server", "")
            smtp_port = params.get("smtp_port", 0)
            username = params.get("username", "")
            password = params.get("password", "")
            from_email = params.get("from", "")
            to_emails = params.get("to", [])
            subject = params.get("subject", "")
            
            # Optional parameters
            cc_emails = params.get("cc", [])
            bcc_emails = params.get("bcc", [])
            body_text = params.get("body", "")
            html_body = params.get("html_body", "")
            attachments = params.get("attachments", [])
            
            # Validate required parameters
            missing_params = []
            if not smtp_server:
                missing_params.append("smtp_server")
            if not smtp_port:
                missing_params.append("smtp_port")
            if not username:
                missing_params.append("username")
            if not password:
                missing_params.append("password")
            if not from_email:
                missing_params.append("from")
            if not to_emails:
                missing_params.append("to")
            if not subject:
                missing_params.append("subject")
            if not body_text and not html_body:
                missing_params.append("body or html_body")
            
            if missing_params:
                return f"Error: Missing required parameters: {', '.join(missing_params)}"
            
            # Create the email message
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr(("Sender", from_email))
            msg["Subject"] = subject
            
            # Add recipients
            if not isinstance(to_emails, list):
                to_emails = [to_emails]
            msg["To"] = ", ".join(to_emails)
            
            if cc_emails:
                if not isinstance(cc_emails, list):
                    cc_emails = [cc_emails]
                msg["Cc"] = ", ".join(cc_emails)
            
            all_recipients = to_emails + cc_emails + bcc_emails
            
            # Add text and HTML parts
            if body_text:
                msg.attach(MIMEText(body_text, "plain"))
            
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    try:
                        with open(attachment_path, "rb") as file:
                            part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                        
                        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                        msg.attach(part)
                    except FileNotFoundError:
                        return f"Error: Attachment file not found: {attachment_path}"
                    except Exception as e:
                        return f"Error processing attachment {attachment_path}: {str(e)}"
            
            # Send the email
            try:
                # Create secure connection with the server and send email
                context = ssl.create_default_context()
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.ehlo()  # Can be omitted
                    server.starttls(context=context)
                    server.ehlo()  # Can be omitted
                    server.login(username, password)
                    server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
                
                return f"Email successfully sent to {', '.join(to_emails)}"
            
            except smtplib.SMTPAuthenticationError:
                return "Error: Authentication failed. Please check your username and password."
            except smtplib.SMTPException as e:
                return f"SMTP error: {str(e)}"
            except Exception as e:
                return f"Error sending email: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return f"Error sending email: {str(e)}"
