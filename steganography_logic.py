def extract_data_optimized(self, carrier_path, key_str, password=None, progress_callback=None):
    """Extract data from carrier image with optimized memory usage."""
    try:
        # Initialize progress
        if progress_callback:
            progress_callback(0)

        # Read carrier image
        carrier = Image.open(carrier_path)
        if carrier.mode != 'RGB':
            carrier = carrier.convert('RGB')

        # Get image dimensions and calculate total pixels
        width, height = carrier.size
        total_pixels = width * height
        chunk_size = min(2 * 1024 * 1024, total_pixels // 4)  # 2MB chunks or quarter of image
        extracted_bits = []

        # Process image in chunks
        for y_start in range(0, height, chunk_size // width + 1):
            y_end = min(y_start + chunk_size // width + 1, height)
            chunk = carrier.crop((0, y_start, width, y_end))
            pixels = list(chunk.getdata())

            # Extract bits from pixels
            for pixel in pixels:
                for color in pixel:
                    extracted_bits.append(color & 1)

            # Update progress
            if progress_callback:
                progress = int(25 * y_end / height)
                progress_callback(progress)

            # Clean up chunk memory
            del chunk
            del pixels

        # Convert bits to bytes
        extracted_bytes = self._bits_to_bytes(extracted_bits)
        del extracted_bits  # Free memory

        if progress_callback:
            progress_callback(30)

        # Decrypt data
        cipher = self.get_cipher(key_str)
        if not cipher:
            return None

        try:
            decrypted_data = cipher.decrypt(bytes(extracted_bytes))
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

        if progress_callback:
            progress_callback(40)

        # Verify password if provided
        if password:
            stored_password = decrypted_data[:100].rstrip(b'\x00').decode('utf-8', errors='ignore')
            if stored_password != password:
                raise ValueError("Invalid password")
            decrypted_data = decrypted_data[100:]

        if progress_callback:
            progress_callback(50)

        # Return the decrypted data
        return decrypted_data

    except Exception as e:
        raise ValueError(f"Extraction failed: {str(e)}")

def extract_data(self, carrier_path, key_str, password=None, progress_callback=None):
    """Extract data from carrier GIF."""
    try:
        # Initialize progress
        if progress_callback:
            progress_callback(0)

        # Read carrier GIF
        carrier = Image.open(carrier_path)
        if not getattr(carrier, "is_animated", False):
            raise ValueError("Not an animated GIF")

        # Extract data from each frame
        extracted_bits = []
        n_frames = carrier.n_frames

        for frame_idx in range(n_frames):
            carrier.seek(frame_idx)
            frame = carrier.copy()
            if frame.mode != 'RGB':
                frame = frame.convert('RGB')

            pixels = list(frame.getdata())
            for pixel in pixels:
                for color in pixel:
                    extracted_bits.append(color & 1)

            # Update progress for frame processing
            if progress_callback:
                progress = int(25 * (frame_idx + 1) / n_frames)
                progress_callback(progress)

            # Clean up frame memory
            del frame
            del pixels

        # Convert bits to bytes
        extracted_bytes = self._bits_to_bytes(extracted_bits)
        del extracted_bits  # Free memory

        if progress_callback:
            progress_callback(30)

        # Decrypt data
        cipher = self.get_cipher(key_str)
        if not cipher:
            return None

        try:
            decrypted_data = cipher.decrypt(bytes(extracted_bytes))
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

        if progress_callback:
            progress_callback(40)

        # Verify password if provided
        if password:
            stored_password = decrypted_data[:100].rstrip(b'\x00').decode('utf-8', errors='ignore')
            if stored_password != password:
                raise ValueError("Invalid password")
            decrypted_data = decrypted_data[100:]

        if progress_callback:
            progress_callback(50)

        # Return the decrypted data
        return decrypted_data

    except Exception as e:
        raise ValueError(f"Extraction failed: {str(e)}")

def embed_data_optimized(self, data, carrier_path, output_path, key_str, password=None, progress_callback=None):
    """Embed data into carrier image with optimized memory usage."""
    try:
        # Initialize progress
        if progress_callback:
            progress_callback(0)

        # Add password to data if provided
        if password:
            password_bytes = password.encode('utf-8')
            password_bytes = password_bytes.ljust(100, b'\x00')  # Pad to fixed length
            data = password_bytes + data

        # Encrypt data
        cipher = self.get_cipher(key_str)
        if not cipher:
            return False

        encrypted_data = cipher.encrypt(data)
        data_bits = self._bytes_to_bits(encrypted_data)

        if progress_callback:
            progress_callback(10)

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
                progress = 10 + int(80 * y_end / height)
                progress_callback(progress)

            # Clean up chunk memory
            del chunk
            del pixels
            del modified_pixels

        # Save the modified image
        carrier.save(output_path, "PNG")

        if progress_callback:
            progress_callback(100)

        return True

    except Exception as e:
        raise ValueError(f"Embedding failed: {str(e)}")

def embed_data(self, data, carrier_path, output_path, key_str, password=None, progress_callback=None):
    """Embed data into carrier GIF."""
    try:
        # Initialize progress
        if progress_callback:
            progress_callback(0)

        # Add password to data if provided
        if password:
            password_bytes = password.encode('utf-8')
            password_bytes = password_bytes.ljust(100, b'\x00')  # Pad to fixed length
            data = password_bytes + data

        # Encrypt data
        cipher = self.get_cipher(key_str)
        if not cipher:
            return False

        encrypted_data = cipher.encrypt(data)
        data_bits = self._bytes_to_bits(encrypted_data)

        if progress_callback:
            progress_callback(10)

        # Read carrier GIF
        carrier = Image.open(carrier_path)
        if not getattr(carrier, "is_animated", False):
            raise ValueError("Not an animated GIF")

        # Check if carrier has enough capacity
        width, height = carrier.size
        total_capacity = width * height * 3 * carrier.n_frames
        if len(data_bits) > total_capacity:
            raise ValueError("Carrier GIF too small for data")

        # Create new GIF
        frames = []
        durations = []
        bit_index = 0

        for frame_idx in range(carrier.n_frames):
            carrier.seek(frame_idx)
            frame = carrier.copy()
            if frame.mode != 'RGB':
                frame = frame.convert('RGB')

            pixels = list(frame.getdata())
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

            # Create new frame with modified pixels
            new_frame = Image.new('RGB', (width, height))
            new_frame.putdata(modified_pixels)
            frames.append(new_frame)
            
            try:
                durations.append(carrier.info['duration'])
            except KeyError:
                durations.append(100)  # Default 100ms duration

            # Update progress
            if progress_callback:
                progress = 10 + int(80 * (frame_idx + 1) / carrier.n_frames)
                progress_callback(progress)

            # Clean up frame memory
            del frame
            del pixels
            del modified_pixels

        # Save the modified GIF
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=False
        )

        if progress_callback:
            progress_callback(100)

        return True

    except Exception as e:
        raise ValueError(f"Embedding failed: {str(e)}")

def process_extracted_data(self, extracted_data):
    """Process extracted data into individual files."""
    try:
        # Check for magic number at the start
        if not extracted_data.startswith(b'\xDE\xAD\xBE\xEF'):
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