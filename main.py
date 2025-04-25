# Import required libraries for GUI, image processing, encryption, and system operations
import customtkinter as ctk  # CustomTkinter for enhanced GUI components
from tkinter import filedialog, messagebox, ttk  # Tkinter modules for file dialogs and messages
from PIL import Image  # Python Imaging Library for image processing
import numpy as np  # NumPy for numerical operations on image data
from cryptography.fernet import Fernet  # Fernet for symmetric encryption
import os  # OS module for file and directory operations
import threading  # Threading for asynchronous operations
import hashlib  # Hashlib for computing file hashes
import time  # Time module for timestamps and performance measurement
import uuid  # UUID for generating unique identifiers
from datetime import datetime  # Datetime for timestamp formatting
import pyperclip  # Pyperclip for copying text to clipboard
import json  # JSON for history file management
import tempfile  # Tempfile for temporary file handling
import struct  # Struct for binary data packing/unpacking
from img import SteganographyLogic  # Custom module for image steganography logic
from gif import GIFSteganographyLogic  # Custom module for GIF steganography logic
from tkinterdnd2 import TkinterDnD, DND_FILES  # TkinterDnD for drag-and-drop functionality
import sys  # Sys for system-specific parameters and functions
import multiprocessing  # Multiprocessing for parallel processing
import concurrent.futures  # Concurrent futures for thread/process pool management
import gc  # Garbage collection for memory management
from functools import partial  # Partial for creating partial function applications

# Handle frozen executable (e.g., PyInstaller) to set up TkinterDnD library path
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # Path to temporary directory for frozen executable
    tkdnd_path = os.path.join(base_path, 'tkinterdnd2')  # Path to TkinterDnD library
    os.environ['TKDND_LIBRARY'] = tkdnd_path  # Set environment variable for TkinterDnD

# Define global constants for UI styling
button_width = 120  # Width for buttons in pixels
button_pady = 10  # Vertical padding for buttons
button_size = 12  # Font size for button text
main_font = ("Helvetica", 20, "bold")  # Main font for section titles

class HistoryManager:
    """Manages the history of embedding and extraction operations."""
    def __init__(self):
        self.history_file = "history.json"  # File to store history data
        self.history = self.load_history()  # Load history on initialization

    def load_history(self):
        """Load history from JSON file."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)  # Parse JSON file into a list
        except FileNotFoundError:
            return []  # Return empty list if file doesn't exist

    def save_history(self):
        """Save history to JSON file."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=4)  # Write history list to file with formatting

    def add_entry(self, operation, details):
        """Add a new history entry with timestamp, operation, and details."""
        entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Current timestamp
            "operation": operation,  # Type of operation (e.g., Embed, Extract)
            "details": details  # Details of the operation
        }
        self.history.append(entry)  # Append entry to history list
        self.save_history()  # Save updated history

    def get_history(self):
        """Retrieve all history entries."""
        return self.history

