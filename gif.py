from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import zlib
import os
import hmac
import hashlib
import struct
import time
import logging
from datetime import datetime
from PIL import Image
from tkinter import messagebox
import secrets
from base64 import b64encode, b64decode

# Setup logging for debugging
logging.basicConfig(filename='steganography.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Unique markers to identify data sections
MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'  # Marks the start of hidden data
METADATA_MARKER = b'\xCA\xFE\xBA\xBE'  # Marks the metadata section

class GIFSteganographyLogic:
    """Handles the core steganography operations for GIFs (embedding, extracting, etc.)."""
    def __init__(self):
        self.cipher = None
        self.key = None  # Store key in memory
        self.hmac_key = None
        self.MAX_FILES_EMBED = 40  # Maximum files that can be embedded
        self.MAX_REASONABLE_SIZE = 1024 * 1024 * 100  # 100 MB max for GIFs

    def generate_key(self):
        """Generate a random encryption key as a string."""
        # Generate a random 32-byte key and encode it as a base64 string
        key_bytes = secrets.token_bytes(32)
        self.key = key_bytes  # Store the raw key bytes in memory
        key_str = b64encode(key_bytes).decode('utf-8')
        return key_str
    
    def generate_hmac(self, data):
        """Generate HMAC for data integrity."""
        return hmac.new(self.hmac_key, data, hashlib.sha256).digest()

    def verify_hmac(self, data, expected_hmac):
        """Verify HMAC for data integrity."""
        return hmac.compare_digest(self.generate_hmac(data), expected_hmac)

    def get_cipher(self, key_str, root=None):
        """Initialize the cipher with the provided key."""
        if not key_str:
            if root:
                root.after(0, lambda: messagebox.showerror("Error", "Please provide an encryption key."))
            return None
        try:
            # Convert key string to bytes if it's not already
            if isinstance(key_str, str):
                key_bytes = key_str.encode('utf-8')
            else:
                key_bytes = key_str
                
            self.key = key_bytes  # Store the key bytes in memory
            
            # Generate Fernet key
            key = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
            self.cipher = Fernet(key)
            
            # Generate HMAC key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"YrLgT7hpEq2bYw!!7WC9tW8ogVVLhowXv9-iko4MghAuXixm34d6TdtYRA*9ZWiLi7aLWLNw77uEMAoCPZZVd3Y*RT7no_7@pYHm",
                iterations=100000,
            )
            self.hmac_key = kdf.derive(self.key)
            
            return self.cipher
        except Exception as e:
            logging.error(f"Cipher setup failed: {str(e)}")
            if root:
                root.after(0, lambda: messagebox.showerror("Error", f"Invalid encryption key: {str(e)}"))
            self.cipher = None
            self.key = None
            self.hmac_key = None
            return None

    def derive_password_hash(self, password):
        """Derive a hash from the password for authentication."""
        kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=16,
                salt=b"22CbooBo3_@NK8c@yGZJ2MRq6t@MhxvhY!x6-4*gsHQbUiY.fjmkK7bHM6FH.L4kQU7deTsJBLmYrsJFsgMw4PetJ_DuURi2R!kY",
                iterations=100000,
            )
        return kdf.derive(password.encode() if password else b"")

    def compress_data(self, data):
        """Compress data using zlib."""
        return zlib.compress(data)

    def decompress_data(self, data):
        """Decompress data using zlib."""
        return zlib.decompress(data)

    def find_gif_trailer(self, data):
        """Find the position of the GIF trailer byte (0x3B)."""
        return data.rfind(b'\x3B')

    def split_gif_data(self, gif_data):
        """Split GIF data into GIF content and hidden data."""
        try:
            # Find GIF trailer
            trailer_index = gif_data.rfind(b'\x3B')
            if trailer_index == -1:
                raise ValueError("Invalid GIF: No trailer marker found")

            # Get GIF content (including trailer)
            gif_content = gif_data[:trailer_index + 1]
            
            # Check if there's any data after the trailer
            if len(gif_data) <= trailer_index + 1:
                raise ValueError("No hidden data found after GIF trailer")

            # Get hidden data (everything after the trailer)
            hidden_data = gif_data[trailer_index + 1:]
            
            # Find magic marker
            magic_index = hidden_data.find(MAGIC_MARKER)
            if magic_index == -1:
                raise ValueError("Invalid hidden data: Missing magic marker")
            
            # Remove any padding before magic marker
            hidden_data = hidden_data[magic_index:]
            
            # Verify magic marker and remove it
            if not hidden_data.startswith(MAGIC_MARKER):
                raise ValueError("Invalid hidden data: Corrupted magic marker")
            hidden_data = hidden_data[len(MAGIC_MARKER):]
            
            # Get and verify data length
            if len(hidden_data) < 4:
                raise ValueError("Invalid hidden data: Missing length prefix")
            data_length = int.from_bytes(hidden_data[:4], byteorder='big')
            if data_length <= 0:
                raise ValueError("Invalid hidden data: Zero or negative length")
            if data_length > 100 * 1024 * 1024:  # 100 MB limit
                raise ValueError("Invalid hidden data: Length exceeds maximum allowed size")
            hidden_data = hidden_data[4:]
            
            if len(hidden_data) < data_length:
                raise ValueError(f"Incomplete hidden data: expected {data_length} bytes, got {len(hidden_data)}")

            # Get the actual data
            hidden_data = hidden_data[:data_length]

            # Verify minimum data size for basic structure (password field + file count)
            if len(hidden_data) < 104:  # 100 bytes for password + 4 bytes for file count
                raise ValueError("Invalid hidden data: Data too small to contain required fields")

            # Extract and validate password field
            password_bytes = hidden_data[:100]
            hidden_data = hidden_data[100:]

            # Check if password is present (non-zero bytes)
            has_password = any(b != 0 for b in password_bytes)
            try:
                password = password_bytes.rstrip(b'\0').decode('utf-8') if has_password else None
            except UnicodeDecodeError:
                raise ValueError("Invalid hidden data: Password field contains invalid characters")

            # Verify file count
            if len(hidden_data) < 4:
                raise ValueError("Invalid hidden data: Missing file count field")
            num_files = int.from_bytes(hidden_data[:4], byteorder='big')
            if num_files <= 0:
                raise ValueError("Invalid hidden data: No files found")
            if num_files > self.MAX_FILES_EMBED:
                raise ValueError(f"Invalid hidden data: Number of files exceeds limit ({self.MAX_FILES_EMBED})")

            return gif_content, hidden_data, password

        except Exception as e:
            logging.error(f"Error in split_gif_data: {str(e)}")
            raise ValueError(f"Failed to split GIF data: {str(e)}")

    def prepare_data_to_embed(self, files_to_embed, password=None, author=None):
        """Prepare data for embedding into GIF."""
        try:
            # Start with magic marker
            prepared_data = bytearray()
            prepared_data.extend(MAGIC_MARKER)

            # Add password field (padded to 100 bytes)
            if password:
                password_bytes = password.encode('utf-8')
                if len(password_bytes) > 100:
                    raise ValueError("Password too long (max 100 bytes)")
                password_bytes = password_bytes.ljust(100, b'\0')
            else:
                password_bytes = b'\0' * 100
            prepared_data.extend(password_bytes)

            # Add number of files
            num_files = len(files_to_embed)
            if num_files <= 0:
                raise ValueError("No files to embed")
            if num_files > self.MAX_FILES_EMBED:
                raise ValueError(f"Too many files (max {self.MAX_FILES_EMBED})")
            prepared_data.extend(num_files.to_bytes(4, byteorder='big'))

            # Calculate total size of files
            total_size = 0
            for file_path in files_to_embed:
                if not os.path.exists(file_path):
                    raise ValueError(f"File not found: {file_path}")
                file_size = os.path.getsize(file_path)
                if file_size > 10 * 1024 * 1024:  # 10 MB per file limit
                    raise ValueError(f"File too large (max 10MB): {file_path}")
                total_size += file_size

            if total_size > 100 * 1024 * 1024:  # 100 MB total limit
                raise ValueError("Total file size exceeds 100MB limit")

            # Add each file's data
            for file_path in files_to_embed:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                ext = ext.lstrip('.')  # Remove leading dot

                # Validate filename and extension
                if len(name) > 255:
                    raise ValueError(f"Filename too long (max 255 chars): {name}")
                if len(ext) > 10:
                    raise ValueError(f"Extension too long (max 10 chars): {ext}")

                # Read file data
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                # Add filename length and filename
                name_bytes = name.encode('utf-8')
                prepared_data.extend(len(name_bytes).to_bytes(1, byteorder='big'))
                prepared_data.extend(name_bytes)

                # Add extension length and extension
                ext_bytes = ext.encode('utf-8')
                prepared_data.extend(len(ext_bytes).to_bytes(1, byteorder='big'))
                prepared_data.extend(ext_bytes)

                # Add file size and data
                prepared_data.extend(len(file_data).to_bytes(4, byteorder='big'))
                prepared_data.extend(file_data)

            # Add metadata
            metadata = bytearray()
            metadata.extend(METADATA_MARKER)
            
            # Add author name (optional)
            author_bytes = (author or "").encode('utf-8')[:50].ljust(50, b' ')
            metadata.extend(author_bytes)
            
            # Add timestamp
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata.extend(timestamp)

            # Add metadata length and data
            prepared_data.extend(len(metadata).to_bytes(4, byteorder='big'))
            prepared_data.extend(metadata)

            # Encrypt entire data if password is provided
            if password:
                data_to_encrypt = prepared_data[len(MAGIC_MARKER):]
                if not self.cipher:
                    self.get_cipher(password)
                if not self.cipher:
                    raise ValueError("Failed to initialize encryption")
                encrypted_data = self.cipher.encrypt(bytes(data_to_encrypt))
                prepared_data = bytearray(MAGIC_MARKER) + encrypted_data

            return prepared_data

        except Exception as e:
            logging.error(f"Error in prepare_data_to_embed: {str(e)}")
            raise ValueError(f"Failed to prepare data for embedding: {str(e)}")

    def embed_data(self, gif_path, files_to_embed, output_path, password=None, author=None, progress_callback=None):
        """Embed data into a GIF file."""
        try:
            # Validate paths
            if not os.path.exists(gif_path):
                raise ValueError(f"Input GIF file not found: {gif_path}")
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Initialize cipher if password is provided
            if password:
                if not self.cipher:
                    self.get_cipher(password)
                if not self.cipher:
                    raise ValueError("Failed to initialize encryption")

            # Read the GIF file
            with open(gif_path, 'rb') as f:
                gif_data = f.read()

            # Verify it's a valid GIF
            if not gif_data.startswith(b'GIF87a') and not gif_data.startswith(b'GIF89a'):
                raise ValueError("Invalid GIF file format")

            # Find the trailer position
            trailer_pos = gif_data.rfind(b'\x3B')
            if trailer_pos == -1:
                raise ValueError("Invalid GIF: No trailer byte found")

            # Keep only up to the trailer
            gif_data = gif_data[:trailer_pos + 1]

            # Prepare the data to embed
            data_to_embed = self.prepare_data_to_embed(files_to_embed, password, author)
            
            # Add magic marker and length prefix
            data_length = len(data_to_embed)
            if data_length > 100 * 1024 * 1024:  # 100 MB limit
                raise ValueError(f"Total data size ({data_length} bytes) exceeds maximum allowed (100 MB)")
                
            final_data = gif_data + data_to_embed

            # Write the output file
            with open(output_path, 'wb') as f:
                f.write(final_data)

            if progress_callback:
                progress_callback(100)  # Embedding complete

            return final_data

        except Exception as e:
            logging.error(f"Error in embed_data: {str(e)}")
            raise ValueError(f"Embedding failed: {str(e)}")

    def embed_batch(self, carrier_gif_path, data_file_paths, key_str, password, author, progress_range=None):
        """Process a batch of files for embedding in GIF with better memory efficiency."""
        if not self.get_cipher(key_str):
            raise ValueError("Invalid encryption key")
        
        if len(data_file_paths) > self.MAX_FILES_EMBED:
            raise ValueError(f"Cannot embed more than {self.MAX_FILES_EMBED} files in batch.")
            
        # Calculate total size of files to embed (with safety checks)
        total_size = 0
        for path in data_file_paths:
            file_size = os.path.getsize(path)
            if file_size > 100 * 1024 * 1024:  # 100MB per file limit
                raise ValueError(f"File {path} is too large ({file_size} bytes). Maximum size per file is 100MB")
            total_size += file_size
            
        # Safety check for total size
        if total_size > 1073741824:  # 1GB limit
            raise ValueError(f"Total data size ({total_size} bytes) exceeds maximum allowed (1GB)")
        
        password_hash = self.derive_password_hash(password) if password else b'\x00' * 16
        key_hash = hashlib.sha256(self.key).digest()[:16]
        
        base_name = os.path.splitext(os.path.basename(carrier_gif_path))[0]
        all_encrypted_data = bytearray()
        file_metadata = []
        file_count = len(data_file_paths)
        
        # Process each file in the batch
        for i, path in enumerate(data_file_paths):
            file_size = os.path.getsize(path)
            with open(path, "rb") as data_file:
                raw_data = data_file.read()
                
            filename = f"{base_name}_{i+1}".encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            ext = os.path.splitext(path)[1].encode('utf-8', errors='replace')[:10].ljust(10, b' ')
            compressed_data = self.compress_data(raw_data)
            encrypted_data = self.cipher.encrypt(compressed_data)
            
            file_metadata.append((filename, ext, len(encrypted_data)))
            all_encrypted_data.extend(encrypted_data)
            
            # Clean up memory
            del raw_data, compressed_data, encrypted_data
        
        # Process metadata
        author_bytes = author.strip().encode('utf-8', errors='replace')[:50].ljust(50, b' ')
        timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
        metadata = METADATA_MARKER + author_bytes + timestamp
        encrypted_metadata = self.cipher.encrypt(metadata)
        
        # Combine everything into the final hidden data
        file_metadata_bytes = b"".join(fn + ext + struct.pack(">I", dl) for fn, ext, dl in file_metadata)
        hidden_data = (MAGIC_MARKER + key_hash + password_hash +
                    struct.pack(">I", file_count) + file_metadata_bytes +
                    bytes(all_encrypted_data) + struct.pack(">I", len(encrypted_metadata)) + encrypted_metadata)
        hmac_value = self.generate_hmac(hidden_data)
        hidden_data += hmac_value
        
        # Return the processed batch data
        return {
            "metadata": file_metadata,
            "hidden_data": hidden_data,
            "batch_size": len(data_file_paths)
        }
    
    def extract_data(self, carrier_gif_path, output_dir, key_str=None, password=None, progress_callback=None):
        """Extract data from the carrier GIF."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Initialize cipher if password is provided
            if password and key_str:
                cipher = self.get_cipher(key_str)
                if cipher is None:
                    raise ValueError("Failed to initialize cipher with provided key")

            # Read the carrier GIF
            with open(carrier_gif_path, "rb") as gif_file:
                file_data = gif_file.read()

            # Find GIF trailer
            trailer_pos = file_data.rfind(b'\x3B')
            if trailer_pos == -1:
                raise ValueError("Invalid GIF: No trailer byte found")

            # Get data after trailer
            hidden_data = file_data[trailer_pos + 1:]

            # Find magic marker
            magic_pos = hidden_data.find(MAGIC_MARKER)
            if magic_pos == -1:
                raise ValueError("No hidden data found: Missing magic marker")

            # Remove any data before magic marker
            hidden_data = hidden_data[magic_pos:]

            # Verify magic marker
            if not hidden_data.startswith(MAGIC_MARKER):
                raise ValueError("Invalid data format: Corrupted magic marker")

            # Remove magic marker
            hidden_data = hidden_data[len(MAGIC_MARKER):]

            # Get password field
            if len(hidden_data) < 100:
                raise ValueError("Invalid data format: Missing password field")
            stored_password = hidden_data[:100].rstrip(b'\0')
            if password:
                if stored_password and stored_password.decode('utf-8', errors='ignore') != password:
                    raise ValueError("Invalid password")
            hidden_data = hidden_data[100:]

            # Decrypt data if password is provided
            if password and key_str:
                try:
                    hidden_data = self.cipher.decrypt(hidden_data)
                except Exception as e:
                    raise ValueError(f"Decryption failed: {str(e)}")

            # Get number of files
            if len(hidden_data) < 4:
                raise ValueError("Invalid data format: Missing file count")
            file_count = int.from_bytes(hidden_data[:4], byteorder='big')
            if file_count <= 0 or file_count > self.MAX_FILES_EMBED:
                raise ValueError(f"Invalid file count: {file_count}")
            pos = 4

            # Process each file
            extracted_files = []
            for i in range(file_count):
                if progress_callback:
                    progress_callback(30 + (50 * i // file_count))

                # Get filename
                if pos >= len(hidden_data):
                    raise ValueError(f"Invalid data format: Incomplete data for file {i+1}")
                filename_length = hidden_data[pos]
                pos += 1
                if pos + filename_length > len(hidden_data):
                    raise ValueError(f"Invalid data format: Filename data incomplete for file {i+1}")
                filename = hidden_data[pos:pos + filename_length].decode('utf-8', errors='ignore')
                pos += filename_length

                # Get extension
                if pos >= len(hidden_data):
                    raise ValueError(f"Invalid data format: Missing extension for file {i+1}")
                ext_length = hidden_data[pos]
                pos += 1
                if pos + ext_length > len(hidden_data):
                    raise ValueError(f"Invalid data format: Extension data incomplete for file {i+1}")
                extension = hidden_data[pos:pos + ext_length].decode('utf-8', errors='ignore')
                pos += ext_length

                # Get file data
                if pos + 4 > len(hidden_data):
                    raise ValueError(f"Invalid data format: Missing data length for file {i+1}")
                data_length = int.from_bytes(hidden_data[pos:pos + 4], byteorder='big')
                pos += 4
                if pos + data_length > len(hidden_data):
                    raise ValueError(f"Invalid data format: File data incomplete for file {i+1}")
                file_data = hidden_data[pos:pos + data_length]
                pos += data_length

                # Create output filename with date
                output_filename = f"{filename}_{datetime.now().strftime('%Y-%m-%d')}{extension}"
                output_path = os.path.join(output_dir, output_filename)

                # Save the file
                with open(output_path, 'wb') as f:
                    f.write(file_data)

                extracted_files.append(output_path)

            # Process metadata
            if pos + 4 > len(hidden_data):
                raise ValueError("Invalid data format: Missing metadata length")
            metadata_length = int.from_bytes(hidden_data[pos:pos + 4], byteorder='big')
            pos += 4

            if pos + metadata_length > len(hidden_data):
                raise ValueError("Invalid data format: Incomplete metadata")
            metadata = hidden_data[pos:pos + metadata_length]

            if not metadata.startswith(METADATA_MARKER):
                metadata = METADATA_MARKER + b''.ljust(50, b' ') + b'0'.ljust(20, b' ')

            # Extract author and timestamp
            author = metadata[4:54].strip().decode('utf-8', errors='ignore')
            timestamp = metadata[54:74].strip().decode('utf-8', errors='ignore')
            timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "N/A"

            if progress_callback:
                progress_callback(100)

            return extracted_files

        except Exception as e:
            logging.error(f"GIF extraction failed: {str(e)}")
            raise ValueError(f"Extraction failed: {str(e)}")

    def extract_data_optimized(self, carrier_gif_path, key_str, password, progress_callback, chunk_size=1024*1024):
        """Extract data from the carrier GIF with optimized memory usage."""
        if not self.get_cipher(key_str):
            raise ValueError("Invalid encryption key")

        password_hash = self.derive_password_hash(password) if password else b'\x00' * 16
        key_hash = hashlib.sha256(self.key).digest()[:16]

        # Get the current date for consistent naming
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Read the GIF in chunks to reduce memory usage for large files
        with open(carrier_gif_path, "rb") as gif_file:
            # First read a small chunk to check the header
            header = gif_file.read(1024)  # Usually GIF headers are small
            if not header.startswith(b'GIF'):
                raise ValueError("Invalid GIF format")
                
            # Find the trailer position by reading chunks
            trailer_pos = -1
            chunk_size = min(chunk_size, 10*1024*1024)  # Max 10MB per chunk for safety
            
            gif_file.seek(0)
            data = b''
            bytes_read = 0
            
            while True:
                chunk = gif_file.read(chunk_size)
                if not chunk:
                    break
                    
                data += chunk
                trailer_idx = data.rfind(b'\x3B')
                if trailer_idx != -1:
                    trailer_pos = bytes_read + trailer_idx
                    break
                    
                # Keep only the last few bytes in case trailer spans chunks
                if len(data) > chunk_size:
                    data = data[-1024:]  # Keep last 1KB in case trailer is split
                    
                bytes_read += len(chunk)
                progress_callback(min(10, bytes_read / os.path.getsize(carrier_gif_path) * 10))
                
        if trailer_pos == -1:
            raise ValueError("Invalid GIF: Trailer byte (0x3B) not found.")
        
        # Now read the GIF part and the hidden data part separately
        with open(carrier_gif_path, "rb") as gif_file:
            gif_file.seek(trailer_pos + 1)  # Skip to just after the trailer
            hidden_data_header = gif_file.read(4)  # Read length prefix
            
            if len(hidden_data_header) < 4:
                raise ValueError("No hidden data found (insufficient data for length prefix).")
                
            hidden_data_length = struct.unpack(">I", hidden_data_header)[0]
            
            # Sanity check on the length
            file_size = os.path.getsize(carrier_gif_path)
            if hidden_data_length > file_size - trailer_pos - 5:
                raise ValueError(f"Hidden data length ({hidden_data_length} bytes) exceeds available data. File may be corrupted.")
                
            # Read hidden data in chunks to manage memory
            hidden_data = bytearray(hidden_data_length)
            bytes_read = 0
            
            while bytes_read < hidden_data_length:
                chunk = gif_file.read(min(chunk_size, hidden_data_length - bytes_read))
                if not chunk:
                    break
                    
                hidden_data[bytes_read:bytes_read+len(chunk)] = chunk
                bytes_read += len(chunk)
                progress_callback(10 + (bytes_read / hidden_data_length * 20))
        
        # Verify HMAC
        if len(hidden_data) < 32:
            raise ValueError("Hidden data too short to contain HMAC.")
            
        extracted_hmac = hidden_data[-32:]
        hidden_data = hidden_data[:-32]
        
        if not self.verify_hmac(hidden_data, extracted_hmac):
            raise ValueError("File integrity check failed!")
        
        progress_callback(30)
        
        # Continue with the regular extraction logic
        marker_index = hidden_data.find(MAGIC_MARKER)
        if marker_index == -1:
            raise ValueError("No hidden data found in this GIF.")
        start_index = marker_index + len(MAGIC_MARKER)

        if hidden_data[start_index:start_index + 16] != key_hash:
            raise ValueError("Incorrect encryption key!")
        start_index += 16
        if hidden_data[start_index:start_index + 16] != password_hash:
            raise ValueError("Incorrect password!")
        start_index += 16

        file_count = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
        logging.info(f"Extracted file count: {file_count}")
        if file_count > self.MAX_FILES_EMBED:
            raise ValueError(f"Extracted file count ({file_count}) exceeds maximum allowed ({self.MAX_FILES_EMBED}).")
        start_index += 4

        # Process metadata in the same way as the original method
        file_metadata = []
        for i in range(file_count):
            if start_index + 64 > len(hidden_data):
                raise ValueError(f"Metadata for file {i + 1} incomplete.")
            try:
                filename = hidden_data[start_index:start_index + 50].strip().decode('utf-8', errors='replace')
                start_index += 50
                ext = hidden_data[start_index:start_index + 10].strip().decode('utf-8', errors='replace')
                start_index += 10
                data_length = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
                start_index += 4
                file_metadata.append((filename, ext, data_length))
            except Exception as e:
                logging.error(f"Failed to decode metadata for file {i + 1}: {str(e)}")
                raise ValueError(f"Failed to decode metadata for file {i + 1}: {str(e)}")
        
        progress_callback(40)

        # Process files in smaller batches
        files_data = []
        batch_size = 5
        for batch_start in range(0, file_count, batch_size):
            batch_end = min(batch_start + batch_size, file_count)
            for i in range(batch_start, batch_end):
                filename, ext, length = file_metadata[i]
                if start_index + length > len(hidden_data):
                    raise ValueError(f"Data for file {filename} incomplete.")
                encrypted_data = hidden_data[start_index:start_index + length]
                start_index += length
                try:
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    decompressed_data = self.decompress_data(decrypted_data)
                    
                    # Format filename with the date
                    new_filename = f"{filename}_{current_date}"
                    
                    files_data.append((new_filename, ext, decompressed_data))
                    progress_callback(50 + (25 * (i + 1) // file_count))
                    
                    # Clean up memory
                    del encrypted_data, decrypted_data, decompressed_data
                except Exception as e:
                    logging.error(f"Failed to decrypt/decompress file {filename}: {str(e)}")
                    raise ValueError(f"Failed to decrypt/decompress file {filename}: {str(e)}")

        # Process metadata section
        if start_index + 4 > len(hidden_data):
            raise ValueError("Metadata length missing.")
        metadata_length = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
        metadata_start = start_index + 4
        if metadata_start + metadata_length > len(hidden_data):
            raise ValueError("Metadata section incomplete or corrupt.")
        
        encrypted_metadata = hidden_data[metadata_start:metadata_start + metadata_length]
        try:
            metadata = self.cipher.decrypt(encrypted_metadata)
            logging.info(f"Metadata type after decryption: {type(metadata)}")
        except Exception as e:
            logging.error(f"Failed to decrypt metadata: {str(e)}")
            raise ValueError(f"Failed to decrypt metadata: {str(e)}")

        if not metadata.startswith(METADATA_MARKER):
            raise ValueError("No metadata found in this GIF.")
        
        try:
            author = metadata[4:54].strip().decode('utf-8', errors='ignore')
            timestamp = metadata[54:74].strip().decode('utf-8', errors='ignore')
            timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "Invalid timestamp"
        except Exception as e:
            logging.error(f"Failed to decode metadata fields: {str(e)}")
            raise ValueError(f"Failed to decode metadata fields: {str(e)}")

        progress_callback(100)
        return files_data, author, timestamp_readable

    def view_metadata(self, carrier_gif_path, key_str=None, password=None, progress_callback=None):
        """View metadata from the carrier GIF."""
        try:
            # Initialize cipher if password is provided
            if password and key_str:
                cipher = self.get_cipher(key_str)
                if cipher is None:
                    raise ValueError("Failed to initialize cipher with provided key")

            # Read the carrier GIF
            with open(carrier_gif_path, "rb") as gif_file:
                file_data = gif_file.read()

            # Find GIF trailer
            trailer_pos = file_data.rfind(b'\x3B')
            if trailer_pos == -1:
                return "", "N/A"  # No metadata found

            # Get data after trailer
            hidden_data = file_data[trailer_pos + 1:]

            # Find magic marker
            magic_pos = hidden_data.find(MAGIC_MARKER)
            if magic_pos == -1:
                return "", "N/A"  # No metadata found

            # Remove any data before magic marker
            hidden_data = hidden_data[magic_pos:]

            # Remove magic marker
            hidden_data = hidden_data[len(MAGIC_MARKER):]

            # Get password field
            if len(hidden_data) < 100:
                return "", "N/A"
            stored_password = hidden_data[:100].rstrip(b'\0')
            if password and stored_password:
                if stored_password.decode('utf-8', errors='ignore') != password:
                    return "", "N/A"
            hidden_data = hidden_data[100:]

            # Decrypt data if password is provided
            if password and key_str:
                try:
                    hidden_data = self.cipher.decrypt(hidden_data)
                except Exception:
                    return "", "N/A"

            # Skip through files to get to metadata
            if len(hidden_data) < 4:
                return "", "N/A"
            file_count = int.from_bytes(hidden_data[:4], byteorder='big')
            pos = 4

            for _ in range(file_count):
                if pos >= len(hidden_data):
                    return "", "N/A"
                
                # Skip filename
                filename_length = hidden_data[pos]
                pos += 1 + filename_length

                # Skip extension
                if pos >= len(hidden_data):
                    return "", "N/A"
                ext_length = hidden_data[pos]
                pos += 1 + ext_length

                # Skip file data
                if pos + 4 >= len(hidden_data):
                    return "", "N/A"
                data_length = int.from_bytes(hidden_data[pos:pos + 4], byteorder='big')
                pos += 4 + data_length

            # Get metadata
            if pos + 4 >= len(hidden_data):
                return "", "N/A"

            metadata_length = int.from_bytes(hidden_data[pos:pos + 4], byteorder='big')
            pos += 4

            if pos + metadata_length > len(hidden_data):
                return "", "N/A"

            metadata = hidden_data[pos:pos + metadata_length]

            if not metadata.startswith(METADATA_MARKER):
                return "", "N/A"

            # Extract author and timestamp
            author = metadata[4:54].strip().decode('utf-8', errors='ignore')
            timestamp = metadata[54:74].strip().decode('utf-8', errors='ignore')
            timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "N/A"

            if progress_callback:
                progress_callback(100)

            return author or "", timestamp_readable

        except Exception as e:
            logging.error(f"Metadata viewing failed: {str(e)}")
            return "", "N/A"

    def process_extracted_data(self, extracted_data):
        """Process extracted data into individual files."""
        try:
            # Check for magic number at the start
            if not extracted_data.startswith(MAGIC_MARKER):
                raise ValueError("Invalid data format")

            # Skip magic number
            data = extracted_data[4:]

            # Get number of files (4 bytes)
            num_files = int.from_bytes(data[:4], byteorder='big')
            data = data[4:]

            files_data = []
            for _ in range(num_files):
                # Get filename length (1 byte)
                filename_length = data[0]
                data = data[1:]

                # Get filename
                filename = data[:filename_length].decode('utf-8', errors='ignore')
                data = data[filename_length:]

                # Get extension length (1 byte)
                ext_length = data[0]
                data = data[1:]

                # Get extension
                extension = data[:ext_length].decode('utf-8', errors='ignore')
                data = data[ext_length:]

                # Get file size (4 bytes)
                file_size = int.from_bytes(data[:4], byteorder='big')
                data = data[4:]

                # Get file data
                file_data = data[:file_size]
                data = data[file_size:]

                # Add to files list
                files_data.append((filename, extension, file_data))

            return files_data

        except Exception as e:
            raise ValueError(f"Failed to process extracted data: {str(e)}")