"""
Security Tools

Tools for encryption/decryption, password management, and file integrity verification.
"""

import sys

import os
import logging
import tempfile
import base64
import hashlib
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

class EncryptionTool(BaseTool):
    """Tool for encrypting and decrypting files."""
    
    name: str = "encryption"
    description: str = """
    Encrypts or decrypts files using various encryption algorithms.
    
    Input should be a JSON object with the following structure:
    For encryption: {"action": "encrypt", "file_path": "path/to/file", "output_path": "path/to/output", "password": "secret_password", "algorithm": "aes-256-cbc"}
    For decryption: {"action": "decrypt", "file_path": "path/to/encrypted_file", "output_path": "path/to/output", "password": "secret_password", "algorithm": "aes-256-cbc"}
    
    Returns a success message or error.
    
    Example: {"action": "encrypt", "file_path": "C:\\Documents\\secret.txt", "output_path": "C:\\Documents\\secret.enc", "password": "my_secure_password"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Encrypt or decrypt files."""
        try:
            import json
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            import os
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            file_path = params.get("file_path", "")
            output_path = params.get("output_path", "")
            password = params.get("password", "")
            algorithm = params.get("algorithm", "aes-256-cbc").lower()
            
            if not action:
                return "Error: Missing action parameter"
                
            if not file_path:
                return "Error: Missing file_path parameter"
                
            if not os.path.exists(file_path):
                return f"Error: File does not exist: {file_path}"
                
            if not password:
                return "Error: Missing password parameter"
            
            if not output_path:
                # Generate default output path
                base, ext = os.path.splitext(file_path)
                if action == "encrypt":
                    output_path = f"{base}.enc"
                else:
                    output_path = f"{base}_decrypted{ext}"
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Currently only supporting AES-256-CBC
            if algorithm != "aes-256-cbc":
                return "Error: Only 'aes-256-cbc' algorithm is currently supported"
            
            # Generate a key from the password
            salt = b'salt_' + password.encode()[:4].ljust(4, b'_')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 32 bytes for AES-256
                salt=salt,
                iterations=100000
            )
            key = kdf.derive(password.encode())
            
            if action == "encrypt":
                # Generate a random IV
                iv = os.urandom(16)  # 16 bytes for AES
                
                # Create an encryptor
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
                encryptor = cipher.encryptor()
                
                # Read the file
                with open(file_path, 'rb') as f:
                    plaintext = f.read()
                
                # Pad the plaintext to a multiple of 16 bytes (AES block size)
                pad_length = 16 - (len(plaintext) % 16)
                plaintext += bytes([pad_length]) * pad_length
                
                # Encrypt the file
                ciphertext = encryptor.update(plaintext) + encryptor.finalize()
                
                # Write the encrypted file with IV at the beginning
                with open(output_path, 'wb') as f:
                    f.write(iv)
                    f.write(ciphertext)
                
                return f"File successfully encrypted to {output_path}"
                
            elif action == "decrypt":
                try:
                    # Read the encrypted file
                    with open(file_path, 'rb') as f:
                        # First 16 bytes are the IV
                        iv = f.read(16)
                        ciphertext = f.read()
                    
                    # Create a decryptor
                    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
                    decryptor = cipher.decryptor()
                    
                    # Decrypt the file
                    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
                    
                    # Remove padding
                    pad_length = padded_plaintext[-1]
                    if pad_length > 16:
                        return "Error: Invalid padding in encrypted file. The password may be incorrect."
                    
                    plaintext = padded_plaintext[:-pad_length]
                    
                    # Write the decrypted file
                    with open(output_path, 'wb') as f:
                        f.write(plaintext)
                    
                    return f"File successfully decrypted to {output_path}"
                
                except Exception as e:
                    return f"Error decrypting file: {str(e)}. The password may be incorrect."
            
            else:
                return f"Error: Unknown action '{action}'. Use 'encrypt' or 'decrypt'."
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in encryption operation: {str(e)}")
            return f"Error in encryption operation: {str(e)}"