class SteganographyApp:
    """Main application class for the steganography GUI."""
    def __init__(self, root):
        self.root = root  # Root window for the GUI
        self.root.title("HideNSeek - Steganography Application")  # Set window title
        self.root.geometry("900x700")  # Set window size to 900x700 pixels
        # Disable full-screen mode to maintain consistent layout
        self.root.attributes('-fullscreen', False)
        # Prevent full-screen toggling via key bindings
        self.root.bind("<F11>", lambda event: "break")
        self.root.bind("<Alt-Return>", lambda event: "break")
        self.root.bind("<Alt-F11>", lambda event: "break")
        # Prevent window resizing to maintain UI consistency
        self.root.resizable(False, False)

        # Initialize attributes to manage state
        self.carrier_image_path = None  # Path to the carrier image
        self.carrier_gif_path = None  # Path to the carrier GIF
        self.data_file_path = None  # Paths to files to embed in image
        self.gif_data_file_path = None  # Paths to files to embed in GIF
        self.stego_image = None  # Resulting stego-image after embedding
        self.operation_in_progress = False  # Flag to track ongoing operations
        self.estimates_visible = False  # Flag to show/hide time estimates
        self.current_operation = None  # Current operation type (embed/extract)
        self.carrier_image_hash = None  # Hash of the carrier image for integrity
        self.carrier_gif_hash = None  # Hash of the carrier GIF for integrity
        self.image_load_lock = threading.Lock()  # Lock for image loading
        self.gif_load_lock = threading.Lock()  # Lock for GIF loading
        self.MAX_FILES_SELECTION = 20  # Maximum number of files to embed at once

        # Initialize steganography logic handlers
        self.image_logic = SteganographyLogic()  # Logic for image steganography
        print("Available methods in SteganographyLogic:", dir(self.image_logic))
        self.gif_logic = GIFSteganographyLogic()  # Logic for GIF steganography
        print("Available methods in GIFSteganographyLogic:", dir(self.gif_logic))
        self.history_manager = HistoryManager()  # History manager instance

        # Memory and CPU management
        self.max_memory = 2.5 * 1024 * 1024 * 1024  # 2.5GB RAM limit
        self.cpu_count = multiprocessing.cpu_count()
        self.process_pool = None
        self.chunk_size = min(512 * 1024, self.max_memory // (4 * self.cpu_count))
        
        # Operation flags
        self.image_operation_active = False
        self.gif_operation_active = False
        
        # Memory monitoring
        self.memory_monitor = threading.Thread(target=self._monitor_memory, daemon=True)
        self.memory_monitor.start()
        
        # Schedule memory checks
        self.root.after(5000, self.check_memory_usage)

        # Schedule periodic carrier validity check
        self.schedule_carrier_check()

        # Configure CustomTkinter appearance
        ctk.set_appearance_mode("dark")  # Set dark mode
        ctk.set_default_color_theme("dark-blue")  # Set dark-blue theme

        # Setup the GUI
        self.setup_gui()

    def setup_gui(self):
        """Setup the main GUI with a sidebar and content area."""
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)  # Main frame for layout
        self.main_frame.pack(fill="both", expand=True)  # Expand to fill window

        # Create sidebar for navigation
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=200, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")

        # Add application title to sidebar
        ctk.CTkLabel(self.sidebar_frame, text="HideNSeek", font=("Helvetica", 20, "bold")).pack(pady=20)

        # Top frame for main feature buttons
        top_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        top_button_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.sidebar_buttons = {}  # Dictionary to store sidebar buttons for styling

        # Image-Stego button in sidebar
        self.sidebar_buttons["image_stego"] = ctk.CTkButton(
            top_button_frame, text="Image-Stego", 
            command=lambda: self.show_frame("image_stego"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", button_size + 2, "bold"),
            height=55, width=160
        )
        self.sidebar_buttons["image_stego"].pack(pady=(15, 15), padx=5, fill="x")

        # GIF-Stego button in sidebar
        self.sidebar_buttons["gif_stego"] = ctk.CTkButton(
            top_button_frame, text="GIF-Stego", 
            command=lambda: self.show_frame("gif_stego"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", button_size + 2, "bold"),
            height=55, width=160
        )
        self.sidebar_buttons["gif_stego"].pack(pady=(15, 15), padx=5, fill="x")

        # Bottom frame for utility buttons
        bottom_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_button_frame.pack(side="bottom", fill="x", padx=10, pady=20)

        # Separator line above utility buttons
        separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#555555")
        separator.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

        # History button in sidebar
        self.sidebar_buttons["history"] = ctk.CTkButton(
            bottom_button_frame, text="History", 
            command=lambda: self.show_frame("history"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", 15, "bold"), width=140
        )
        self.sidebar_buttons["history"].pack(pady=7, fill="x")

        # Help button in sidebar
        self.sidebar_buttons["help"] = ctk.CTkButton(
            bottom_button_frame, text="Help", 
            command=self.show_help,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", 15, "bold"), width=140
        )
        self.sidebar_buttons["help"].pack(pady=5, fill="x")

        # Content area for displaying frames
        self.content_frame = ctk.CTkFrame(self.main_frame, corner_radius=0)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Initialize frames dictionary for different tabs
        self.frames = {}
        self.setup_image_stego_frame()  # Setup Image-Stego tab
        self.setup_gif_stego_frame()  # Setup GIF-Stego tab
        self.setup_history_frame()  # Setup History tab

        # Display the initial frame
        self.active_frame = None
        self.show_frame("image_stego")
        self.root.update_idletasks()  # Force GUI update

    def schedule_carrier_check(self):
        """Schedule periodic checks of carrier file validity every 1 second."""
        self.check_carrier_validity()
        self.root.after(1000, self.schedule_carrier_check)

    def _get_system_memory(self):
        """Estimate available system memory in bytes."""
        try:
            import psutil
            return psutil.virtual_memory().available  # Get available memory using psutil
        except ImportError:
            return 2 * 1024 * 1024 * 1024  # Default to 2GB if psutil is unavailable

    def _manage_memory(self, aggressive=False):
        """Enhanced memory management with strict limits."""
        gc.collect()
        
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss
            
            if aggressive or memory_usage > self.max_memory * 0.9:
                # Clear large objects
                if hasattr(self, 'stego_image') and self.stego_image is not None:
                    self.stego_image = None
                
                # Clear temporary data
                for attr_name in list(vars(self).keys()):
                    if attr_name.startswith('_temp_'):
                        setattr(self, attr_name, None)
                
                # Reset process pool if memory usage is critical
                if memory_usage > self.max_memory * 0.95:
                    if self.process_pool is not None:
                        self.process_pool.shutdown(wait=False)
                        self.process_pool = None
                    
                # Force multiple garbage collections
                for _ in range(3):
                    gc.collect()
                    time.sleep(0.1)
                
                # Adjust chunk size based on available memory
                available_memory = psutil.virtual_memory().available
                self.chunk_size = min(
                    512 * 1024,
                    available_memory // (8 * self.cpu_count)
                )
                
        except ImportError:
            pass
        except Exception as e:
            print(f"Memory management error: {str(e)}")

    def _split_files_for_processing(self, file_paths, max_batch_size=50*1024*1024):
        """Split files into batches for parallel processing based on size."""
        batches = []
        current_batch = []
        current_batch_size = 0

        for path in file_paths:
            file_size = os.path.getsize(path)
            if current_batch_size + file_size > max_batch_size and current_batch:
                batches.append(current_batch)
                current_batch = [path]
                current_batch_size = file_size
            else:
                current_batch.append(path)
                current_batch_size += file_size

        if current_batch:
            batches.append(current_batch)

        return batches

    def _check_concurrent_operations(self):
        """Check if both image and GIF operations are running simultaneously."""
        return self.image_operation_active and self.gif_operation_active

    def _low_priority_gc(self):
        """Run garbage collection in a low-priority thread to avoid blocking the UI."""
        def gc_thread():
            gc.collect()
        threading.Thread(target=gc_thread, daemon=True).start()

    def schedule_memory_check(self):
        """Schedule periodic checks of memory usage."""
        self.check_memory_usage()
        self.root.after(5000, self.schedule_memory_check)  # Check every 5 seconds

    def check_memory_usage(self):
        """Check memory usage and take action if needed."""
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss
            
            # If using more than 90% of our target limit, force garbage collection
            if memory_usage > self.max_memory * 0.9:
                self._manage_memory(aggressive=True)
                print(f"Memory management: Usage was {memory_usage/(1024*1024):.1f} MB, performed aggressive GC")
        except ImportError:
            # If psutil isn't available, just do regular GC
            self._manage_memory()
        
    def update_progress(self, value, is_gif=False):
        """Update the progress bar and label (combined for both image and GIF)."""
        progress_bar = self.gif_progress if is_gif else self.progress
        progress_label = self.gif_progress_label if is_gif else self.progress_label
        try:
            if value == 0:  # Reset functionality
                progress_bar.set(0)
                progress_label.configure(text="Progress: 0%")
            else:
                # Only update if change is significant (reduces UI updates)
                if not hasattr(self, '_last_progress_value') or abs(self._last_progress_value - value) >= 2:
                    self._last_progress_value = value
                    progress_bar.set(value / 100)
                    progress_label.configure(text=f"Progress: {int(value)}%")
            self.root.update_idletasks()
        except Exception as e:
            print(f"Progress update error: {str(e)}")

    def show_frame(self, frame_name):
        """Display the specified frame and update sidebar button styles."""
        if hasattr(self, 'active_frame') and self.active_frame == frame_name:
            return  # Do nothing if the frame is already active

        # Hide all frames
        for frame in self.frames.values():
            frame.pack_forget()

        # Show the selected frame
        self.frames[frame_name].pack(fill="both", expand=True)
        self.active_frame = frame_name

        # Update sidebar button styles (active/inactive)
        for name, button in self.sidebar_buttons.items():
            if name == frame_name:
                button.configure(
                    fg_color="#2E7D32", hover_color="#2E7D32",
                    text_color="white", state="disabled", text_color_disabled="white"
                )
            else:
                button.configure(
                    fg_color="#4CAF50", hover_color="#388E3C",
                    text_color="white", state="normal"
                )

        self.check_carrier_validity()  # Validate carriers when switching tabs

    def setup_frame(self, frame_name, is_gif=False):
        """Generalized method to setup frames for both Image-Stego and GIF-Stego."""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.frames[frame_name] = frame
        scrollable_frame = ctk.CTkScrollableFrame(frame, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Carrier Section
        section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        section.pack(fill="x", pady=5)
        ctk.CTkLabel(section, text=f"Carrier {'GIF' if is_gif else 'Image'}", font=main_font).pack(pady=(10, 10))

        button_frame = ctk.CTkFrame(section, fg_color="transparent")
        button_frame.pack(pady=(0, 10))
        load_button = ctk.CTkButton(
            button_frame, text=f"Browse {'GIF' if is_gif else 'Image'}",
            command=partial(self.load_carrier, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold")
        )
        load_button.pack(side="left", padx=(0, 0))
        setattr(self, f"load_{'gif' if is_gif else 'image'}_button", load_button)

        status_label = ctk.CTkLabel(
            section, text=f"No {'GIF' if is_gif else 'image'} selected",
            text_color="red", font=("Helvetica", 14, "bold"), wraplength=300, justify="center"
        )
        status_label.pack(pady=(0, button_pady))
        setattr(self, f"carrier_{'gif' if is_gif else 'image'}_status", status_label)

        capacity_label = ctk.CTkLabel(
            section, text="", text_color="#66BB6A", font=("Helvetica", 12, "italic")
        )
        capacity_label.pack(pady=(0, button_pady))
        setattr(self, f"{'gif_' if is_gif else ''}capacity_label", capacity_label)

        section.drop_target_register(DND_FILES)
        section.dnd_bind('<<Drop>>', partial(self.drop_carrier, is_gif=is_gif))

        # Data Section
        data_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        data_section.pack(fill="x", pady=5)
        ctk.CTkLabel(data_section, text="Data to Hide", font=main_font).pack(pady=(10, 10))

        data_button = ctk.CTkButton(
            data_section, text="Browse Files",
            command=partial(self.load_data_file, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold")
        )
        data_button.pack(pady=5)
        setattr(self, f"load_{'gif_' if is_gif else ''}data_button", data_button)

        data_status = ctk.CTkLabel(
            data_section, text="No files selected", text_color="red",
            font=("Helvetica", 14, "bold"), wraplength=300
        )
        data_status.pack(pady=5)
        setattr(self, f"{'gif_' if is_gif else ''}data_file_status", data_status)

        data_section.drop_target_register(DND_FILES)
        data_section.dnd_bind('<<Drop>>', partial(self.drop_data_file, is_gif=is_gif))

        # Key Section
        key_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        key_section.pack(fill="x", pady=5)
        ctk.CTkLabel(key_section, text="Encryption Key", font=main_font).pack(pady=(10, 10))

        key_frame = ctk.CTkFrame(key_section, fg_color="transparent")
        key_frame.pack(pady=2)
        key_entry = ctk.CTkEntry(
            key_frame, width=300, placeholder_text="Enter or generate a key",
            font=("Helvetica", 14, "normal"), state="disabled"
        )
        key_entry.pack(pady=(0, button_pady))
        setattr(self, f"{'gif_' if is_gif else ''}key_entry", key_entry)

        key_button = ctk.CTkButton(
            key_frame, text="Generate",
            command=partial(self.generate_key, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        key_button.pack(pady=(button_pady, button_pady))
        setattr(self, f"{'gif_' if is_gif else ''}generate_key_button", key_button)

        estimates_label = ctk.CTkLabel(
            key_section, text="", font=("Helvetica", 12, "italic"),
            text_color="#66BB6A", wraplength=300, justify="left", anchor="w"
        )
        estimates_label.pack_forget()
        setattr(self, f"{'gif_' if is_gif else ''}estimates_label", estimates_label)

        # Authentication Section
        auth_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        auth_section.pack(fill="x", pady=5)
        ctk.CTkLabel(auth_section, text="Authentication", font=main_font).pack(pady=(10, 10))

        password_entry = ctk.CTkEntry(
            auth_section, 
            show="*",  # This ensures password masking with asterisks
            width=300, 
            placeholder_text="Enter password (optional)",
            font=("Helvetica", 14, "normal")
        )
        password_entry.pack(pady=(0, button_pady))
        password_entry.configure(state="disabled")  # Initially disabled
        setattr(self, f"{'gif_' if is_gif else ''}password_entry", password_entry)

        author_entry = ctk.CTkEntry(
            auth_section, 
            width=300, 
            placeholder_text="Enter author name (optional)",
            font=("Helvetica", 14, "normal")
        )
        author_entry.pack(pady=(button_pady, 20))
        author_entry.configure(state="disabled")  # Initially disabled
        setattr(self, f"{'gif_' if is_gif else ''}author_entry", author_entry)

        # Action Section
        action_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        action_frame.pack(fill="x", pady=5)
        button_container = ctk.CTkFrame(action_frame, fg_color="transparent")
        button_container.pack(pady=(5, 5), fill="x")
        center_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        center_frame.pack(pady=10, padx=10)

        embed_button = ctk.CTkButton(
            center_frame, text="Embed Data",
            command=partial(self.start_embed, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        embed_button.pack(side="left", padx=10)
        setattr(self, f"{'gif_' if is_gif else ''}embed_button", embed_button)

        extract_button = ctk.CTkButton(
            center_frame, text="Extract Data",
            command=partial(self.start_extract, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        extract_button.pack(side="left", padx=10)
        setattr(self, f"{'gif_' if is_gif else ''}extract_button", extract_button)

        metadata_button = ctk.CTkButton(
            center_frame, text="View Metadata",
            command=partial(self.start_view_metadata, is_gif=is_gif),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        metadata_button.pack(side="left", padx=10)
        setattr(self, f"{'gif_' if is_gif else ''}metadata_button", metadata_button)

        # Progress Section
        progress_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        progress_frame.pack(fill="x", pady=5)
        progress_label = ctk.CTkLabel(
            progress_frame, text="Progress: 0%", font=("Helvetica", 12, "bold"), text_color="#66BB6A"
        )
        progress_label.pack(pady=(5, 2))
        setattr(self, f"{'gif_' if is_gif else ''}progress_label", progress_label)

        progress_bar = ctk.CTkProgressBar(
            progress_frame, width=300, height=20, corner_radius=10,
            determinate_speed=2, mode="determinate", fg_color="#2B2B2B", progress_color="#4CAF50"
        )
        progress_bar.pack(pady=(0, 5))
        progress_bar.set(0)
        setattr(self, f"{'gif_' if is_gif else ''}progress", progress_bar)

    def setup_image_stego_frame(self):
        """Setup the Image-Stego frame using the generalized method."""
        self.setup_frame("image_stego", is_gif=False)

    def setup_gif_stego_frame(self):
        """Setup the GIF-Stego frame using the generalized method."""
        self.setup_frame("gif_stego", is_gif=True)

    def setup_history_frame(self):
        """Setup the history frame to display past operations."""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.frames["history"] = frame
        ctk.CTkLabel(frame, text="Operation History", font=("Helvetica", 16, "bold")).pack(pady=10)

        tree_frame = ctk.CTkFrame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        v_scrollbar = ttk.Scrollbar(tree_frame)
        v_scrollbar.pack(side="right", fill="y")

        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", background="#333333", foreground="white")

        self.history_tree = ttk.Treeview(
            tree_frame, columns=("Timestamp", "Operation", "Details"), show="headings",
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set, style="Treeview"
        )

        v_scrollbar.config(command=self.history_tree.yview)
        h_scrollbar.config(command=self.history_tree.xview)

        self.history_tree.heading("Timestamp", text="Timestamp")
        self.history_tree.heading("Operation", text="Operation")
        self.history_tree.heading("Details", text="Details")

        self.history_tree.column("Timestamp", width=150, minwidth=150)
        self.history_tree.column("Operation", width=120, minwidth=100)
        self.history_tree.column("Details", minwidth=200, stretch=False, width=1200)

        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.history_tree.configure(displaycolumns=("Timestamp", "Operation", "Details"))

        self.update_history_view()

    def show_help(self):
        """Display a help message with application instructions."""
        messagebox.showinfo("Help", "HideNSeek Steganography Application\n\n"
                            "1. Select a carrier image or GIF using 'Browse Image/GIF' or drag and drop.\n"
                            "2. Choose files to hide using 'Browse Files' or drag and drop (max 20 files).\n"
                            "3. Enter an encryption key or generate one.\n"
                            "4. (Optional) Add a password and author name.\n"
                            "5. Click 'Embed Data' to hide data, 'Extract Data' to retrieve it, or 'View Metadata' to see details.\n"
                            "6. Check the history tab to see past operations.\n\n"
                            "Note: Ensure the key and password match during extraction!")

    def update_history_view(self):
        """Update the history view with the latest entries."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in self.history_manager.get_history():
            self.history_tree.insert("", "end", values=(
                entry["timestamp"], entry["operation"], entry["details"]
            ))

    def estimate_embedding_time(self, is_gif=False):
        """Estimate the time required for embedding (generalized for both image and GIF)."""
        carrier_path = self.carrier_gif_path if is_gif else self.carrier_image_path
        data_paths = self.gif_data_file_path if is_gif else self.data_file_path
        key_entry = self.gif_key_entry if is_gif else self.key_entry
        logic = self.gif_logic if is_gif else self.image_logic
        author_entry = self.gif_author_entry if is_gif else self.author_entry

        if not carrier_path or not data_paths:
            return None

        try:
            key_str = key_entry.get().strip()
            if not key_str:
                temp_key = Fernet.generate_key()
                logic.get_cipher(temp_key.decode())
            else:
                logic.get_cipher(key_str)

            total_size = sum(os.path.getsize(path) for path in data_paths)
            file_count = len(data_paths)

            author = author_entry.get().strip() or "N/A"
            author_bytes = author.encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata = b'\xCA\xFE\xBA\xBE' + author_bytes + timestamp
            encrypted_metadata = logic.cipher.encrypt(metadata)
            estimated_metadata_size = len(encrypted_metadata) + 4

            file_metadata_size = file_count * (50 + 10 + 4)
            compressed_size = int(total_size * 0.7)
            encrypted_size = compressed_size + 100 * file_count
            total_data_size = (len(b'\xDE\xAD\xBE\xEF') + (16 if is_gif else 32) + 16 + 4 +
                               file_metadata_size + encrypted_size + estimated_metadata_size + 32 + 4)

            if is_gif:
                sample_size = min(1024 * 1024, total_size)
                sample_data = b"\x00" * sample_size
                start_time = time.perf_counter()
                compressed_sample = logic.compress_data(sample_data)
                encrypted_sample = logic.cipher.encrypt(compressed_sample)
                end_time = time.perf_counter()
                total_bits = total_data_size
            else:
                with Image.open(carrier_path) as carrier_image:
                    carrier_image = carrier_image.convert('RGB')
                    image_array = np.array(carrier_image, dtype=np.uint8)
                    flat_image = image_array.ravel()
                    total_bits = total_data_size * 8 + 16

                    if total_bits > len(flat_image):
                        return f"Data too large. Required: {total_bits} bits, Available: {len(flat_image)} bits"

                    sample_size = min(5000, len(flat_image))
                    dummy_array = flat_image[:sample_size].copy()
                    sample_bits = [0] * sample_size
                    start_time = time.perf_counter()
                    for i in range(sample_size):
                        pixel_value = dummy_array[i] & 0xFE
                        bit_value = sample_bits[i]
                        dummy_array[i] = pixel_value | bit_value
                    end_time = time.perf_counter()

            time_taken = end_time - start_time
            rate = sample_size / (time_taken if time_taken > 0 else 0.0001)
            estimated_time = total_bits / rate

            return estimated_time * 1.10

        except Exception as e:
            return f"Estimation failed: {str(e)}"

    def estimate_extracting_time(self, is_gif=False):
        """Estimate the time required for extraction (generalized for both image and GIF)."""
        carrier_path = self.carrier_gif_path if is_gif else self.carrier_image_path
        key_entry = self.gif_key_entry if is_gif else self.key_entry
        logic = self.gif_logic if is_gif else self.image_logic

        if not carrier_path:
            return None

        try:
            key_str = key_entry.get().strip()
            if not key_str:
                temp_key = Fernet.generate_key()
                logic.get_cipher(temp_key.decode())
            else:
                logic.get_cipher(key_str)

            if is_gif:
                with open(carrier_path, "rb") as gif_file:
                    file_data = gif_file.read()
                total_size = len(file_data)
                sample_size = 1024 * 1024
                sample_data = b"\x00" * sample_size
                compressed_sample = logic.compress_data(sample_data)
                encrypted_sample = logic.cipher.encrypt(compressed_sample)
                start_time = time.perf_counter()
                decrypted_sample = logic.cipher.decrypt(encrypted_sample)
                logic.decompress_data(decrypted_sample)
                end_time = time.perf_counter()
                total_bits = total_size
            else:
                with Image.open(carrier_path) as carrier_image:
                    carrier_image = carrier_image.convert('RGB')
                    image_array = np.array(carrier_image, dtype=np.uint8)
                    flat_image = image_array.ravel()
                    total_bits = len(flat_image)
                    sample_size = min(5000, len(flat_image))
                    dummy_array = flat_image[:sample_size]
                    start_time = time.perf_counter()
                    _ = [(pixel & 1) for pixel in dummy_array]
                    end_time = time.perf_counter()

            time_taken = end_time - start_time
            bits_per_second = sample_size / (time_taken if time_taken > 0 else 0.0001)
            estimated_time = total_bits / bits_per_second

            return estimated_time * 1.05

        except Exception as e:
            return f"Estimation failed: {str(e)}"

    def update_estimated_times(self):
        """Update the estimated times display based on the active frame."""
        if not self.estimates_visible:
            return

        active_frame = self.active_frame
        if active_frame == "image_stego":
            if self.current_operation == "embed":
                embed_time = self.estimate_embedding_time()
                if embed_time is None:
                    text, color = "Estimated Time:\nEmbed: N/A", "#66BB6A"
                elif isinstance(embed_time, str):
                    text, color = f"Estimated Time:\nEmbed: {embed_time}", "red"
                else:
                    text, color = f"Estimated Time:\nEmbed: {embed_time:.2f} seconds", "#66BB6A"
            else:
                extract_time = self.estimate_extracting_time()
                text = "Estimated Time:\nExtract: "
                if extract_time is None:
                    text, color = text + "N/A", "#66BB6A"
                elif isinstance(extract_time, str):
                    text, color = text + extract_time, "red"
                else:
                    text, color = text + f"{extract_time:.2f} seconds", "#66BB6A"
            self.estimates_label.configure(text=text, text_color=color)
            self.estimates_label.pack(pady=(0, 5))
        elif active_frame == "gif_stego":
            if self.current_operation == "embed":
                embed_time = self.estimate_embedding_time(is_gif=True)
                if embed_time is None:
                    text, color = "Estimated Time:\nEmbed: N/A", "#66BB6A"
                elif isinstance(embed_time, str):
                    text, color = f"Estimated Time:\nEmbed: {embed_time}", "red"
                else:
                    text, color = f"Estimated Time:\nEmbed: {embed_time:.2f} seconds", "#66BB6A"
            else:
                extract_time = self.estimate_extracting_time(is_gif=True)
                text = "Estimated Time:\nExtract: "
                if extract_time is None:
                    text, color = text + "N/A", "#66BB6A"
                elif isinstance(extract_time, str):
                    text, color = text + extract_time, "red"
                else:
                    text, color = text + f"{extract_time:.2f} seconds", "#66BB6A"
            self.gif_estimates_label.configure(text=text, text_color=color)
            self.gif_estimates_label.pack(pady=(0, 5))

    def generate_key(self, is_gif=False):
        """Generate a new encryption key and copy it to clipboard (generalized)."""
        logic = self.gif_logic if is_gif else self.image_logic
        key_entry = self.gif_key_entry if is_gif else self.key_entry
        
        # Generate the key
        key = logic.generate_key()
        
        # Clear the entry field first
        key_entry.delete(0, "end")
        
        # Insert the key, and ensure entry state is normal
        key_entry.configure(state="normal")
        key_entry.insert(0, key)
        
        # Copy to clipboard
        pyperclip.copy(key)
        messagebox.showinfo("Key Generated", "Key copied to clipboard.")
        self.history_manager.add_entry("Key Generation", f"Generated a new encryption key for {'GIF' if is_gif else 'Image'}-Stego.")
        self.update_estimated_times()

    def validate_inputs(self, password_entry, author_entry, for_embedding=True):
        """Validate password and author inputs."""
        try:
            password = password_entry.get().strip()
            author = author_entry.get().strip()

            if password:
                password = "".join(c for c in password if c.isprintable())
                if len(password.encode('utf-8')) > 100:
                    messagebox.showerror("Error", "Password must not exceed 100 bytes.")
                    return False, None, None

            if author:
                author = "".join(c for c in author if c.isprintable())
                author_bytes = author.encode('utf-8', errors='replace')
                if len(author_bytes) > 50:
                    messagebox.showerror("Error", "Author name must not exceed 50 bytes.")
                    return False, None, None
                author = author_bytes[:50].decode('utf-8', errors='ignore')

            if not for_embedding and not password:
                messagebox.showerror("Error", "Password is required for extraction if set during embedding.")
                return False, None, None

            return True, password, author
        except Exception as e:
            messagebox.showerror("Error", f"Input validation failed: {str(e)}")
            return False, None, None

    def check_carrier_validity(self):
        """Check if carrier files are still valid and reset if needed."""
        if self.carrier_image_path and not os.path.exists(self.carrier_image_path):
            print(f"Carrier image no longer exists: {self.carrier_image_path}")
            self.carrier_image_path = None
            self.carrier_image_status.configure(text="No image selected", text_color="red")
            self._hide_capacity_and_disable_fields(is_gif=False)

        if self.carrier_gif_path and not os.path.exists(self.carrier_gif_path):
            print(f"Carrier GIF no longer exists: {self.carrier_gif_path}")
            self.carrier_gif_path = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            self._hide_capacity_and_disable_fields(is_gif=True)

    def drop_carrier(self, event, is_gif=False):
        """Handle dropped files for carrier (generalized for image and GIF)."""
        lock = self.gif_load_lock if is_gif else self.image_load_lock
        if self.operation_in_progress or lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        files = self.root.splitlist(event.data)
        if len(files) > 1:
            messagebox.showerror("Error", f"Please drop only one {'GIF' if is_gif else 'image'} file.")
            return

        file_path = files[0]
        if is_gif:
            if not file_path.lower().endswith('.gif'):
                messagebox.showerror("Error", "Please drop a GIF file.")
                return
        else:
            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                messagebox.showerror("Error", "Please drop a PNG, JPG, or JPEG file.")
                return

        if is_gif:
            self.carrier_gif_path = file_path
            if not self.validate_gif(self.carrier_gif_path):
                messagebox.showerror("Error", "Invalid GIF format!")
                self.carrier_gif_path = None
                self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
                self.update_estimated_times()
                return
            self.carrier_gif_status.configure(text="Loading...", text_color="yellow")
            self.load_gif_button.configure(state="disabled")
        else:
            self.carrier_image_path = file_path
            self.carrier_image_status.configure(text="Loading...", text_color="yellow")
            self.load_image_button.configure(state="disabled")

        threading.Thread(target=lambda: self._load_carrier(is_gif), daemon=True).start()

    def load_carrier(self, file_path=None, is_gif=False):
        """Load the carrier file (generalized for image and GIF)."""
        lock = self.gif_load_lock if is_gif else self.image_load_lock
        if self.operation_in_progress or lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[("GIF files", "*.gif")] if is_gif else [("Image files", "*.png *.jpg *.jpeg")]
            )
        if not file_path:
            return

        if is_gif:
            self.carrier_gif_path = file_path
            if not self.validate_gif(self.carrier_gif_path):
                messagebox.showerror("Error", "Invalid GIF format!")
                self.carrier_gif_path = None
                self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
                self.update_estimated_times()
                return
            self.carrier_gif_status.configure(text="Loading...", text_color="yellow")
            self.load_gif_button.configure(state="disabled")
        else:
            self.carrier_image_path = file_path
            self.carrier_image_status.configure(text="Loading...", text_color="yellow")
            self.load_image_button.configure(state="disabled")

        threading.Thread(target=lambda: self._load_carrier(is_gif), daemon=True).start()

    # Fix in the _load_carrier method
    def _load_carrier(self, is_gif=False):
        """Load the carrier file and compute its hash (generalized)."""
        lock = self.gif_load_lock if is_gif else self.image_load_lock
        carrier_path = self.carrier_gif_path if is_gif else self.carrier_image_path
        status_label = self.carrier_gif_status if is_gif else self.carrier_image_status
        load_button = self.load_gif_button if is_gif else self.load_image_button
        capacity_label = self.gif_capacity_label if is_gif else self.capacity_label
        hash_attr = 'carrier_gif_hash' if is_gif else 'carrier_image_hash'
        key_entry = self.gif_key_entry if is_gif else self.key_entry

        with lock:
            try:
                with open(carrier_path, "rb") as f:
                    setattr(self, hash_attr, hashlib.sha256(f.read()).hexdigest())

                capacity_mb = self.calculate_gif_capacity(carrier_path) if is_gif else self.calculate_image_capacity(carrier_path)
                filename = os.path.basename(carrier_path)
                if len(filename) > 30:
                    display_name = f"{filename[:15]}...{filename[-12:]}"
                else:
                    display_name = filename

                self.root.after(0, lambda: status_label.configure(
                    text=f"{'GIF' if is_gif else 'Image'} selected:\n{display_name}", text_color="green"
                ))
                self.root.after(0, lambda: capacity_label.configure(
                    text=f"Max safe storage: {capacity_mb:.2f} MB (recommended: {capacity_mb*0.8:.2f} MB)",
                    text_color="#66BB6A"
                ))

                # Enable buttons and fields - ensuring key field is properly enabled
                buttons = ['embed_button', 'extract_button', 'metadata_button', 'generate_key_button']
                entries = ['key_entry', 'password_entry', 'author_entry']
                
                # Enable all buttons first
                for btn in buttons:
                    self.root.after(0, lambda b=btn: getattr(self, f"{'gif_' if is_gif else ''}{b}").configure(state="normal"))
                
                # Then enable entry fields with proper placeholders
                for entry in entries:
                    entry_widget = getattr(self, f"{'gif_' if is_gif else ''}{entry}")
                    placeholder = f"Enter {'key' if 'key' in entry else 'password' if 'password' in entry else 'author name'} (optional)"
                    self.root.after(0, lambda e=entry_widget, p=placeholder: e.configure(state="normal", placeholder_text=p))
                
                # Specifically ensure the key entry is enabled and ready for input
                self.root.after(0, lambda: key_entry.configure(state="normal"))
                
                # Force the UI to update immediately
                self.root.update_idletasks()

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load {'GIF' if is_gif else 'image'}: {str(e)}"))
                self.root.after(0, lambda: status_label.configure(text=f"Failed to load {'GIF' if is_gif else 'image'}: {str(e)}", text_color="red"))
                self._hide_capacity_and_disable_fields(is_gif)
            finally:
                self.root.after(0, lambda: load_button.configure(state="normal"))
                self.root.after(0, self.update_estimated_times)

    def drop_data_file(self, event, is_gif=False):
        """Handle dropped files for data to hide (generalized)."""
        files = self.root.splitlist(event.data)
        if len(files) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            return

        if is_gif:
            MAX_FILE_SIZE = 500 * 1024 * 1024
            oversized_files = [f"{os.path.basename(f)} ({round(os.path.getsize(f)/1024/1024)} MB)" 
                              for f in files if os.path.getsize(f) > MAX_FILE_SIZE]
            if oversized_files:
                messagebox.showerror("Error", "The following files exceed the 500MB size limit:\n\n" + "\n".join(oversized_files))
                return

        if is_gif:
            self.gif_data_file_path = files
            self.gif_data_file_status.configure(
                text=f"{len(self.gif_data_file_path)} files selected" if self.gif_data_file_path else "No files selected",
                text_color="green" if self.gif_data_file_path else "red"
            )
        else:
            self.data_file_path = files
            self.data_file_status.configure(
                text=f"{len(self.data_file_path)} files selected" if self.data_file_path else "No files selected",
                text_color="green" if self.data_file_path else "red"
            )
        self.update_estimated_times()

    def load_data_file(self, file_paths=None, is_gif=False):
        """Load data files to embed (generalized)."""
        if not file_paths:
            file_paths = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])

        if len(file_paths) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            file_paths = []
            status_label = self.gif_data_file_status if is_gif else self.data_file_status
            status_label.configure(text="No files selected", text_color="red")
            return

        if is_gif:
            MAX_FILE_SIZE = 500 * 1024 * 1024
            oversized_files = [f"{os.path.basename(f)} ({round(os.path.getsize(f)/1024/1024)} MB)" 
                              for f in file_paths if os.path.getsize(f) > MAX_FILE_SIZE]
            if oversized_files:
                messagebox.showerror("Error", "The following files exceed the 500MB size limit:\n\n" + "\n".join(oversized_files))
                file_paths = []
                self.gif_data_file_status.configure(text="No files selected", text_color="red")
                return
            self.gif_data_file_path = file_paths
            self.gif_data_file_status.configure(
                text=f"{len(self.gif_data_file_path)} files selected" if self.gif_data_file_path else "No files selected",
                text_color="green" if self.gif_data_file_path else "red"
            )
        else:
            self.data_file_path = file_paths
            self.data_file_status.configure(
                text=f"{len(self.data_file_path)} files selected" if self.data_file_path else "No files selected",
                text_color="green" if self.data_file_path else "red"
            )
        self.update_estimated_times()

    def validate_gif(self, gif_path):
        """Validate if the file is a valid GIF."""
        try:
            with Image.open(gif_path) as img:
                return img.format == "GIF"
        except Exception:
            return False

    def calculate_image_capacity(self, image_path):
        """Calculate the data storage capacity of an image."""
        try:
            if not image_path or not os.path.exists(image_path):
                return 0
            with Image.open(image_path) as img:
                width, height = img.size
                channels = len(img.getbands()) if img.mode != 'P' else 3
                raw_capacity_bits = width * height * channels
                raw_capacity_bytes = raw_capacity_bits // 8
                base_overhead = 4 + 16 + 16 + 4 + 32 + 100
                encryption_overhead = int(raw_capacity_bytes * 0.15)
                usable_capacity = max(0, raw_capacity_bytes - base_overhead - encryption_overhead)
                safe_capacity = int(usable_capacity * 0.9)
                return safe_capacity / (1024 * 1024)
        except Exception as e:
            print(f"Error calculating image capacity: {str(e)}")
            return 0

    def calculate_gif_capacity(self, gif_path):
        """Calculate the data storage capacity of a GIF."""
        try:
            if not gif_path or not os.path.exists(gif_path):
                return 0
            file_size = os.path.getsize(gif_path)
            raw_capacity = int(file_size * 0.75)
            overhead = 4 + 16 + 16 + 4 + 32 + 100
            usable_capacity = max(0, raw_capacity - overhead)
            return usable_capacity / (1024 * 1024)
        except Exception as e:
            print(f"Error calculating GIF capacity: {str(e)}")
            return 0

    def _hide_capacity_and_disable_fields(self, is_gif=False):
        """Hide capacity label and disable fields when no carrier is loaded (generalized)."""
        capacity_label = self.gif_capacity_label if is_gif else self.capacity_label
        capacity_label.configure(text="")

        buttons = ['embed_button', 'extract_button', 'metadata_button', 'generate_key_button']
        entries = ['key_entry', 'password_entry', 'author_entry']
        for btn in buttons:
            getattr(self, f"{'gif_' if is_gif else ''}{btn}").configure(state="disabled")
        for entry in entries:
            attr = getattr(self, f"{'gif_' if is_gif else ''}{entry}")
            attr.configure(state="disabled", placeholder_text=f"Select a {'GIF' if is_gif else 'image'} first")
            attr.delete(0, "end")

    def reset_fields(self, is_gif=False):
        """Reset all fields to initial state (generalized) with complete cleanup."""
        # Reset data paths and status labels
        if is_gif:
            self.carrier_gif_path = None
            self.gif_data_file_path = None
            self.carrier_gif_hash = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            self.gif_data_file_status.configure(text="No files selected", text_color="red")
            self.gif_capacity_label.configure(text="")
            self.gif_estimates_label.pack_forget()
            
            # Reset key and auth fields
            for field in [self.gif_key_entry, self.gif_password_entry, self.gif_author_entry]:
                field.delete(0, "end")
                field.configure(state="disabled", placeholder_text="Select a GIF first")
            
            # Reset buttons
            self.gif_embed_button.configure(state="disabled")
            self.gif_extract_button.configure(state="disabled") 
            self.gif_metadata_button.configure(state="disabled")
            self.gif_generate_key_button.configure(state="disabled")
            
            # Reset progress
            self.update_progress(0, is_gif=True)
        else:
            self.carrier_image_path = None
            self.data_file_path = None
            self.stego_image = None
            self.carrier_image_hash = None
            self.carrier_image_status.configure(text="No image selected", text_color="red")
            self.data_file_status.configure(text="No files selected", text_color="red")
            self.capacity_label.configure(text="")
            self.estimates_label.pack_forget()
            
            # Reset key and auth fields
            for field in [self.key_entry, self.password_entry, self.author_entry]:
                field.delete(0, "end")
                field.configure(state="disabled", placeholder_text="Select an image first")
            
            # Reset buttons
            self.embed_button.configure(state="disabled")
            self.extract_button.configure(state="disabled")
            self.metadata_button.configure(state="disabled")
            self.generate_key_button.configure(state="disabled")
            
            # Reset progress
            self.update_progress(0)

        # Global reset actions
        self.estimates_visible = False
        self._manage_memory(aggressive=True)
        
        # Force UI update
        self.root.update_idletasks()

    def set_button_state(self, button, state, operation=False):
        """Enable/disable buttons during processing."""
        button.configure(state=state)
        if operation:
            self.operation_in_progress = (state == "disabled")

    def start_embed(self, is_gif=False):
        """Start the embedding process (generalized)."""
        if self.operation_in_progress:
            return
        if is_gif and self.image_operation_active:
            messagebox.showinfo("Notice", "Please wait for the image operation to finish.")
            return
        if not is_gif and self.gif_operation_active:
            messagebox.showinfo("Notice", "Please wait for the GIF operation to finish.")
            return

        password_entry = self.gif_password_entry if is_gif else self.password_entry
        author_entry = self.gif_author_entry if is_gif else self.author_entry
        embed_button = self.gif_embed_button if is_gif else self.embed_button

        valid, password, author = self.validate_inputs(password_entry, author_entry)
        if not valid:
            return

        self.update_progress(0, is_gif)
        threading.Thread(target=lambda: self._embed_data_thread(password, author, is_gif), daemon=True).start()

    def _embed_data_thread(self, password, author, is_gif=False):
        """Thread for embedding data (generalized) - now using optimized methods."""
        if is_gif:
            embed_button = self.gif_embed_button
            carrier_path = self.carrier_gif_path
            data_paths = self.gif_data_file_path
            key_entry = self.gif_key_entry
            logic = self.gif_logic
            operation_flag = 'gif_operation_active'
        else:
            embed_button = self.embed_button
            carrier_path = self.carrier_image_path
            data_paths = self.data_file_path
            key_entry = self.key_entry
            logic = self.image_logic
            operation_flag = 'image_operation_active'

        # Set the operation flag only for the active section
        if hasattr(self, operation_flag):
            setattr(self, operation_flag, True)
        self.set_button_state(embed_button, "disabled", operation=True)

        try:
            # Validate inputs
            if not carrier_path or not data_paths:
                raise ValueError(f"Select a carrier {'GIF' if is_gif else 'image'} and at least one file to embed.")

            key_str = key_entry.get().strip()
            if not key_str:
                raise ValueError("Please provide a valid encryption key.")

            if not logic.get_cipher(key_str, self.root):
                return

            self.current_operation = "embed"
            self.estimates_visible = True
            self.update_estimated_times()

            # Process embedding based on type
            if is_gif:
                output_data = self._process_gif_embed(logic, carrier_path, data_paths, key_str, password, author)
            else:
                output_data = self._process_image_embed(logic, carrier_path, data_paths, key_str, password, author)

            # Save the output
            extension = ".gif" if is_gif else ".png"
            save_path = filedialog.asksaveasfilename(
                defaultextension=extension,
                filetypes=[(f"{'GIF' if is_gif else 'Image'} files", f"*{extension}")]
            )

            if save_path:
                if is_gif:
                    with open(save_path, "wb") as output_file:
                        output_file.write(output_data)
                else:
                    # For images, output_data is a PIL Image object
                    output_data.save(save_path, format="PNG")
                self._handle_success(save_path, len(data_paths), is_gif)

        except Exception as e:
            self._handle_error(str(e), is_gif)
        finally:
            # Reset only the active operation flag
            if hasattr(self, operation_flag):
                setattr(self, operation_flag, False)
            self.set_button_state(embed_button, "normal", operation=True)
            self._manage_memory(aggressive=True)
            self.root.update_idletasks()

    def _process_gif_embed(self, logic, carrier_path, data_paths, key_str, password, author):
        """Handle GIF embedding process."""
        return logic.embed_data(
            carrier_path, data_paths, key_str, password, author,
            lambda value: self.root.after(0, lambda v=value: self.update_progress(v, is_gif=True))
        )

    def _process_image_embed(self, logic, carrier_path, data_paths, key_str, password, author):
        """Handle image embedding process with optimized memory usage."""
        total_data_size = sum(os.path.getsize(path) for path in data_paths)
        
        if total_data_size > 50 * 1024 * 1024:  # For large files
            return self._process_large_image_embed(logic, carrier_path, data_paths, key_str, password, author)
        else:
            return logic.embed_data(
                image_path=carrier_path,
                data_file_paths=data_paths,
                key_str=key_str,
                password=password,
                author=author,
                update_progress_callback=self.update_progress
            )

    def _save_output(self, save_path, output_data, is_gif):
        """Save the processed output data."""
        if is_gif:
            with open(save_path, "wb") as output_file:
                output_file.write(output_data)
        else:
            w, h = output_data.size
            compress_level = 1 if w * h > 4000 * 4000 else 6
            output_data.save(save_path, format="PNG", compress_level=compress_level)

    def _handle_success(self, save_path, file_count, is_gif):
        """Handle successful operation."""
        self.update_progress(100, is_gif)
        messagebox.showinfo("Success", f"{file_count} files embedded successfully!")
        self.history_manager.add_entry(
            "Embed",
            f"Embedded {file_count} files into {save_path} ({'GIF' if is_gif else 'Image'}-Stego)"
        )
        self.update_history_view()
        self.root.after(100, lambda: self.reset_fields(is_gif))

    def _handle_error(self, error_message, is_gif):
        """Handle operation errors."""
        self.root.after(0, lambda: messagebox.showerror("Error", f"Operation failed: {error_message}"))
        self.root.after(0, lambda: self.update_progress(0, is_gif))

    def _cleanup_after_operation(self, button, operation_flag, is_gif):
        """Clean up after operation completion."""
        self.set_button_state(button, "normal", operation=True)
        setattr(self, operation_flag, False)
        self._manage_memory(aggressive=True)
        self.root.update_idletasks()

    def start_extract(self, is_gif=False):
        """Start the extraction process (generalized)."""
        if self.operation_in_progress:
            return
        password_entry = self.gif_password_entry if is_gif else self.password_entry
        author_entry = self.gif_author_entry if is_gif else self.author_entry
        valid, password, author = self.validate_inputs(password_entry, author_entry, for_embedding=False)
        if not valid:
            return
        threading.Thread(target=lambda: self._extract_data_thread(password, is_gif), daemon=True).start()

    def _extract_data_thread(self, password, is_gif=False):
        """Thread for extracting data with CPU-focused optimization."""
        if is_gif:
            extract_button = self.gif_extract_button
            carrier_path = self.carrier_gif_path
            carrier_hash = self.carrier_gif_hash
            key_entry = self.gif_key_entry
            logic = self.gif_logic
            operation_flag = 'gif_operation_active'
        else:
            extract_button = self.extract_button
            carrier_path = self.carrier_image_path
            carrier_hash = self.carrier_image_hash
            key_entry = self.key_entry
            logic = self.image_logic
            operation_flag = 'image_operation_active'

        # Set the operation flag only for the active section
        if hasattr(self, operation_flag):
            setattr(self, operation_flag, True)
        self.set_button_state(extract_button, "disabled", operation=True)

        try:
            if not carrier_path:
                raise ValueError(f"Select a carrier {'GIF' if is_gif else 'image'}.")

            with open(carrier_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if carrier_hash != current_hash:
                raise ValueError(f"Carrier {'GIF' if is_gif else 'image'} has been modified since loading!")

            key_str = key_entry.get().strip()
            if not key_str:
                raise ValueError("Please provide a valid encryption key.")

            if not logic.get_cipher(key_str, self.root):
                return

            self.current_operation = "extract"
            self.estimates_visible = True
            self.update_estimated_times()

            # Create a progress callback that doesn't involve tkinter directly
            def safe_progress_callback(value):
                if not self.root.winfo_exists():
                    return
                self.root.after(0, lambda: self.update_progress(value, is_gif))

            # Extract data using the safe callback
            if is_gif:
                extracted_data = logic.extract_data(carrier_path, key_str, password, safe_progress_callback)
            else:
                extracted_data = logic.extract_data_optimized(carrier_path, key_str, password, safe_progress_callback)

            if not extracted_data:
                raise ValueError("No data could be extracted.")

            # Process the extracted data
            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if not output_folder:
                return

            carrier_filename = os.path.splitext(os.path.basename(carrier_path))[0]
            extraction_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            subfolder_name = f"Extracted_{carrier_filename}_{extraction_time}"
            output_subfolder = os.path.join(output_folder, subfolder_name)
            os.makedirs(output_subfolder, exist_ok=True)

            # Process the extracted data in chunks to manage memory
            files_data = logic.process_extracted_data(extracted_data)
            batch_size = max(1, min(3, self.max_memory // (750 * 1024 * 1024)))

            for i in range(0, len(files_data), batch_size):
                batch = files_data[i:i+batch_size]
                for j, (filename, ext, file_data) in enumerate(batch):
                    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
                    output_path = os.path.join(output_subfolder, f"{safe_filename}{ext}")
                    
                    with open(output_path, "wb") as output_file:
                        output_file.write(file_data)
                    
                    # Update progress safely
                    if self.root.winfo_exists():
                        progress = 75 + (25 * (i + j + 1) // len(files_data))
                        self.root.after(0, lambda v=progress: self.update_progress(v, is_gif))
                    
                    # Clean up memory after each file
                    del file_data
                    if (j + 1) % batch_size == 0:
                        self._manage_memory(aggressive=True)

            if self.root.winfo_exists():
                self.root.after(0, lambda: self.update_progress(100, is_gif))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"Extracted {len(files_data)} files to {output_subfolder}"
                ))
                self.history_manager.add_entry(
                    "Extract",
                    f"Extracted {len(files_data)} files from {carrier_path} to {output_subfolder} ({'GIF' if is_gif else 'Image'}-Stego)"
                )
                self.update_history_view()
                self.root.after(100, lambda: self.reset_fields(is_gif))

        except Exception as e:
            if self.root.winfo_exists():
                self._handle_error(str(e), is_gif)
        finally:
            # Reset only the active operation flag
            if hasattr(self, operation_flag):
                setattr(self, operation_flag, False)
            if self.root.winfo_exists():
                self.set_button_state(extract_button, "normal", operation=True)
                self._manage_memory(aggressive=True)
                self.root.update_idletasks()

    def start_view_metadata(self, is_gif=False):
        """Start the metadata viewing process (generalized)."""
        if self.operation_in_progress:
            return
        threading.Thread(target=lambda: self._view_metadata_thread(is_gif), daemon=True).start()

    def _view_metadata_thread(self, is_gif=False):
        """Thread for viewing metadata (generalized)."""
        metadata_button = self.gif_metadata_button if is_gif else self.metadata_button
        carrier_path = self.carrier_gif_path if is_gif else self.carrier_image_path
        carrier_hash = self.carrier_gif_hash if is_gif else self.carrier_image_hash
        key_entry = self.gif_key_entry if is_gif else self.key_entry
        password_entry = self.gif_password_entry if is_gif else self.password_entry
        logic = self.gif_logic if is_gif else self.image_logic

        self.set_button_state(metadata_button, "disabled", operation=True)
        if not carrier_path:
            messagebox.showerror("Error", f"Select a carrier {'GIF' if is_gif else 'image'}.")
            self.root.after(0, lambda: self.update_progress(0, is_gif))
            self.set_button_state(metadata_button, "normal", operation=True)
            return

        with open(carrier_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if carrier_hash != current_hash:
            messagebox.showerror("Error", f"Carrier {'GIF' if is_gif else 'image'} has been modified since loading!")
            self.root.after(0, lambda: self.update_progress(0, is_gif))
            self.set_button_state(metadata_button, "normal", operation=True)
            return

        key_str = key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.root.after(0, lambda: self.update_progress(0, is_gif))
            self.set_button_state(metadata_button, "normal", operation=True)
            return

        if not logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_progress(0, is_gif))
            self.set_button_state(metadata_button, "normal", operation=True)
            return

        self.current_operation = "metadata"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            password = password_entry.get().strip()
            if is_gif:
                author, timestamp = logic.view_metadata(
                    carrier_path, key_str, password,
                    lambda value: self.root.after(0, lambda v=value: self.update_progress(v, is_gif=True))
                )
                files_count = "N/A"
            else:
                files_data, author, timestamp = logic.extract_data(
                    carrier_path, key_str, password,
                    lambda value: self.root.after(0, lambda v=value: self.update_progress(v))
                )
                files_count = len(files_data)

            self.root.after(0, lambda: self.update_progress(100, is_gif))
            self.root.after(0, lambda: messagebox.showinfo(
                "Metadata",
                f"Metadata for {carrier_path}\n\n"
                f"Author: {author}\nTimestamp: {timestamp}\n"
                f"Files Embedded: {files_count}" if not is_gif else ""
            ))
            self.history_manager.add_entry(
                "View Metadata",
                f"Viewed metadata from {carrier_path} ({'GIF' if is_gif else 'Image'}-Stego)"
            )
            self.update_history_view()
            self.root.after(100, lambda: self.reset_fields(is_gif))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to view metadata: {str(e)}"))
            self.root.after(0, lambda: self.update_progress(0, is_gif))
        finally:
            self.set_button_state(metadata_button, "normal", operation=True)
            self._manage_memory(aggressive=True)
            self.root.after(0, lambda: self.update_progress(0, is_gif))
            # Force UI refresh to ensure reset is visible
            self.root.update_idletasks()

    def cleanup(self):
        """Clean up resources before closing the application."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)
        if hasattr(self, 'process_pool') and self.process_pool:
            self.process_pool.shutdown(wait=False)
        self.carrier_image_path = None
        self.carrier_gif_path = None
        self.data_file_path = None
        self.gif_data_file_path = None
        self.stego_image = None
        gc.collect()

    def _monitor_memory(self):
        """Continuously monitor memory usage and take action if needed."""
        while True:
            try:
                import psutil
                process = psutil.Process()
                memory_usage = process.memory_info().rss
                
                if memory_usage > self.max_memory * 0.9:  # 90% of limit
                    self._manage_memory(aggressive=True)
                elif memory_usage > self.max_memory * 0.8:  # 80% of limit
                    self._manage_memory(aggressive=False)
                    
            except ImportError:
                pass  # psutil not available
            except Exception as e:
                print(f"Memory monitoring error: {str(e)}")
            
            time.sleep(5)  # Check every 5 seconds

    def _process_extraction_chunk(self, chunk_data, key_str, password):
        """Process a chunk of data during extraction using CPU."""
        try:
            # Extract data from the chunk
            extracted_data = []
            for i in range(0, len(chunk_data), 8):
                byte_bits = chunk_data[i:i+8]
                if len(byte_bits) == 8:
                    byte_val = int(''.join(map(str, byte_bits)), 2)
                    extracted_data.append(byte_val)
            
            return bytes(extracted_data)
        except Exception as e:
            raise Exception(f"Chunk processing failed: {str(e)}")

    def _extract_data_optimized(self, carrier_path, key_str, password, is_gif=False):
        """Optimized extraction focusing on CPU usage rather than RAM."""
        logic = self.gif_logic if is_gif else self.image_logic
        
        try:
            # Initialize process pool if needed
            if self.process_pool is None:
                self.process_pool = concurrent.futures.ProcessPoolExecutor(
                    max_workers=self.cpu_count
                )
            
            if is_gif:
                # GIF extraction with chunked processing
                with open(carrier_path, 'rb') as f:
                    gif_data = f.read()
                    
                chunk_size = min(1024 * 1024, self.max_memory // (4 * self.cpu_count))
                chunks = [gif_data[i:i+chunk_size] for i in range(0, len(gif_data), chunk_size)]
                
                futures = []
                for chunk in chunks:
                    future = self.process_pool.submit(
                        logic.extract_chunk,
                        chunk,
                        key_str,
                        password
                    )
                    futures.append(future)
                
                # Process results as they complete
                results = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        print(f"Chunk processing error: {str(e)}")
                
                return b''.join(results)
            
            else:
                # Image extraction with parallel processing
                with Image.open(carrier_path) as img:
                    img = img.convert('RGB')
                    width, height = img.size
                    pixels = np.array(img)
                    
                # Split image into chunks for parallel processing
                chunks = np.array_split(pixels.flatten(), self.cpu_count)
                futures = []
                
                for chunk in chunks:
                    future = self.process_pool.submit(
                        self._process_extraction_chunk,
                        chunk,
                        key_str,
                        password
                    )
                    futures.append(future)
                
                # Combine results
                extracted_data = bytearray()
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        extracted_data.extend(result)
                    except Exception as e:
                        print(f"Chunk processing error: {str(e)}")
                
                return bytes(extracted_data)
                
        except Exception as e:
            raise Exception(f"Extraction failed: {str(e)}")
        finally:
            self._manage_memory(aggressive=True)

if __name__ == "__main__":
    """Main entry point for the application."""
    try:
        root = TkinterDnD.Tk()  # Create root window with drag-and-drop support
        app = SteganographyApp(root)  # Initialize the application
    except RuntimeError as e:
        if "tkdnd" in str(e).lower():
            messagebox.showwarning(
                "Warning",
                "Failed to load tkdnd library for drag-and-drop support. Falling back to basic window."
            )
            root = ctk.CTk()  # Fallback to basic window
            app = SteganographyApp(root)
            # Disable drag-and-drop
            app.image_section.drop_target_register()
            app.data_section.drop_target_register()
            app.gif_section.drop_target_register()
            app.gif_data_section.drop_target_register()
        else:
            raise e
    root.protocol("WM_DELETE_WINDOW", lambda: [app.cleanup(), root.destroy()])  # Cleanup on window close
    root.mainloop()  # Start the main event loop