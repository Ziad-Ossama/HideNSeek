from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from datetime import datetime
from tkinter import messagebox
import zlib
import os
import hmac
import hashlib
import struct
import time
import logging
import secrets
import base64

# Setup logging for debugging
logging.basicConfig(filename='steganography.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class GIFSteganographyLogic:
    """Handles the core steganography operations for GIFs (embedding, extracting, etc.)."""
    def __init__(self):
        self.key = None
        self.cipher = None
        self.hmac_key = None
        self.MAX_FILES_EMBED = 20  # Maximum files that can be embedded
        self.MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
        self.METADATA_MARKER = b'\xCA\xFE\xBA\xBE'

    def generate_key(self):
        """Generate a random encryption key as a string."""
        # Generate a random 32-byte key and encode it as a base64 string
        key_bytes = secrets.token_bytes(32)
        key_str = base64.b64encode(key_bytes).decode('utf-8')
        return key_str
    
    def generate_hmac(self, data):
        """Generate HMAC for data integrity."""
        return hmac.new(self.hmac_key, data, hashlib.sha256).digest()

    def verify_hmac(self, data, expected_hmac):
        """Verify HMAC for data integrity."""
        return hmac.compare_digest(self.generate_hmac(data), expected_hmac)

    def get_cipher(self, key_str, root=None, key_is_generated=False):
        """
        Initialize the cipher with the provided key or password.
        If key_is_generated is True, use the key as a base64-encoded 32-byte Fernet key.
        If False, derive a Fernet key from the password using PBKDF2HMAC.
        """
        if not key_str:
            if root:
                root.after(0, lambda: messagebox.showerror("Error", "Please provide an encryption key."))
            return False
        key_str = key_str.strip()
        try:
            if key_is_generated:
                # Use the generated key directly (must be base64, 32 bytes)
                key_bytes = base64.b64decode(key_str)
                if len(key_bytes) != 32:
                    raise ValueError("Generated key must be 32 bytes (base64-encoded).")
                key = base64.urlsafe_b64encode(key_bytes)
            else:
                # Derive a Fernet key from the password
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"YrLgT7hpEq2bYw!!7WC9tW8ogVVLhowXv9-iko4MghAuXixm34d6TdtYRA*9ZWiLi7aLWLNw77uEMAoCPZZVd3Y*RT7no_7@pYHm",  # Use a constant salt for reproducibility
                    iterations=100000,
                )
                key_bytes = kdf.derive(key_str.encode('utf-8'))
                key = base64.urlsafe_b64encode(key_bytes)
            self.cipher = Fernet(key)
            # HMAC key can be derived from key_bytes or key_str as before
            self.hmac_key = hashlib.sha256(key_bytes).digest()
            self.key = key_bytes
            return True
        except Exception as e:
            logging.error("Cipher setup failed:" + str(e))
            if root:
                root.after(0, lambda: messagebox.showerror("Error", "Invalid key or password:" + str(e)))
            return False

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

    def split_gif_data(self, data):
        """Split the GIF data into the valid GIF part and the appended hidden data."""
        trailer_pos = self.find_gif_trailer(data)
        if trailer_pos == -1:
            raise ValueError("Invalid GIF: Trailer byte (0x3B) not found.")
        gif_part = data[:trailer_pos + 1]
        remaining_data = data[trailer_pos + 1:] if trailer_pos + 1 < len(data) else b""
        logging.info(f"Remaining data size after GIF trailer: {len(remaining_data)} bytes")

        if len(remaining_data) == 0:
            raise ValueError("No hidden data found after GIF trailer.")

        # Check for magic marker before trusting the length
        if len(remaining_data) < 8:
            raise ValueError("No hidden data found after GIF trailer (insufficient data for length and marker).")

        hidden_data_length = struct.unpack(">I", remaining_data[:4])[0]
        # Check for magic marker
        if not remaining_data[4:8] == self.MAGIC_MARKER:
            raise ValueError("No valid stego data found after GIF trailer (magic marker missing).")

        available_length = len(remaining_data) - 4
        logging.info(f"Parsed hidden data length: {hidden_data_length} bytes, Available: {available_length} bytes")

        # Adjust the reasonable length to be more appropriate for typical use
        MAX_REASONABLE_LENGTH = 1024 * 1024 * 1000  # 1000 MB max 
        if hidden_data_length > MAX_REASONABLE_LENGTH:
            raise ValueError(f"Hidden data length ({hidden_data_length} bytes) exceeds maximum allowed ({MAX_REASONABLE_LENGTH} bytes). Possible data corruption or incorrect file.")

        if hidden_data_length > available_length:
            raise ValueError(f"Hidden data length ({hidden_data_length} bytes) exceeds available data ({available_length} bytes). File may be corrupted or not properly embedded.")

        hidden_data = remaining_data[4:4 + hidden_data_length]
        if not hidden_data.startswith(self.MAGIC_MARKER):
            raise ValueError("Hidden data does not start with magic marker. File may not contain embedded data or is corrupted.")

        return gif_part, hidden_data

    def embed_data(self, carrier_gif_path, data_paths, key_str, password, author, progress_callback, key_is_generated=False):
        """Embed data into the carrier GIF."""
        if not self.get_cipher(key_str, None, key_is_generated):
            raise ValueError("Invalid Encryption key")
        if len(data_paths) > self.MAX_FILES_EMBED:
            raise ValueError(f"Cannot Embed more than {self.MAX_FILES_EMBED} files.")
        password_hash = self.derive_password_hash(password) if password else b'\x00' * 16
        key_hash = hashlib.sha256(self.key).digest()[:16]

        with open(carrier_gif_path, "rb") as gif_file:
            file_data = gif_file.read()
        trailer_pos = self.find_gif_trailer(file_data)
        if trailer_pos == -1:
            raise ValueError("Invalid GIF: Trailer byte (0x3B) not found.")
        gif_part = file_data[:trailer_pos + 1]
        logging.info(f"GIF part size: {len(gif_part)} bytes")

        base_name = os.path.splitext(os.path.basename(carrier_gif_path))[0]
        all_encrypted_data = bytearray()
        file_metadata = []
        file_count = len(data_paths)

        batch_size = 5
        for batch_start in range(0, file_count, batch_size):
            batch_end = min(batch_start + batch_size, file_count)
            for i in range(batch_start, batch_end):
                path = data_paths[i]
                with open(path, "rb") as data_file:
                    raw_data = data_file.read()
                filename = f"{base_name}_{i+1}".encode('utf-8', errors='replace')[:50].ljust(50, b' ')
                ext = os.path.splitext(path)[1].encode('utf-8', errors='replace')[:10].ljust(10, b' ')
                compressed_data = self.compress_data(raw_data)
                encrypted_data = self.cipher.encrypt(compressed_data)
                file_metadata.append((filename, ext, len(encrypted_data)))
                all_encrypted_data.extend(encrypted_data)
                progress_callback(10 + (80 * (i + 1) // file_count))
            del raw_data, compressed_data, encrypted_data

        author_bytes = author.strip().encode('utf-8', errors='replace')[:50].ljust(50, b' ')
        timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
        metadata = self.METADATA_MARKER + author_bytes + timestamp
        encrypted_metadata = self.cipher.encrypt(metadata)

        file_metadata_bytes = b"".join(fn + ext + struct.pack(">I", dl) for fn, ext, dl in file_metadata)
        hidden_data = (self.MAGIC_MARKER + key_hash + password_hash +
                       struct.pack(">I", file_count) + file_metadata_bytes +
                       bytes(all_encrypted_data) + struct.pack(">I", len(encrypted_metadata)) + encrypted_metadata)
        hmac_value = self.generate_hmac(hidden_data)
        hidden_data += hmac_value

        # Log the hidden data size before writing
        logging.info(f"Hidden data size: {len(hidden_data)} bytes")
        length_prefix = struct.pack(">I", len(hidden_data))
        output_data = gif_part + length_prefix + hidden_data
        logging.info(f"Total output size: {len(output_data)} bytes")

        return output_data

    def extract_data(self, carrier_gif_path, key_str, password, progress_callback):
        """Extract data from the carrier GIF."""
        if not self.get_cipher(key_str):
            raise ValueError("Invalid encryption key")

        password_hash = self.derive_password_hash(password) if password else b'\x00' * 16
        key_hash = hashlib.sha256(self.key).digest()[:16]

        # Get the current date in YYYY-MM-DD format for consistent naming
        current_date = datetime.now().strftime('%Y-%m-%d')

        with open(carrier_gif_path, "rb") as gif_file:
            file_data = gif_file.read()
        logging.info(f"GIF size: {len(file_data)} bytes")
        progress_callback(10)

        try:
            _, hidden_data = self.split_gif_data(file_data)
        except ValueError as e:
            logging.error(f"Failed to split GIF data: {e}")
            raise

        if len(hidden_data) < 32:
            raise ValueError("Hidden data too short to contain HMAC.")
        
        extracted_hmac = hidden_data[-32:]
        hidden_data = hidden_data[:-32]
        if not self.verify_hmac(hidden_data, extracted_hmac):
            logging.error("HMAC verification failed")
            raise ValueError("Password Mismatch or Key Mismatch")

        marker_index = hidden_data.find(self.MAGIC_MARKER)
        if marker_index == -1:
            raise ValueError("No hidden data found in this GIF.")
        start_index = marker_index + len(self.MAGIC_MARKER)

        if hidden_data[start_index:start_index + 16] != key_hash:
            raise ValueError("Password Mismatch or Key Mismatch")
        start_index += 16
        if hidden_data[start_index:start_index + 16] != password_hash:
            raise ValueError("Password Mismatch or Key Mismatch")
        start_index += 16

        file_count = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
        logging.info(f"Extracted file count: {file_count}")
        if file_count > self.MAX_FILES_EMBED:
            raise ValueError(f"Extracted file count ({file_count}) exceeds maximum allowed ({self.MAX_FILES_EMBED}).")
        start_index += 4

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
                    
                    new_filename = f"{filename}_{current_date}"
                    
                    files_data.append((new_filename, ext, decompressed_data))
                    progress_callback(50 + (25 * (i + 1) // file_count))
                except Exception as e:
                    logging.error(f"Failed to decrypt/decompress file {filename}: {str(e)}")
                    raise ValueError(f"Failed to decrypt/decompress file {filename}: {str(e)}")
                finally:
                    del encrypted_data, decrypted_data, decompressed_data

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
            raise ValueError(f"Failed to decrypt metadata:" + str(e))

        if not metadata.startswith(self.METADATA_MARKER):
            raise ValueError("No metadata found in this GIF.")
        
        try:
            author = metadata[4:54].strip().decode('utf-8', errors='replace')
            timestamp = metadata[54:74].strip().decode('utf-8', errors='replace')
            timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "Invalid timestamp"
        except Exception as e:
            logging.error(f"Failed to decode metadata fields:" + str(e))
            raise ValueError(f"Failed to decode metadata fields:" + str(e))

        progress_callback(100)
        return files_data, author, timestamp_readable

    def view_metadata(self, carrier_gif_path, key_str, password, progress_callback):
        """View metadata from the carrier GIF."""
        if not self.get_cipher(key_str):
            raise ValueError("Invalid encryption key")

        password_hash = self.derive_password_hash(password) if password else b'\x00' * 16
        key_hash = hashlib.sha256(self.key).digest()[:16]

        with open(carrier_gif_path, "rb") as gif_file:
            file_data = gif_file.read()
        logging.info(f"GIF size: {len(file_data)} bytes")
        progress_callback(10)

        _, hidden_data = self.split_gif_data(file_data)

        if len(hidden_data) < 32:
            raise ValueError("Hidden data too short to contain HMAC.")
        extracted_hmac = hidden_data[-32:]
        hidden_data = hidden_data[:-32]
        computed_hmac = self.generate_hmac(hidden_data)
        logging.info(f"Extracted HMAC: {extracted_hmac.hex()}")
        logging.info(f"Computed HMAC: {computed_hmac.hex()}")
        if not self.verify_hmac(hidden_data, extracted_hmac):
            raise ValueError("File integrity check failed!")

        marker_index = hidden_data.find(self.MAGIC_MARKER)
        if marker_index == -1:
            raise ValueError("No hidden data found in this GIF.")
        start_index = marker_index + len(self.MAGIC_MARKER)

        if hidden_data[start_index:start_index + 16] != key_hash:
            raise ValueError("Password Mismatch or Key Mismatch")
        start_index += 16
        if hidden_data[start_index:start_index + 16] != password_hash:
            raise ValueError("Password Mismatch or Key Mismatch")
        start_index += 16

        file_count = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
        start_index += 4

        data_length_total = 0
        for i in range(file_count):
            if start_index + 64 > len(hidden_data):
                raise ValueError(f"Metadata for file {i + 1} incomplete.")
            start_index += 50  # Skip filename
            start_index += 10  # Skip extension
            data_length = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
            start_index += 4
            data_length_total += data_length
        progress_callback(50)

        start_index += data_length_total

        if start_index + 4 > len(hidden_data):
            raise ValueError("Metadata length missing.")
        metadata_length = struct.unpack(">I", hidden_data[start_index:start_index + 4])[0]
        metadata_start = start_index + 4
        if metadata_start + metadata_length > len(hidden_data):
            raise ValueError("Metadata section incomplete or corrupt.")
        encrypted_metadata = hidden_data[metadata_start:metadata_start + metadata_length]
        metadata = self.cipher.decrypt(encrypted_metadata)
        if not metadata.startswith(self.METADATA_MARKER):
            raise ValueError("No metadata found in this GIF.")
        author = metadata[4:54].strip().decode('utf-8', errors='replace')
        timestamp = metadata[54:74].strip().decode('utf-8')
        timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "Invalid timestamp"

        progress_callback(100)
        return author, timestamp_readable , file_count