class PasswordManagerTool(BaseTool):
    """Tool for secure credential storage and retrieval."""
    
    name: str = "password_manager"
    description: str = """
    Securely stores and retrieves passwords and credentials.
    
    Input should be a JSON object with the following structure:
    For storing: {"action": "store", "service": "website_or_app_name", "username": "your_username", "password": "your_password", "master_password": "your_master_password"}
    For retrieving: {"action": "retrieve", "service": "website_or_app_name", "master_password": "your_master_password"}
    For listing: {"action": "list", "master_password": "your_master_password"}
    For deleting: {"action": "delete", "service": "website_or_app_name", "master_password": "your_master_password"}
    
    Returns the stored credentials or a success/error message.
    
    Example: {"action": "store", "service": "github", "username": "user@example.com", "password": "secure_password", "master_password": "master_key"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Store or retrieve passwords."""
        try:
            import json
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            service = params.get("service", "")
            username = params.get("username", "")
            password = params.get("password", "")
            master_password = params.get("master_password", "")
            
            if not action:
                return "Error: Missing action parameter"
                
            if not master_password:
                return "Error: Missing master_password parameter"
            
            # Actions that require a service
            if action in ["store", "retrieve", "delete"] and not service:
                return "Error: Missing service parameter"
            
            # Create password store directory if it doesn't exist
            password_dir = os.path.join(os.path.expanduser("~"), ".password_store")
            os.makedirs(password_dir, exist_ok=True)
            
            # Derive key from master password
            salt = b'password_manager_salt'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            fernet = Fernet(key)
            
            # Path to the encrypted password database
            db_path = os.path.join(password_dir, "passwords.enc")
            
            # Load existing passwords if file exists
            if os.path.exists(db_path):
                try:
                    with open(db_path, 'rb') as f:
                        encrypted_data = f.read()
                    
                    # Try to decrypt
                    try:
                        decrypted_data = fernet.decrypt(encrypted_data)
                        passwords = json.loads(decrypted_data.decode())
                    except Exception:
                        return "Error: Invalid master password or corrupted password database"
                
                except Exception as e:
                    return f"Error reading password database: {str(e)}"
            else:
                passwords = {}
            
            if action == "store":
                # Store a new password
                if not username:
                    return "Error: Missing username parameter"
                    
                if not password:
                    return "Error: Missing password parameter"
                
                # Create/update entry
                passwords[service] = {
                    "username": username,
                    "password": password
                }
                
                # Encrypt and save passwords
                try:
                    encrypted_data = fernet.encrypt(json.dumps(passwords).encode())
                    
                    with open(db_path, 'wb') as f:
                        f.write(encrypted_data)
                    
                    return f"Credentials for '{service}' successfully stored"
                
                except Exception as e:
                    return f"Error saving credentials: {str(e)}"
            
            elif action == "retrieve":
                # Retrieve a password
                if service not in passwords:
                    return f"Error: No credentials found for '{service}'"
                
                credential = passwords[service]
                
                return f"Credentials for '{service}':\nUsername: {credential['username']}\nPassword: {credential['password']}"
            
            elif action == "list":
                # List all stored services
                if not passwords:
                    return "No credentials stored yet"
                
                services = list(passwords.keys())
                services.sort()
                
                return f"Stored credentials for {len(services)} services:\n" + "\n".join(services)
            
            elif action == "delete":
                # Delete a password
                if service not in passwords:
                    return f"Error: No credentials found for '{service}'"
                
                # Remove the entry
                del passwords[service]
                
                # Encrypt and save updated passwords
                try:
                    encrypted_data = fernet.encrypt(json.dumps(passwords).encode())
                    
                    with open(db_path, 'wb') as f:
                        f.write(encrypted_data)
                    
                    return f"Credentials for '{service}' successfully deleted"
                
                except Exception as e:
                    return f"Error updating password database: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: store, retrieve, list, delete"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in password management: {str(e)}")
            return f"Error in password management: {str(e)}"


class FileIntegrityTool(BaseTool):
    """Tool for verifying file checksums and integrity."""
    
    name: str = "file_integrity"
    description: str = """
    Verifies file integrity by calculating and verifying checksums.
    
    Input should be a JSON object with the following structure:
    For calculating checksum: {"action": "calculate", "file_path": "path/to/file", "algorithm": "md5/sha1/sha256"}
    For verifying checksum: {"action": "verify", "file_path": "path/to/file", "checksum": "expected_checksum", "algorithm": "md5/sha1/sha256"}
    
    Returns the calculated checksum or verification result.
    
    Example: {"action": "calculate", "file_path": "C:\\Downloads\\file.zip", "algorithm": "sha256"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Calculate or verify file checksums."""
        try:
            import json
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            file_path = params.get("file_path", "")
            algorithm = params.get("algorithm", "sha256").lower()
            checksum = params.get("checksum", "")
            
            if not action:
                return "Error: Missing action parameter"
                
            if not file_path:
                return "Error: Missing file_path parameter"
                
            if not os.path.exists(file_path):
                return f"Error: File does not exist: {file_path}"
            
            # Validate algorithm
            valid_algorithms = ["md5", "sha1", "sha256", "sha512"]
            if algorithm not in valid_algorithms:
                return f"Error: Unsupported algorithm '{algorithm}'. Supported algorithms are: {', '.join(valid_algorithms)}"
            
            # Calculate the checksum
            calculated_checksum = self._calculate_checksum(file_path, algorithm)
            
            if action == "calculate":
                return f"{algorithm.upper()} checksum for {file_path}:\n{calculated_checksum}"
                
            elif action == "verify":
                if not checksum:
                    return "Error: Missing checksum parameter for verification"
                
                # Normalize checksums for comparison (remove whitespace, make lowercase)
                checksum = checksum.lower().strip()
                calculated_checksum = calculated_checksum.lower().strip()
                
                if calculated_checksum == checksum:
                    return f"Checksum verification PASSED for {file_path}\nExpected: {checksum}\nCalculated: {calculated_checksum}"
                else:
                    return f"Checksum verification FAILED for {file_path}\nExpected: {checksum}\nCalculated: {calculated_checksum}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: calculate, verify"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in file integrity verification: {str(e)}")
            return f"Error in file integrity verification: {str(e)}"
    
    def _calculate_checksum(self, file_path: str, algorithm: str) -> str:
        """Calculate a file's checksum using the specified algorithm."""
        try:
            # Choose the appropriate hashlib function
            hash_function = None
            if algorithm == "md5":
                hash_function = hashlib.md5()
            elif algorithm == "sha1":
                hash_function = hashlib.sha1()
            elif algorithm == "sha256":
                hash_function = hashlib.sha256()
            elif algorithm == "sha512":
                hash_function = hashlib.sha512()
            else:
                return f"Error: Unsupported algorithm '{algorithm}'"
            
            # Calculate hash in chunks to handle large files
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_function.update(chunk)
            
            return hash_function.hexdigest()
        
        except Exception as e:
            return f"Error calculating checksum: {str(e)}"
