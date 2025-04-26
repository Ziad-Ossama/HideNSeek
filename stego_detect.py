import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from PIL import Image
import struct
import threading
import sys

class StegoDetectorApp:
    """Tkinter app to detect steganography in an image with terminal logging."""
    def __init__(self, root):
        self.root = root
        self.root.title("Stego Detector")
        self.root.geometry("400x200")
        self.root.resizable(False, False)

        self.image_path = None
        self.operation_in_progress = False
        self.MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
        self.MAX_REASONABLE_SIZE = 1024 * 1024 * 500  # 500 MB max

        self.setup_gui()
        self.log("Application initialized.")

    def log(self, message):
        """Log messages to the terminal."""
        print(f"[StegoDetector] {message}")
        sys.stdout.flush()

    def setup_gui(self):
        """Setup the GUI for the steganography detector."""
        self.log("Setting up GUI...")
        # Main frame
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.main_frame.pack(fill="both", expand=True)

        # Image selection
        tk.Label(self.main_frame, text="Select Image to Check", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.image_status = tk.Label(self.main_frame, text="No image selected", fg="red")
        self.image_status.pack(pady=5)
        tk.Button(self.main_frame, text="Browse Image", command=self.load_image, bg="#4CAF50", fg="white").pack(pady=5)

        # Detect button
        self.detect_button = tk.Button(self.main_frame, text="Check for Steganography", command=self.start_detect, bg="#4CAF50", fg="white")
        self.detect_button.pack(pady=10)

        # Result label
        self.result_label = tk.Label(self.main_frame, text="", font=("Helvetica", 12), wraplength=350)
        self.result_label.pack(pady=10)
        self.log("GUI setup completed.")

    def load_image(self):
        """Load the image to check for steganography."""
        self.log("Attempting to load image...")
        if self.operation_in_progress:
            self.log("Operation in progress, cannot load new image.")
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if not image_path:
            self.log("Image selection cancelled by user.")
            return

        self.image_path = image_path
        self.image_status.config(text=f"Image: {image_path.split('/')[-1]}", fg="green")
        self.result_label.config(text="")
        self.log(f"Image loaded successfully: {self.image_path}")

    def start_detect(self):
        """Start the steganography detection process."""
        self.log("Starting steganography detection...")
        if self.operation_in_progress:
            self.log("Detection already in progress, ignoring new request.")
            return

        if not self.image_path:
            self.log("No image selected for detection.")
            messagebox.showerror("Error", "Please select an image first.")
            return

        self.operation_in_progress = True
        self.detect_button.config(state="disabled")
        self.result_label.config(text="Checking...", fg="blue")
        self.log("Launching detection thread...")
        threading.Thread(target=self._detect_stego_thread, daemon=True).start()

    def _detect_stego_thread(self):
        """Thread to detect steganography in the image with detailed logging."""
        self.log("Detection thread started.")
        try:
            self.log("Loading and converting image to RGB...")
            carrier_image = Image.open(self.image_path).convert('RGB')
            self.log("Converting image to numpy array...")
            image_array = np.array(carrier_image, dtype=np.uint8)
            self.log("Flattening image array...")
            flat_image = image_array.flatten()
            self.log(f"Image array flattened, size: {len(flat_image)} pixels")

            # Extract bits from LSBs
            self.log("Extracting bits from LSBs...")
            bits = []
            i = 0
            while i < len(flat_image):
                bit = flat_image[i] & 1
                bits.append(str(bit))
                i += 1
                if i % 1000000 == 0:
                    self.log(f"Processed {i} pixels...")
                if i >= 16 and ''.join(bits[-16:]) == '1111111111111110':
                    self.log("Termination sequence '1111111111111110' found!")
                    break

            if i >= len(flat_image):
                self.log("Reached end of image without finding termination sequence.")
                self.root.after(0, lambda: self._update_result("No steganography detected: No termination sequence found.", "green"))
                return

            self.log(f"Extracted {i} bits before termination sequence.")

            # Convert bits to bytes
            self.log("Converting bits to bytes...")
            data_bits = bits[:-16]
            self.log(f"Total data bits (excluding termination): {len(data_bits)}")
            byte_array = bytearray()
            for j in range(0, len(data_bits), 8):
                byte = ''.join(data_bits[j:j+8])
                byte_array.append(int(byte, 2))
            full_data = bytes(byte_array)
            self.log(f"Converted to {len(full_data)} bytes of data.")

            # Check for data length
            self.log("Checking data length prefix...")
            if len(full_data) < 4:
                self.log("Data length prefix missing or invalid.")
                self.root.after(0, lambda: self._update_result("No steganography detected: Invalid data length.", "green"))
                return

            data_length = struct.unpack(">I", full_data[:4])[0]
            self.log(f"Data length from prefix: {data_length} bytes")
            if data_length > self.MAX_REASONABLE_SIZE:
                self.log(f"Data length ({data_length}) exceeds maximum allowed size ({self.MAX_REASONABLE_SIZE}).")
                self.root.after(0, lambda: self._update_result("No steganography detected: Data length exceeds maximum.", "green"))
                return

            hidden_data = full_data[4:4 + data_length]
            self.log(f"Extracted hidden data: {len(hidden_data)} bytes")

            # Check for magic marker
            self.log("Checking for magic marker...")
            if not hidden_data.startswith(self.MAGIC_MARKER):
                self.log(f"Magic marker {self.MAGIC_MARKER.hex()} not found at start of hidden data.")
                self.root.after(0, lambda: self._update_result("No steganography detected: Magic marker not found.", "green"))
                return

            self.log(f"Magic marker {self.MAGIC_MARKER.hex()} found!")
            self.root.after(0, lambda: self._update_result("Steganography detected in the image!", "red"))

        except Exception as e:
            self.log(f"Error during detection: {str(e)}")
            self.root.after(0, lambda: self._update_result(f"Detection failed: {str(e)}", "red"))
        finally:
            self.log("Detection thread completed.")
            self.operation_in_progress = False
            self.root.after(0, lambda: self.detect_button.config(state="normal"))

    def _update_result(self, message, color):
        """Update the result label with the detection result."""
        self.log(f"Updating result: {message}")
        self.result_label.config(text=message, fg=color)

if __name__ == "__main__":
    root = tk.Tk()
    app = StegoDetectorApp(root)
    root.mainloop()