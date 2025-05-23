from datetime import datetime
from PIL import Image
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import struct
import hashlib
import zlib
import base64
import logging
import time
import secrets
import numpy as np

# Setup logging
logging.basicConfig(filename='steganography.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class SteganographyLogic:
    """Handles steganography logic for embedding and extracting data in images."""
    def __init__(self):
        self.cipher = None
        self.MAX_FILES_EMBED = 20
        self.MAX_REASONABLE_SIZE = 1024 * 1024 * 100  # 100 MB max
        self.MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
        self.METADATA_MARKER = b'\xCA\xFE\xBA\xBE'

    def generate_key(self):
        """Generate a random encryption key as a string."""
        # Generate a random 32-byte key and encode it as a base64 string
        key_bytes = secrets.token_bytes(32)
        key_str = base64.b64encode(key_bytes).decode('utf-8')
        return key_str
    
    def get_cipher(self, key_str, root=None, key_is_generated=False):
        """
        Initialize the cipher with the provided key or password.
        If key_is_generated is True, use the key as a base64-encoded 32-byte Fernet key.
        If False, derive a Fernet key from the password using PBKDF2HMAC.
        """
        if not key_str:
            if root:
                root.after(0, lambda: root.show_error("Please provide an encryption key or password."))
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
                    salt=b"P673XfybNqgEm9PPBDtoP4CFqroTHRjG.vE94hDftUGXK.AkjHqp-yqmh2DAi3@4D-ewUu@xp_GC7eqegGVXz4MYECgH-8vCumU*",  # Use a constant salt for reproducibility
                    iterations=100000,
                )
                key_bytes = kdf.derive(key_str.encode('utf-8'))
                key = base64.urlsafe_b64encode(key_bytes)
            self.cipher = Fernet(key)
            self.key = key_bytes
            return True
        except Exception as e:
            logging.error("Cipher setup failed:" + str(e))
            if root:
                root.after(0, lambda: root.show_error("Invalid key or password:" + str(e)))
            return False

    def compress_data(self, data):
        """Compress data using zlib."""
        return zlib.compress(data, level=9)

    def decompress_data(self, compressed_data):
        """Decompress data using zlib."""
        try:
            return zlib.decompress(compressed_data)
        except zlib.error as e:
            raise ValueError("Decompression failed")

    def derive_password_hash(self, password):
        """Derive a 32-byte hash from the password using PBKDF2HMAC."""
        if not password:
            return b'\x00' * 32
        salt = b'P673XfybNqgEm9PPBDtoP4CFqroTHRjG.vE94hDftUGXK.AkjHqp-yqmh2DAi3@4D-ewUu@xp_GC7eqegGVXz4MYECgH-8vCumU*'  # Use the same salt as above for consistency
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        return kdf.derive(password.encode('utf-8'))

    def generate_hmac(self, data):
        """Generate an HMAC for the data."""
        h = hmac.HMAC(self.cipher._signing_key, hashes.SHA256())
        h.update(data)
        return h.finalize()

    def verify_hmac(self, data, signature):
        """Verify the HMAC of the data."""
        h = hmac.HMAC(self.cipher._signing_key, hashes.SHA256())
        h.update(data)
        try:
            h.verify(signature)
            return True
        except Exception:
            return False

    def embed_data(self, image_path, data_file_paths, key_str, password, author, update_progress_callback, key_is_generated=False):
        """Embed multiple files into an image."""
        if not self.get_cipher(key_str, None, key_is_generated):
            raise ValueError("Invalid encryption key")
        if len(data_file_paths) > self.MAX_FILES_EMBED:
            raise ValueError(f"Cannot embed more than {self.MAX_FILES_EMBED} files")
        if not os.path.exists(image_path):
            raise ValueError("Carrier image does not exist")
        for path in data_file_paths:
            if not os.path.exists(path):
                raise ValueError("Data file does not exist")
        # Password length validation
        if not key_is_generated:
            if len(password) < 5 or len(password) > 12:
                raise ValueError("Password must be between 5 and 12 characters.")

        try:
            carrier_image = Image.open(image_path).convert('RGB')
            image_array = np.array(carrier_image, dtype=np.uint8)

            if np.any(image_array < 0) or np.any(image_array > 255):
                raise ValueError("Image contains invalid pixel values outside uint8 range (0-255)")
            if image_array.size == 0:
                raise ValueError("Image array is empty")

            key_bytes = self.key
            all_encrypted_data = bytearray()
            file_metadata = []
            file_count = len(data_file_paths)

            # Extract the original carrier image name
            base_name = os.path.splitext(os.path.basename(image_path))[0]

            update_progress_callback(10)
            batch_size = 5
            
            for batch_start in range(0, file_count, batch_size):
                batch_end = min(batch_start + batch_size, file_count)
                for i in range(batch_start, batch_end):
                    path = data_file_paths[i]
                    with open(path, "rb") as data_file:
                        raw_data = data_file.read()
                    # Use the original carrier name in the filename
                    filename = f"{base_name}_{i+1}".encode('utf-8', errors='replace')[:50].ljust(50, b' ')
                    ext = os.path.splitext(path)[1].encode('utf-8', errors='replace')[:10].ljust(10, b' ')
                    compressed_data = self.compress_data(raw_data)
                    encrypted_data = self.cipher.encrypt(compressed_data)
                    file_metadata.append((filename, ext, len(encrypted_data)))
                    all_encrypted_data.extend(encrypted_data)
                    update_progress_callback(10 + (80 * (i + 1) // file_count))
                    del raw_data, compressed_data, encrypted_data

            author_bytes = (author or "N/A").encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata = self.METADATA_MARKER + author_bytes + timestamp
            encrypted_metadata = self.cipher.encrypt(metadata)

            file_metadata_bytes = b"".join(fn + ext + struct.pack(">I", dl) for fn, ext, dl in file_metadata)
            hidden_data = (self.MAGIC_MARKER + hashlib.sha256(key_bytes).digest() +
                           self.derive_password_hash(password) +
                           struct.pack(">I", file_count) + file_metadata_bytes +
                           bytes(all_encrypted_data) + struct.pack(">I", len(encrypted_metadata)) + encrypted_metadata)
            hmac_value = self.generate_hmac(hidden_data)
            hidden_data += hmac_value

            length_prefix = struct.pack(">I", len(hidden_data))
            full_data = length_prefix + hidden_data
            data_bits = ''.join([f'{byte:08b}' for byte in full_data]) + '1111111111111110'

            flat_image = image_array.flatten()
            if len(data_bits) > len(flat_image):
                raise ValueError(f"Data too large for carrier image. Required: {len(data_bits)} bits, Available: {len(flat_image)} bits")


            for i in range(len(data_bits)):
                pixel_value = flat_image[i] & 0xFE  # 0xFE is 11111110 in binary, clears the LSB
                bit_value = int(data_bits[i])
                flat_image[i] = pixel_value | bit_value

            modified_image = flat_image.reshape(image_array.shape)
            update_progress_callback(90)
            return Image.fromarray(modified_image)
        except ValueError as e:
            logging.error("Embedding failed:" + str(e))
            raise
        

    def extract_data(self, image_path, key_str, password, update_progress_callback, carrier_filename=None, key_is_generated=False):
        """Extract multiple files and metadata from an image with custom filename format."""
        if not self.get_cipher(key_str, None, key_is_generated):
            raise ValueError("Invalid encryption key")
        if not os.path.exists(image_path):
            raise ValueError("Carrier image does not exist")

        # Get the current date in YYYY-MM-DD format
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            carrier_image = Image.open(image_path).convert('RGB')
            image_array = np.array(carrier_image, dtype=np.uint8)
            flat_image = image_array.flatten()

            bits = []
            i = 0
            update_progress_callback(10)
            while i < len(flat_image):
                bit = flat_image[i] & 1
                bits.append(str(bit))
                i += 1
                if i >= 16 and ''.join(bits[-16:]) == '1111111111111110':
                    break

            if i >= len(flat_image):
                raise ValueError("Termination sequence not found in image")

            data_bits = bits[:-16]
            byte_array = bytearray()
            for j in range(0, len(data_bits), 8):
                byte = ''.join(data_bits[j:j+8])
                byte_array.append(int(byte, 2))
            full_data = bytes(byte_array)

            update_progress_callback(30)

            if len(full_data) < 4:
                raise ValueError("Invalid data: length prefix missing")
            data_length = struct.unpack(">I", full_data[:4])[0]
            if data_length > self.MAX_REASONABLE_SIZE:
                raise ValueError(f"Data length ({data_length}) exceeds maximum ({self.MAX_REASONABLE_SIZE})")
            hidden_data = full_data[4:4 + data_length]

            hmac_value = hidden_data[-32:]
            data_to_verify = hidden_data[:-32]
            if not self.verify_hmac(data_to_verify, hmac_value):
                raise ValueError("Password Mismatch or Key Mismatch")

            update_progress_callback(40)

            if not hidden_data.startswith(self.MAGIC_MARKER):
                raise ValueError("Invalid data: magic bytes missing")

            key_bytes = self.key
            stored_key_hash = hidden_data[4:36]
            if hashlib.sha256(key_bytes).digest() != stored_key_hash:
                raise ValueError("Password Mismatch or Key Mismatch")

            stored_password_hash = hidden_data[36:68]
            if self.derive_password_hash(password) != stored_password_hash:
                raise ValueError("Password Mismatch or Key Mismatch")

            file_count = struct.unpack(">I", hidden_data[68:72])[0]
            pos = 72

            file_metadata = []
            for _ in range(file_count):
                filename = hidden_data[pos:pos+50]
                ext = hidden_data[pos+50:pos+60]
                data_length = struct.unpack(">I", hidden_data[pos+60:pos+64])[0]
                filename_str = filename.decode('utf-8', errors='replace').strip()
                ext_str = ext.decode('utf-8', errors='replace').strip()
                file_metadata.append((filename_str, ext_str, data_length))
                pos += 64

            encrypted_data_end = pos + sum(dl for _, _, dl in file_metadata)
            all_encrypted_data = hidden_data[pos:encrypted_data_end]
            pos = encrypted_data_end

            metadata_length = struct.unpack(">I", hidden_data[pos:pos+4])[0]
            pos += 4
            encrypted_metadata = hidden_data[pos:pos+metadata_length]

            update_progress_callback(60)

            try:
                metadata = self.cipher.decrypt(encrypted_metadata)
            except InvalidToken:
                raise ValueError("Metadata decryption failed: incorrect key")

            if not metadata.startswith(self.METADATA_MARKER):
                raise ValueError("Invalid metadata: magic bytes missing")
            author = metadata[4:54].decode('utf-8', errors='replace').strip()
            timestamp = metadata[54:74].decode('utf-8', errors='replace').strip()
            timestamp_readable = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S') if timestamp.isdigit() else "Invalid timestamp"

            files_data = []
            pos = 0
            for i, (filename_str, ext_str, data_length) in enumerate(file_metadata):
                encrypted_data = all_encrypted_data[pos:pos+data_length]
                pos += data_length
                try:
                    compressed_data = self.cipher.decrypt(encrypted_data)
                    raw_data = self.decompress_data(compressed_data)
                    # Use the filename stored in metadata, which includes the original carrier name
                    new_filename = f"{filename_str}_{current_date}"
                    files_data.append((new_filename, ext_str, raw_data))
                    update_progress_callback(60 + (30 * (i + 1) // file_count))
                except InvalidToken:
                    raise ValueError(f"Decryption failed for file {filename_str}")
                except zlib.error as e:
                    raise ValueError(f"Decompression failed for file {filename_str}")
                
            update_progress_callback(90)
            return files_data, author, timestamp_readable
        
        except ValueError as e:
            logging.error("Extraction failed:" + str(e))
            raise
        except Exception as e:
            logging.error("Extraction failed")
            raise ValueError("Extraction failed:" + str(e))