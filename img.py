import numpy as np
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
from datetime import datetime
import secrets
from base64 import b64encode, b64decode
import io
import gc

# Setup logging
logging.basicConfig(filename='steganography.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class SteganographyLogic:
    """Handles steganography logic for embedding and extracting data in images."""
    def __init__(self):
        self.cipher = None
        self.key = None  # Store key in memory
        self.MAX_FILES_EMBED = 40
        self.MAX_REASONABLE_SIZE = 1024 * 1024 * 500  # 500 MB max
        self.MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
        self.METADATA_MARKER = b'\xCA\xFE\xBA\xBE'

    def generate_key(self):
        """Generate a random encryption key as a string."""
        # Generate a random 32-byte key and encode it as a base64 string
        key_bytes = secrets.token_bytes(32)
        self.key = key_bytes  # Store the raw key bytes in memory
        key_str = b64encode(key_bytes).decode('utf-8')
        return key_str
    
    def get_cipher(self, key_str, root=None):
        """Initialize the cipher with the provided key."""
        if not key_str:
            if root:
                root.after(0, lambda: root.show_error("Please provide an encryption key."))
            return None
        try:
            key_bytes = key_str.encode('utf-8')
            self.key = key_bytes  # Store the key bytes in memory
            key = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
            self.cipher = Fernet(key)
            return self.cipher
        except Exception as e:
            logging.error(f"Cipher setup failed: {str(e)}")
            if root:
                root.after(0, lambda: root.show_error(f"Invalid encryption key: {str(e)}"))
            self.cipher = None
            self.key = None
            return None

    def compress_data(self, data):
        """Compress data using zlib."""
        return zlib.compress(data, level=9)

    def decompress_data(self, compressed_data):
        """Decompress data using zlib."""
        try:
            return zlib.decompress(compressed_data)
        except zlib.error as e:
            raise ValueError(f"Decompression failed: {str(e)}")

    def derive_password_hash(self, password):
        """Derive a hash from the password for authentication."""
        if not password:
            return b'\x00' * 32
        
        # Use a fixed salt for consistency
        salt = b"HideNSeek_v1_2024_Static_Salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))

    def generate_hmac(self, data):
        """Generate HMAC for data integrity."""
        if not self.key:
            raise ValueError("Key not initialized")
        
        # Create a new HMAC instance with SHA256
        h = hmac.new(self.key, digestmod=hashlib.sha256)
        h.update(data)
        return h.digest()

    def verify_hmac(self, data, signature):
        """Verify HMAC for data integrity."""
        if not self.key:
            raise ValueError("Key not initialized")
        
        # Create a new HMAC instance with SHA256
        h = hmac.new(self.key, digestmod=hashlib.sha256)
        h.update(data)
        expected_hmac = h.digest()
        
        # Use constant-time comparison
        return hmac.compare_digest(expected_hmac, signature)

    def _bytes_to_bits(self, data):
        """Convert bytes to a list of bits."""
        return [int(b) for byte in data for b in format(byte, '08b')]

    def _bits_to_bytes(self, bits):
        """Convert a list of bits to bytes."""
        return bytes(int(''.join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits), 8))

    def process_extracted_data(self, extracted_data):
        """Process extracted data into individual files."""
        try:
            # Check for magic number at the start
            if not extracted_data.startswith(self.MAGIC_MARKER):
                raise ValueError("Invalid data format: Missing magic marker")

            # Skip magic number
            data = extracted_data[len(self.MAGIC_MARKER):]

            # Get number of files (4 bytes)
            if len(data) < 4:
                raise ValueError("Invalid data format: Missing file count")
            num_files = int.from_bytes(data[:4], byteorder='big')
            if num_files <= 0 or num_files > self.MAX_FILES_EMBED:
                raise ValueError(f"Invalid file count: {num_files}")
            data = data[4:]

            files_data = []
            for i in range(num_files):
                # Get filename length (1 byte)
                if len(data) < 1:
                    raise ValueError(f"Invalid data format: Missing filename length for file {i+1}")
                filename_length = data[0]
                data = data[1:]

                # Get filename
                if len(data) < filename_length:
                    raise ValueError(f"Invalid data format: Incomplete filename for file {i+1}")
                filename = data[:filename_length].decode('utf-8', errors='ignore')
                data = data[filename_length:]

                # Get extension length (1 byte)
                if len(data) < 1:
                    raise ValueError(f"Invalid data format: Missing extension length for file {i+1}")
                ext_length = data[0]
                data = data[1:]

                # Get extension
                if len(data) < ext_length:
                    raise ValueError(f"Invalid data format: Incomplete extension for file {i+1}")
                extension = data[:ext_length].decode('utf-8', errors='ignore')
                data = data[ext_length:]

                # Get file size (4 bytes)
                if len(data) < 4:
                    raise ValueError(f"Invalid data format: Missing file size for file {i+1}")
                file_size = int.from_bytes(data[:4], byteorder='big')
                data = data[4:]

                # Get file data
                if len(data) < file_size:
                    raise ValueError(f"Invalid data format: Incomplete file data for file {i+1}")
                file_data = data[:file_size]
                data = data[file_size:]

                # Add to files list
                files_data.append((filename, extension, file_data))

            return files_data

        except Exception as e:
            raise ValueError(f"Failed to process extracted data: {str(e)}")

    def extract_data_optimized(self, carrier_path, key_str, password, progress_callback, chunk_size=1024*1024):
        """Extract data from carrier image with optimized memory usage."""
        try:
            # Initialize progress
            if progress_callback:
                progress_callback(0)

            # Initialize cipher with proper key handling
            if isinstance(key_str, str):
                key_bytes = key_str.encode('utf-8')
            else:
                key_bytes = key_str
            
            self.key = key_bytes  # Store the raw key for HMAC
            key = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
            self.cipher = Fernet(key)
            if not self.cipher:
                raise ValueError("Failed to initialize cipher")

            # Read carrier image
            carrier = Image.open(carrier_path)
            if carrier.mode != 'RGB':
                carrier = carrier.convert('RGB')

            width, height = carrier.size
            total_pixels = width * height * 3  # RGB channels

            # Process image in chunks to extract bits
            chunk_height = 1000  # Process 1000 rows at a time
            extracted_bits = []
            
            for y_start in range(0, height, chunk_height):
                y_end = min(y_start + chunk_height, height)
                chunk = carrier.crop((0, y_start, width, y_end))
                chunk_array = np.array(chunk, dtype=np.uint8)
                
                # Extract bits from this chunk
                chunk_bits = [pixel & 1 for pixel in chunk_array.flat]
                extracted_bits.extend(chunk_bits)
                
                # Update progress
                if progress_callback:
                    progress = int(25 * y_end / height)
                    progress_callback(progress)
                
                # Clean up chunk memory
                del chunk
                del chunk_array
                del chunk_bits

            # Find termination sequence and trim excess bits
            bit_string = ''.join(map(str, extracted_bits))
            term_sequence = '1111111111111110'
            term_pos = bit_string.find(term_sequence)
            if term_pos != -1:
                extracted_bits = extracted_bits[:term_pos]

            # Convert bits to bytes efficiently
            byte_count = len(extracted_bits) // 8
            extracted_bytes = bytearray(byte_count)
            for i in range(byte_count):
                byte_bits = extracted_bits[i*8:(i+1)*8]
                extracted_bytes[i] = int(''.join(map(str, byte_bits)), 2)
            
            del extracted_bits  # Free memory

            if progress_callback:
                progress_callback(30)

            # Get the length prefix
            if len(extracted_bytes) < 4:
                raise ValueError("Invalid data format: Missing length prefix")
            data_length = int.from_bytes(extracted_bytes[:4], byteorder='big')
            if data_length <= 0 or data_length > len(extracted_bytes) - 4:
                raise ValueError("Invalid data length")

            # Get the actual data
            hidden_data = extracted_bytes[4:4+data_length]
            if not hidden_data.startswith(self.MAGIC_MARKER):
                raise ValueError("Invalid data format: Missing magic marker")

            # Separate HMAC from data
            data_without_hmac = hidden_data[:-32]
            hmac_value = hidden_data[-32:]

            # Verify HMAC first
            if not self.verify_hmac(data_without_hmac, hmac_value):
                raise ValueError("Data integrity check failed")

            # Skip magic marker and get key hash
            pos = len(self.MAGIC_MARKER)
            stored_key_hash = data_without_hmac[pos:pos+32]
            if hashlib.sha256(key_bytes).digest() != stored_key_hash:
                raise ValueError("Invalid key")
            pos += 32

            # Get password hash
            stored_pass_hash = data_without_hmac[pos:pos+32]
            if self.derive_password_hash(password) != stored_pass_hash:
                raise ValueError("Invalid password")
            pos += 32

            # Get the rest of the data
            encrypted_data = data_without_hmac[pos:]

            if progress_callback:
                progress_callback(40)

            # Decrypt the data in chunks if it's large
            try:
                if len(encrypted_data) > 10 * 1024 * 1024:  # 10MB
                    chunk_size = 5 * 1024 * 1024  # 5MB chunks
                    decrypted_data = bytearray()
                    for i in range(0, len(encrypted_data), chunk_size):
                        chunk = encrypted_data[i:i+chunk_size]
                        try:
                            decrypted_chunk = self.cipher.decrypt(bytes(chunk))
                            decrypted_data.extend(decrypted_chunk)
                        except Exception as e:
                            raise ValueError(f"Chunk decryption failed: {str(e)}")
                        if progress_callback:
                            progress = 40 + (10 * (i + chunk_size) // len(encrypted_data))
                            progress_callback(progress)
                else:
                    decrypted_data = self.cipher.decrypt(bytes(encrypted_data))
            except Exception as e:
                raise ValueError(f"Decryption failed: {str(e)}")

            if progress_callback:
                progress_callback(50)

            # Process the extracted data
            try:
                files_data = self.process_extracted_data(bytes(decrypted_data))
            except Exception as e:
                raise ValueError(f"Failed to process decrypted data: {str(e)}")
            del decrypted_data  # Free memory
            
            # Save extracted files
            extracted_files = []
            output_dir = os.path.dirname(carrier_path)
            os.makedirs(output_dir, exist_ok=True)
            
            for i, (filename, extension, file_data) in enumerate(files_data):
                # Create output filename with date
                output_filename = f"{filename}_{datetime.now().strftime('%Y-%m-%d')}{extension}"
                output_path = os.path.join(output_dir, output_filename)
                
                # Write file in chunks if it's large
                with open(output_path, 'wb') as f:
                    if len(file_data) > 10 * 1024 * 1024:  # 10MB
                        for j in range(0, len(file_data), chunk_size):
                            f.write(file_data[j:j+chunk_size])
                    else:
                        f.write(file_data)
                
                extracted_files.append(output_path)

                if progress_callback:
                    progress_callback(50 + (40 * (i + 1) // len(files_data)))

            if progress_callback:
                progress_callback(100)

            return extracted_files

        except Exception as e:
            logging.error(f"Extraction failed: {str(e)}")
            raise ValueError(f"Extraction failed: {str(e)}")
        finally:
            # Clean up
            gc.collect()

    def embed_data_optimized(self, carrier_path, data_paths, key_str=None, password=None, author=None, progress_callback=None):
        """Embed data into carrier image with optimized memory usage."""
        try:
            # Initialize progress
            if progress_callback:
                progress_callback(0)

            # Initialize cipher if password is provided
            if password and key_str:
                if not self.cipher:
                    self.get_cipher(key_str)
                if not self.cipher:
                    raise ValueError("Failed to initialize encryption")

            # Prepare the data to embed
            all_data = bytearray()
            
            # Add magic marker
            all_data.extend(self.MAGIC_MARKER)
            
            # Add password field (padded to 100 bytes)
            if password:
                password_bytes = password.encode('utf-8')
                if len(password_bytes) > 100:
                    raise ValueError("Password too long (max 100 bytes)")
                password_bytes = password_bytes.ljust(100, b'\0')
            else:
                password_bytes = b'\0' * 100
            all_data.extend(password_bytes)
            
            # Add number of files
            num_files = len(data_paths)
            if num_files <= 0:
                raise ValueError("No files to embed")
            if num_files > self.MAX_FILES_EMBED:
                raise ValueError(f"Too many files (max {self.MAX_FILES_EMBED})")
            all_data.extend(num_files.to_bytes(4, byteorder='big'))
            
            # Process each file
            total_size = 0
            for file_path in data_paths:
                file_size = os.path.getsize(file_path)
                if file_size > 10 * 1024 * 1024:  # 10 MB per file limit
                    raise ValueError(f"File too large (max 10MB): {file_path}")
                total_size += file_size

            if total_size > 100 * 1024 * 1024:  # 100 MB total limit
                raise ValueError("Total file size exceeds 100MB limit")

            for i, file_path in enumerate(data_paths):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    
                # Get filename and extension
                filename = os.path.splitext(os.path.basename(file_path))[0]
                extension = os.path.splitext(file_path)[1]
                
                # Validate filename and extension
                if len(filename) > 255:
                    raise ValueError(f"Filename too long (max 255 chars): {filename}")
                if len(extension) > 10:
                    raise ValueError(f"Extension too long (max 10 chars): {extension}")
                
                # Add filename length and filename
                name_bytes = filename.encode('utf-8')
                all_data.append(len(name_bytes))
                all_data.extend(name_bytes)
                
                # Add extension length and extension
                ext_bytes = extension.encode('utf-8')
                all_data.append(len(ext_bytes))
                all_data.extend(ext_bytes)
                
                # Add file size and data
                all_data.extend(len(file_data).to_bytes(4, byteorder='big'))
                all_data.extend(file_data)
                
                if progress_callback:
                    progress_callback(10 + (30 * (i + 1) // len(data_paths)))

            # Add metadata
            metadata = bytearray()
            metadata.extend(self.METADATA_MARKER)
            
            # Add author name (optional)
            author_bytes = (author or "").encode('utf-8')[:50].ljust(50, b' ')
            metadata.extend(author_bytes)
            
            # Add timestamp
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata.extend(timestamp)

            # Add metadata length and data
            all_data.extend(len(metadata).to_bytes(4, byteorder='big'))
            all_data.extend(metadata)

            # Encrypt data if password is provided
            if password and key_str:
                encrypted_data = self.cipher.encrypt(bytes(all_data))
                all_data = encrypted_data

            if progress_callback:
                progress_callback(50)

            # Convert data to bits
            data_bits = self._bytes_to_bits(all_data)

            # Read carrier image
            carrier = Image.open(carrier_path)
            if carrier.mode != 'RGB':
                carrier = carrier.convert('RGB')

            # Check if carrier has enough capacity
            width, height = carrier.size
            total_pixels = width * height * 3
            if len(data_bits) > total_pixels:
                raise ValueError("Carrier image too small for data")

            # Process image in chunks
            chunk_size = min(2 * 1024 * 1024, total_pixels // 4)  # 2MB chunks or quarter of image
            bit_index = 0

            for y_start in range(0, height, chunk_size // width + 1):
                y_end = min(y_start + chunk_size // width + 1, height)
                chunk = carrier.crop((0, y_start, width, y_end))
                pixels = list(chunk.getdata())
                modified_pixels = []

                for pixel in pixels:
                    if bit_index >= len(data_bits):
                        modified_pixels.append(pixel)
                        continue

                    r, g, b = pixel
                    new_pixel = [r, g, b]

                    for i in range(3):
                        if bit_index < len(data_bits):
                            new_pixel[i] = (new_pixel[i] & ~1) | data_bits[bit_index]
                            bit_index += 1

                    modified_pixels.append(tuple(new_pixel))

                # Update chunk with modified pixels
                chunk.putdata(modified_pixels)
                carrier.paste(chunk, (0, y_start))

                # Update progress
                if progress_callback:
                    progress = 50 + int(40 * y_end / height)
                    progress_callback(progress)

                # Clean up chunk memory
                del chunk
                del pixels
                del modified_pixels

            # Save the modified image
            carrier.save(carrier_path, "PNG")

            if progress_callback:
                progress_callback(100)

            return True

        except Exception as e:
            logging.error(f"Embedding failed: {str(e)}")
            raise ValueError(f"Embedding failed: {str(e)}")

    def embed_data(self, image_path, data_file_paths, key_str, password, author, update_progress_callback):
        """Embed multiple files into an image."""
        try:
            # Initialize key and cipher
            if isinstance(key_str, str):
                self.key = key_str.encode('utf-8')
            else:
                self.key = key_str
            
            fernet_key = base64.urlsafe_b64encode(hashlib.sha256(self.key).digest())
            self.cipher = Fernet(fernet_key)
            if not self.cipher:
                raise ValueError("Failed to initialize cipher")

            # Validate inputs
            if len(data_file_paths) > self.MAX_FILES_EMBED:
                raise ValueError(f"Cannot embed more than {self.MAX_FILES_EMBED} files")
            if not os.path.exists(image_path):
                raise ValueError("Carrier image does not exist")
            for path in data_file_paths:
                if not os.path.exists(path):
                    raise ValueError(f"Data file does not exist: {path}")

            # Calculate total data size first
            total_data_size = sum(os.path.getsize(path) for path in data_file_paths)
            if total_data_size > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError("Total data size exceeds 100MB limit")

            # Process carrier image
            carrier_image = Image.open(image_path).convert('RGB')
            width, height = carrier_image.size
            total_pixels = width * height * 3  # RGB channels
            available_bits = total_pixels

            # Process files in batches
            all_encrypted_data = bytearray()
            file_metadata = []
            update_progress_callback(10)

            batch_size = 5
            for batch_start in range(0, len(data_file_paths), batch_size):
                batch_end = min(batch_start + batch_size, len(data_file_paths))
                batch = data_file_paths[batch_start:batch_end]
                
                for i, path in enumerate(batch):
                    with open(path, "rb") as data_file:
                        raw_data = data_file.read()
                    
                    filename = os.path.splitext(os.path.basename(path))[0].encode('utf-8', errors='replace')[:50].ljust(50, b' ')
                    ext = os.path.splitext(path)[1].encode('utf-8', errors='replace')[:10].ljust(10, b' ')
                    
                    # Process data in smaller chunks if file is large
                    if len(raw_data) > 10 * 1024 * 1024:  # 10MB
                        chunk_size = 5 * 1024 * 1024  # 5MB chunks
                        compressed_data = bytearray()
                        for j in range(0, len(raw_data), chunk_size):
                            chunk = raw_data[j:j+chunk_size]
                            compressed_chunk = self.compress_data(chunk)
                            compressed_data.extend(compressed_chunk)
                    else:
                        compressed_data = self.compress_data(raw_data)
                    
                    try:
                        encrypted_data = self.cipher.encrypt(bytes(compressed_data))
                        file_metadata.append((filename, ext, len(encrypted_data)))
                        all_encrypted_data.extend(encrypted_data)
                    except Exception as e:
                        raise ValueError(f"Encryption failed for file {os.path.basename(path)}: {str(e)}")
                    
                    # Clean up
                    del raw_data
                    del compressed_data
                    del encrypted_data
                    
                    global_index = batch_start + i
                    update_progress_callback(10 + (60 * (global_index + 1) // len(data_file_paths)))

            # Prepare metadata
            author_bytes = (author or "N/A").encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata = self.METADATA_MARKER + author_bytes + timestamp
            encrypted_metadata = self.cipher.encrypt(metadata)

            # Prepare the data structure
            file_metadata_bytes = b"".join(fn + ext + struct.pack(">I", dl) for fn, ext, dl in file_metadata)
            data_block = (self.MAGIC_MARKER + 
                       hashlib.sha256(self.key).digest() +
                       self.derive_password_hash(password) +
                       struct.pack(">I", len(data_file_paths)) + 
                       file_metadata_bytes +
                       bytes(all_encrypted_data) + 
                       struct.pack(">I", len(encrypted_metadata)) + 
                       encrypted_metadata)
            
            # Generate HMAC for the data block
            hmac_value = self.generate_hmac(data_block)
            
            # Combine everything
            hidden_data = data_block + hmac_value

            # Calculate total required bits
            total_required_bits = (len(hidden_data) + 4) * 8 + 16  # +4 for length prefix, +16 for termination
            if total_required_bits > available_bits:
                raise ValueError(f"Data too large for carrier image. Required: {total_required_bits} bits, Available: {available_bits} bits")

            # Prepare final data
            length_prefix = struct.pack(">I", len(hidden_data))
            full_data = length_prefix + hidden_data
            data_bits = ''.join([f'{byte:08b}' for byte in full_data]) + '1111111111111110'

            # Process image in chunks
            chunk_height = 1000  # Process 1000 rows at a time
            modified_image = Image.new('RGB', (width, height))
            
            for y_start in range(0, height, chunk_height):
                y_end = min(y_start + chunk_height, height)
                chunk = carrier_image.crop((0, y_start, width, y_end))
                chunk_array = np.array(chunk, dtype=np.uint8)
                chunk_flat = chunk_array.flatten()
                
                # Calculate bit indices for this chunk
                start_idx = y_start * width * 3
                end_idx = min(y_end * width * 3, len(data_bits))
                chunk_bits = data_bits[start_idx:end_idx]
                
                # Modify only the required pixels
                for i, bit in enumerate(chunk_bits):
                    if i < len(chunk_flat):
                        chunk_flat[i] = (chunk_flat[i] & 0xFE) | int(bit)
                
                # Reshape and update the image
                chunk_array = chunk_flat.reshape(chunk_array.shape)
                modified_chunk = Image.fromarray(chunk_array)
                modified_image.paste(modified_chunk, (0, y_start))
                
                update_progress_callback(70 + (20 * y_end // height))
                
                # Clean up
                del chunk_array
                del chunk_flat
                del modified_chunk

            update_progress_callback(90)
            return modified_image

        except Exception as e:
            logging.error(f"Embedding failed: {str(e)}")
            raise ValueError(f"Embedding failed: {str(e)}")
        finally:
            # Clean up
            gc.collect()

    def embed_batch(self, image_path, data_file_paths, key_str, password, author, progress_range=None):
        """Process a batch of files for embedding with better memory efficiency."""
        if not self.get_cipher(key_str):
            raise ValueError("Invalid encryption key")
            
        if not os.path.exists(image_path):
            raise ValueError("Carrier image does not exist")
        
        # This runs in a separate process, so we need to set up everything
        # Load the carrier image
        carrier_image = Image.open(image_path).convert('RGB')
        image_array = np.array(carrier_image, dtype=np.uint8)
        
        key_bytes = key_str.encode('utf-8')
        all_encrypted_data = bytearray()
        file_metadata = []
        file_count = len(data_file_paths)
        
        # Extract the original carrier image name
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Process each file in the batch
        for i, path in enumerate(data_file_paths):
            if not os.path.exists(path):
                raise ValueError(f"Data file does not exist: {path}")
                
            with open(path, "rb") as data_file:
                raw_data = data_file.read()
                
            # Use the original carrier name in the filename
            filename = f"{base_name}_{i+1}".encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            ext = os.path.splitext(path)[1].encode('utf-8', errors='replace')[:10].ljust(10, b' ')
            
            # Compress and encrypt more efficiently
            compressed_data = self.compress_data(raw_data)
            encrypted_data = self.cipher.encrypt(compressed_data)
            
            file_metadata.append((filename, ext, len(encrypted_data)))
            all_encrypted_data.extend(encrypted_data)
            
            # Clean up memory after each file
            del raw_data, compressed_data, encrypted_data
            
        # Process metadata
        author_bytes = (author or "N/A").encode('utf-8', errors='replace')[:50].ljust(50, b' ')
        timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
        metadata = self.METADATA_MARKER + author_bytes + timestamp
        encrypted_metadata = self.cipher.encrypt(metadata)
        
        # Combine everything into the final hidden data
        file_metadata_bytes = b"".join(fn + ext + struct.pack(">I", dl) for fn, ext, dl in file_metadata)
        hidden_data = (self.MAGIC_MARKER + hashlib.sha256(key_bytes).digest() +
                    self.derive_password_hash(password) +
                    struct.pack(">I", file_count) + file_metadata_bytes +
                    bytes(all_encrypted_data) + struct.pack(">I", len(encrypted_metadata)) + encrypted_metadata)
        hmac_value = self.generate_hmac(hidden_data)
        hidden_data += hmac_value
        
        # Return the processed data for the batch
        return {
            "metadata": file_metadata,
            "hidden_data": hidden_data,
            "batch_size": len(data_file_paths)
        }

    def extract_data(self, image_path, key_str, password, update_progress_callback, carrier_filename=None):
        """Extract multiple files and metadata from an image with custom filename format."""
        if not self.get_cipher(key_str):
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
                raise ValueError("File integrity check failed")

            update_progress_callback(40)

            if not hidden_data.startswith(self.MAGIC_MARKER):
                raise ValueError("Invalid data: magic bytes missing")

            key_bytes = key_str.encode('utf-8')
            stored_key_hash = hidden_data[4:36]
            if hashlib.sha256(key_bytes).digest() != stored_key_hash:
                raise ValueError("Key mismatch: incorrect key provided")

            stored_password_hash = hidden_data[36:68]
            if self.derive_password_hash(password) != stored_password_hash:
                raise ValueError("Password mismatch: incorrect password provided")

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
                    raise ValueError(f"Decryption failed for file {filename_str}: incorrect key")
                except zlib.error as e:
                    raise ValueError(f"Decompression failed for file {filename_str}: {str(e)}")

            update_progress_callback(90)
            return files_data, author, timestamp_readable

        except Exception as e:
            logging.error(f"Extraction failed: {str(e)}")
            raise ValueError(f"Extraction failed: {str(e)}")