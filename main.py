import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import numpy as np
from cryptography.fernet import Fernet
import os
import threading
import hashlib
import time
import uuid
from datetime import datetime
import pyperclip
import json
import tempfile
import gc
import struct
from img import SteganographyLogic
from gif import GIFSteganographyLogic
from tkinterdnd2 import TkinterDnD, DND_FILES
import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    tkdnd_path = os.path.join(base_path, 'tkinterdnd2')
    os.environ['TKDND_LIBRARY'] = tkdnd_path
    
button_width = 120
button_pady = 10
button_size = 12
main_font = ("Helvetica", 20, "bold")

class HistoryManager:
    """Manages the history of embedding and extraction operations."""
    def __init__(self):
        self.history_file = "history.json"
        self.history = self.load_history()

    def load_history(self):
        """Load history from file."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_history(self):
        """Save history to file."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=4)

    def add_entry(self, operation, details):
        """Add a new history entry."""
        entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "operation": operation,
            "details": details
        }
        self.history.append(entry)
        self.save_history()

    def get_history(self):
        """Get all history entries."""
        return self.history

class SteganographyApp:
    """Main application class for the steganography GUI."""
    def __init__(self, root):
        self.root = root
        self.root.title("HideNSeek - Steganography Application")
        self.root.geometry("900x700")
        # Disable full screen mode
        self.root.attributes('-fullscreen', False)
        # Intercept attempts to enter fullscreen
        self.root.bind("<F11>", lambda event: "break")
        self.root.bind("<Alt-Return>", lambda event: "break")
        self.root.bind("<Alt-F11>", lambda event: "break")

        # Prevent window resizing
        self.root.resizable(False, False)
        
        self.image_logic = SteganographyLogic()
        print("Available methods in SteganographyLogic:", dir(self.image_logic))
        self.gif_logic = GIFSteganographyLogic()
        print("Available methods in SteganographyLogic:", dir(self.gif_logic))
        self.history_manager = HistoryManager()
        self.carrier_image_path = None
        self.carrier_gif_path = None
        self.data_file_path = None
        self.gif_data_file_path = None
        self.stego_image = None
        self.operation_in_progress = False
        self.estimates_visible = False
        self.current_operation = None
        self.carrier_image_hash = None
        self.carrier_gif_hash = None
        self.image_load_lock = threading.Lock()
        self.gif_load_lock = threading.Lock()
        self.MAX_FILES_SELECTION = 20

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.setup_gui()

    def setup_gui(self):
        """Setup the main GUI with a sidebar and content area."""
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        # Create sidebar with consistent green styling
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=200, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")

        # Add app title at top
        ctk.CTkLabel(self.sidebar_frame, text="HideNSeek", font=("Helvetica", 20, "bold")).pack(pady=20)

        # Create a top frame for main feature buttons (takes most of the sidebar space)
        top_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        top_button_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Store references to sidebar buttons to update their appearance
        self.sidebar_buttons = {}
        
        # Create main feature buttons with consistent size and spacing
        self.sidebar_buttons["image_stego"] = ctk.CTkButton(
            top_button_frame, text="Image-Stego", 
            command=lambda: self.show_frame("image_stego"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", button_size + 2, "bold"),
            height=55,  # Ensure exact same height
            width=160   # Same width
        )
        self.sidebar_buttons["image_stego"].pack(pady=(15, 15), padx=5, fill="x")  # Equal padding above and below

        self.sidebar_buttons["gif_stego"] = ctk.CTkButton(
            top_button_frame, text="GIF-Stego", 
            command=lambda: self.show_frame("gif_stego"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", button_size + 2, "bold"),
            height=55,  # Ensure exact same height
            width=160   # Same width
        )
        self.sidebar_buttons["gif_stego"].pack(pady=(15, 15), padx=5, fill="x")  # Equal padding above and below

        # Create a bottom frame for utility buttons (fixed at bottom)
        bottom_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_button_frame.pack(side="bottom", fill="x", padx=10, pady=20)
        
        # Add a separator line above bottom buttons
        separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#555555")
        separator.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

        # Add utility buttons to bottom frame with consistent styling
        self.sidebar_buttons["history"] = ctk.CTkButton(
            bottom_button_frame, text="History", 
            command=lambda: self.show_frame("history"),
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", 15, "bold"),
            width=140
        )
        self.sidebar_buttons["history"].pack(pady=7, fill="x")

        self.sidebar_buttons["help"] = ctk.CTkButton(
            bottom_button_frame, text="Help", 
            command=self.show_help,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C",
            font=("Helvetica", 15, "bold"),
            width=140
        )
        self.sidebar_buttons["help"].pack(pady=5, fill="x")

        self.content_frame = ctk.CTkFrame(self.main_frame, corner_radius=0)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        self.frames = {}
        self.setup_image_stego_frame()
        self.setup_gif_stego_frame()
        self.setup_history_frame()

        # Ensure the active frame is set and displayed
        print("Setting up GUI: Initializing frames...")
        print(f"Available frames: {list(self.frames.keys())}")
        self.active_frame = None  # Reset active frame to force display
        self.show_frame("image_stego")
        print(f"Displayed frame: {self.active_frame}")
        
        # Force a GUI update to ensure rendering
        self.root.update_idletasks()

    def show_frame(self, frame_name):
        """Show the specified frame in the content area and update sidebar button styles."""
        # Don't do anything if clicking the already active tab
        if hasattr(self, 'active_frame') and self.active_frame == frame_name:
            return
            
        # Hide all frames
        for frame in self.frames.values():
            frame.pack_forget()
        
        # Show the selected frame
        self.frames[frame_name].pack(fill="both", expand=True)
        
        # Update active frame tracking
        self.active_frame = frame_name
        
        # Reset all sidebar button styles
        for name, button in self.sidebar_buttons.items():
            if name == frame_name:
                # Active button styling - darker green background (same as image)
                button.configure(
                    fg_color="#2E7D32",  # Darker green for active tab
                    hover_color="#2E7D32",  # Don't change on hover when active
                    text_color="white",
                    state="disabled",  # Disable clicking on active tab
                    text_color_disabled="white"  # Keep text white when disabled
                )
            else:
                # Normal button styling - lighter green like in your image
                button.configure(
                    fg_color="#4CAF50",  
                    hover_color="#388E3C", 
                    text_color="white",
                    state="normal"  # Enable clicking on inactive tabs
                )
            
    def setup_image_stego_frame(self):
        """Setup the Image-Stego frame with all steganography features."""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.frames["image_stego"] = frame
        print("Created Image-Stego frame")

        scrollable_frame = ctk.CTkScrollableFrame(frame, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.image_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.image_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.image_section, text="Carrier Image", font=main_font).pack(pady=(10, 10))
        
        self.image_button_frame = ctk.CTkFrame(self.image_section, fg_color="transparent")
        self.image_button_frame.pack(pady=(0, 10))
        
        self.load_image_button = ctk.CTkButton(
            self.image_button_frame, text="Browse Image", command=self.load_carrier_image,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width , 
            font=("Helvetica", button_size , "bold") 
        )
        self.load_image_button.pack(side="left", padx=(0, 0))
        
        self.carrier_image_status = ctk.CTkLabel(self.image_section, text="No image selected", text_color="red", font=("Helvetica", 14, "bold"))
        self.carrier_image_status.pack(pady=(0, button_pady))
        
        self.image_section.drop_target_register(DND_FILES)
        self.image_section.dnd_bind('<<Drop>>', self.drop_carrier_image)

        self.data_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.data_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.data_section, text="Data to Hide", font=main_font).pack(pady=(10, 10))

        self.load_data_button = ctk.CTkButton(
            self.data_section, text="Browse Files", command=self.load_data_file,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C" , width=button_width ,
            font=("Helvetica", button_size , "bold")
        )
        self.load_data_button.pack(pady=5)
        self.data_file_status = ctk.CTkLabel(self.data_section, text="No files selected", text_color="red" , font=("Helvetica", 14, "bold"))
        self.data_file_status.pack(pady=5)
        self.data_section.drop_target_register(DND_FILES)
        self.data_section.dnd_bind('<<Drop>>', self.drop_data_file)
        
        self.key_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.key_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.key_section, text="Encryption Key", font=main_font).pack(pady=(10, 10))
        
        self.generate_key_frame = ctk.CTkFrame(self.key_section, fg_color="transparent")
        self.generate_key_frame.pack(pady=2)
        
        self.key_entry = ctk.CTkEntry(
            self.generate_key_frame, 
            width=300, 
            placeholder_text="Enter or generate a key",
            font=("Helvetica", 14, "normal"),
            state="disabled"
        )
        self.key_entry.pack(pady=(0, button_pady))
        
        self.generate_key_button = ctk.CTkButton(
            self.generate_key_frame,
            text="Generate",
            command=self.generate_key,
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            width=button_width,
            font=("Helvetica", button_size, "bold"),
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.generate_key_button.pack(pady=(button_pady, button_pady))
        self.estimates_label = ctk.CTkLabel(
            self.key_section, text="", font=("Helvetica", 12, "italic"),
            text_color="#66BB6A", wraplength=300, justify="left", anchor="w"
        )
        self.estimates_label.pack_forget()

        self.auth_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.auth_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.auth_section, text="Authentication", font=main_font).pack(pady=(10, 10))
        self.password_entry = ctk.CTkEntry(self.auth_section, show="*", width=300, state = "disabled" , placeholder_text="Enter password (optional)" , font=("Helvetica", 14, "normal"))
        self.password_entry.pack(pady=(0, button_pady))
        self.author_entry = ctk.CTkEntry(self.auth_section, width=300, state = "disabled" , placeholder_text="Enter author name (optional)" , font=("Helvetica", 14, "normal"))
        self.author_entry.pack(pady=(button_pady, 20))

        self.action_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.action_frame.pack(fill="x", pady=5)

        button_container = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        button_container.pack(pady=(5, 5), fill="x")

        center_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        center_frame.pack(pady=10, padx=10)

        self.embed_button = ctk.CTkButton(
            center_frame, text="Embed Data", command=self.start_embed,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold") , state = "disabled" ,
            text_color_disabled="#8fbf8f"
        )
        self.embed_button.pack(side="left", padx=10)

        self.extract_button = ctk.CTkButton(
            center_frame, text="Extract Data", command=self.start_extract,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold") , state = "disabled" ,
            text_color_disabled="#8fbf8f"
        )
        self.extract_button.pack(side="left", padx=10)

        self.metadata_button = ctk.CTkButton(
            center_frame, text="View Metadata", command=self.start_view_metadata,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold") , state = "disabled" ,
            text_color_disabled="#8fbf8f"
        )
        self.metadata_button.pack(side="left", padx=10)

        self.progress_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.progress_frame.pack(fill="x", pady=5)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="Progress: 0%", font=("Helvetica", 12, "bold"), text_color="#66BB6A"
        )
        self.progress_label.pack(pady=(5, 2))
        self.progress = ctk.CTkProgressBar(
            self.progress_frame, width=300, height=20, corner_radius=10,
            determinate_speed=2, mode="determinate", fg_color="#2B2B2B", progress_color="#4CAF50"
        )
        self.progress.pack(pady=(0, 5))
        self.progress.set(0)

    def setup_gif_stego_frame(self):
        """Setup the GIF-Stego frame with all steganography features."""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.frames["gif_stego"] = frame

        scrollable_frame = ctk.CTkScrollableFrame(frame, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # GIF Carrier Section
        self.gif_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.gif_section, text="Carrier GIF", font=main_font).pack(pady=(10, 10))
        
        self.gif_button_frame = ctk.CTkFrame(self.gif_section, fg_color="transparent")
        self.gif_button_frame.pack(pady=(0, 10))
        
        self.load_gif_button = ctk.CTkButton(
            self.gif_button_frame, text="Browse GIF", command=self.load_carrier_gif,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold")
        )
        self.load_gif_button.pack(side="left", padx=(0, 0))
        
        self.carrier_gif_status = ctk.CTkLabel(self.gif_section, text="No GIF selected", text_color="red", 
                                            font=("Helvetica", 14, "bold"))
        self.carrier_gif_status.pack(pady=(0, button_pady))
        
        # Make the entire GIF section a drop target
        self.gif_section.drop_target_register(DND_FILES)
        self.gif_section.dnd_bind('<<Drop>>', self.drop_carrier_gif)

        # Data Section
        self.gif_data_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_data_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.gif_data_section, text="Data to Hide", font=main_font).pack(pady=(10, 10))
        
        self.load_gif_data_button = ctk.CTkButton(
            self.gif_data_section, text="Browse Files", command=self.load_gif_data_file,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold")
        )
        self.load_gif_data_button.pack(pady=5)
        
        self.gif_data_file_status = ctk.CTkLabel(self.gif_data_section, text="No files selected", 
                                            text_color="red", font=("Helvetica", 14, "bold"))
        self.gif_data_file_status.pack(pady=5)
        
        # Make the entire data section a drop target
        self.gif_data_section.drop_target_register(DND_FILES)
        self.gif_data_section.dnd_bind('<<Drop>>', self.drop_gif_data_file)

        # Key Section
        self.gif_key_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_key_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.gif_key_section, text="Encryption Key", font=main_font).pack(pady=(10, 10))
        
        self.gif_generate_key_frame = ctk.CTkFrame(self.gif_key_section, fg_color="transparent")
        self.gif_generate_key_frame.pack(pady=2)
        
        self.gif_key_entry = ctk.CTkEntry(
            self.gif_generate_key_frame,
            width=300,
            placeholder_text="Enter or generate a key",
            font=("Helvetica", 14, "normal"),
            state="disabled"
        )
        self.gif_key_entry.pack(pady=(0, button_pady))
        
        self.gif_generate_key_button = ctk.CTkButton(
            self.gif_generate_key_frame,
            text="Generate",
            command=self.generate_gif_key,
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            width=button_width,
            font=("Helvetica", button_size, "bold"),
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_generate_key_button.pack(pady=(button_pady, button_pady))
        
        self.gif_estimates_label = ctk.CTkLabel(
            self.gif_key_section, text="", font=("Helvetica", 12, "italic"),
            text_color="#66BB6A", wraplength=300, justify="left", anchor="w"
        )
        self.gif_estimates_label.pack_forget()

        # Authentication Section
        self.gif_auth_section = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_auth_section.pack(fill="x", pady=5)

        ctk.CTkLabel(self.gif_auth_section, text="Authentication", font=main_font).pack(pady=(10, 10))
        
        self.gif_password_entry = ctk.CTkEntry(self.gif_auth_section, show="*", width=300, 
                                            placeholder_text="Enter password (optional)",
                                            font=("Helvetica", 14, "normal") ,state="disabled")
        self.gif_password_entry.pack(pady=(0, button_pady))
        
        self.gif_author_entry = ctk.CTkEntry(self.gif_auth_section, width=300, 
                                        placeholder_text="Enter author name (optional)",
                                        font=("Helvetica", 14, "normal") , state="disabled")
        self.gif_author_entry.pack(pady=(button_pady, 20))

        # Action Section with centered buttons
        self.gif_action_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_action_frame.pack(fill="x", pady=5)

        # Button container with centered layout
        gif_button_container = ctk.CTkFrame(self.gif_action_frame, fg_color="transparent")
        gif_button_container.pack(pady=(5, 5), fill="x")

        # Center frame to hold the buttons
        gif_center_frame = ctk.CTkFrame(gif_button_container, fg_color="transparent")
        gif_center_frame.pack(pady=10, padx=10)

        self.gif_embed_button = ctk.CTkButton(
            gif_center_frame, text="Embed Data", command=self.start_gif_embed,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_embed_button.pack(side="left", padx=10)

        self.gif_extract_button = ctk.CTkButton(
            gif_center_frame, text="Extract Data", command=self.start_gif_extract,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_extract_button.pack(side="left", padx=10)

        self.gif_metadata_button = ctk.CTkButton(
            gif_center_frame, text="View Metadata", command=self.start_gif_view_metadata,
            corner_radius=8, fg_color="#4CAF50", hover_color="#388E3C", width=button_width,
            font=("Helvetica", button_size, "bold"), state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_metadata_button.pack(side="left", padx=10)

        # Progress Section
        self.gif_progress_frame = ctk.CTkFrame(scrollable_frame, corner_radius=10)
        self.gif_progress_frame.pack(fill="x", pady=5)

        self.gif_progress_label = ctk.CTkLabel(
            self.gif_progress_frame, text="Progress: 0%", font=("Helvetica", 12, "bold"), text_color="#66BB6A"
        )
        self.gif_progress_label.pack(pady=(5, 2))
        
        self.gif_progress = ctk.CTkProgressBar(
            self.gif_progress_frame, width=300, height=20, corner_radius=10,
            determinate_speed=2, mode="determinate", fg_color="#2B2B2B", progress_color="#4CAF50"
        )
        self.gif_progress.pack(pady=(0, 5))
        self.gif_progress.set(0)

    def setup_history_frame(self):
        """Setup the history frame to display past operations."""
        frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.frames["history"] = frame

        ctk.CTkLabel(frame, text="Operation History", font=("Helvetica", 16, "bold")).pack(pady=10)

        # Create a frame to hold the Treeview with both scrollbars
        tree_frame = ctk.CTkFrame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_frame)
        v_scrollbar.pack(side="right", fill="y")

        # Create horizontal scrollbar - Make sure it's visible and working
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")

        # Style configuration to ensure proper display with dark theme
        style = ttk.Style()
        style.theme_use('default')  # Use default theme as base
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", background="#333333", foreground="white")
        
        # Create the Treeview with scrollbar configuration
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=("Timestamp", "Operation", "Details"),
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            style="Treeview"
        )

        # IMPORTANT: Configure the scrollbars to work with the Treeview
        v_scrollbar.config(command=self.history_tree.yview)
        h_scrollbar.config(command=self.history_tree.xview)

        # Configure column headings
        self.history_tree.heading("Timestamp", text="Timestamp")
        self.history_tree.heading("Operation", text="Operation")
        self.history_tree.heading("Details", text="Details")
        
        # Configure column widths - CRITICAL FIX: Make Details column much wider
        self.history_tree.column("Timestamp", width=150, minwidth=150)
        self.history_tree.column("Operation", width=120, minwidth=100)
        # Set a very large width for the Details column to ensure all text is visible when scrolling
        self.history_tree.column("Details", minwidth=200, stretch=False, width=1200)
        
        # Pack the treeview - IMPORTANT: Pack before configuring columns
        self.history_tree.pack(side="left", fill="both", expand=True)
        
        # Set display expansion
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Make sure horizontal scrolling is enabled and showing all columns
        self.history_tree.configure(displaycolumns=("Timestamp", "Operation", "Details"))

        self.update_history_view()

    def show_help(self):
        """Show a help message with instructions."""
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

    def estimate_embedding_time(self):
        """Estimate the time required for image embedding."""
        if not self.carrier_image_path or not self.data_file_path:
            return None

        try:
            key_str = self.key_entry.get().strip()
            temp_logic = SteganographyLogic()
            if not key_str:
                temp_key = Fernet.generate_key()
                temp_logic.get_cipher(temp_key.decode())
            else:
                temp_logic.get_cipher(key_str)

            with Image.open(self.carrier_image_path) as carrier_image:
                carrier_image = carrier_image.convert('RGB')
                image_array = np.array(carrier_image, dtype=np.uint8)
                flat_image = image_array.ravel()

                total_size = sum(os.path.getsize(path) for path in self.data_file_path)
                author = self.author_entry.get().strip() or "N/A"
                author_bytes = author.encode('utf-8', errors='replace')[:50].ljust(50, b' ')
                timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
                metadata = b'\xCA\xFE\xBA\xBE' + author_bytes + timestamp
                encrypted_metadata = temp_logic.cipher.encrypt(metadata)
                estimated_metadata_size = len(encrypted_metadata) + 4

                file_count = len(self.data_file_path)
                file_metadata_size = file_count * (50 + 10 + 4)
                compressed_size = int(total_size * 0.7)
                encrypted_size = compressed_size + 100 * file_count
                total_data_size = (len(b'\xDE\xAD\xBE\xEF') + 32 + 32 + 4 + file_metadata_size + 
                                encrypted_size + estimated_metadata_size + 32 + 4)
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
                bits_per_second = sample_size / (time_taken if time_taken > 0 else 0.0001)
                estimated_time = total_bits / bits_per_second

                return estimated_time * 1.10

        except Exception as e:
            return f"Estimation failed: {str(e)}"

    def estimate_extracting_time(self):
        """Estimate the time required for image extraction."""
        if not self.carrier_image_path:
            return None

        try:
            key_str = self.key_entry.get().strip()
            temp_logic = SteganographyLogic()
            if not key_str:
                temp_key = Fernet.generate_key()
                temp_logic.get_cipher(temp_key.decode())
            else:
                temp_logic.get_cipher(key_str)

            with Image.open(self.carrier_image_path) as carrier_image:
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

    def estimate_gif_embedding_time(self):
        """Estimate the time required for GIF embedding."""
        if not self.carrier_gif_path or not self.gif_data_file_path:
            return None

        try:
            key_str = self.gif_key_entry.get().strip()
            temp_logic = GIFSteganographyLogic()
            if not key_str:
                temp_key = Fernet.generate_key()
                temp_logic.get_cipher(temp_key.decode())
            else:
                temp_logic.get_cipher(key_str)

            total_size = sum(os.path.getsize(path) for path in self.gif_data_file_path)
            file_count = len(self.gif_data_file_path)
            
            author = self.gif_author_entry.get().strip() or "N/A"
            author_bytes = author.encode('utf-8', errors='replace')[:50].ljust(50, b' ')
            timestamp = str(int(time.time())).encode('utf-8')[:20].ljust(20, b' ')
            metadata = b'\xCA\xFE\xBA\xBE' + author_bytes + timestamp
            encrypted_metadata = temp_logic.cipher.encrypt(metadata)
            estimated_metadata_size = len(encrypted_metadata) + 4

            file_metadata_size = file_count * (50 + 10 + 4)
            compressed_size = int(total_size * 0.7)
            encrypted_size = compressed_size + 100 * file_count
            total_data_size = (len(b'\xDE\xAD\xBE\xEF') + 16 + 16 + 4 + file_metadata_size + 
                               encrypted_size + estimated_metadata_size + 32 + 4)

            sample_size = min(1024 * 1024, total_size)
            sample_data = b"\x00" * sample_size
            start_time = time.perf_counter()
            compressed_sample = temp_logic.compress_data(sample_data)
            encrypted_sample = temp_logic.cipher.encrypt(compressed_sample)
            end_time = time.perf_counter()

            time_taken = end_time - start_time
            bytes_per_second = sample_size / (time_taken if time_taken > 0 else 0.0001)
            estimated_time = total_data_size / bytes_per_second

            return estimated_time * 1.10

        except Exception as e:
            return f"Estimation failed: {str(e)}"

    def estimate_gif_extracting_time(self):
        """Estimate the time required for GIF extraction."""
        if not self.carrier_gif_path:
            return None

        try:
            key_str = self.gif_key_entry.get().strip()
            temp_logic = GIFSteganographyLogic()
            if not key_str:
                temp_key = Fernet.generate_key()
                temp_logic.get_cipher(temp_key.decode())
            else:
                temp_logic.get_cipher(key_str)

            with open(self.carrier_gif_path, "rb") as gif_file:
                file_data = gif_file.read()
            total_size = len(file_data)

            sample_size = 1024 * 1024
            sample_data = b"\x00" * sample_size
            compressed_sample = temp_logic.compress_data(sample_data)
            encrypted_sample = temp_logic.cipher.encrypt(compressed_sample)

            start_time = time.perf_counter()
            decrypted_sample = temp_logic.cipher.decrypt(encrypted_sample)
            temp_logic.decompress_data(decrypted_sample)
            end_time = time.perf_counter()

            time_taken = end_time - start_time
            bytes_per_second = sample_size / (time_taken if time_taken > 0 else 0.0001)
            estimated_time = total_size / bytes_per_second

            return estimated_time * 1.05

        except Exception as e:
            return f"Estimation failed: {str(e)}"

    def update_estimated_times(self):
        """Update the estimated times display based on the active frame."""
        if not self.estimates_visible:
            return

        active_frame = self.frames.get("image_stego") if self.frames["image_stego"].winfo_ismapped() else self.frames.get("gif_stego")
        if active_frame == self.frames["image_stego"]:
            if self.current_operation == "embed":
                embed_time = self.estimate_embedding_time()
                if embed_time is None:
                    text = "Estimated Time:\nEmbed: N/A"
                    color = "#66BB6A"
                elif isinstance(embed_time, str):
                    text = f"Estimated Time:\nEmbed: {embed_time}"
                    color = "red"
                else:
                    text = f"Estimated Time:\nEmbed: {embed_time:.2f} seconds"
                    color = "#66BB6A"
            else:
                extract_time = self.estimate_extracting_time()
                text = "Estimated Time:\nExtract: "
                if extract_time is None:
                    text += "N/A"
                    color = "#66BB6A"
                elif isinstance(extract_time, str):
                    text += extract_time
                    color = "red"
                else:
                    text += f"{extract_time:.2f} seconds"
                    color = "#66BB6A"
            self.estimates_label.configure(text=text, text_color=color)
            self.estimates_label.pack(pady=(0, 5))
        elif active_frame == self.frames["gif_stego"]:
            if self.current_operation == "embed":
                embed_time = self.estimate_gif_embedding_time()
                if embed_time is None:
                    text = "Estimated Time:\nEmbed: N/A"
                    color = "#66BB6A"
                elif isinstance(embed_time, str):
                    text = f"Estimated Time:\nEmbed: {embed_time}"
                    color = "red"
                else:
                    text = f"Estimated Time:\nEmbed: {embed_time:.2f} seconds"
                    color = "#66BB6A"
            else:
                extract_time = self.estimate_gif_extracting_time()
                text = "Estimated Time:\nExtract: "
                if extract_time is None:
                    text += "N/A"
                    color = "#66BB6A"
                elif isinstance(extract_time, str):
                    text += extract_time
                    color = "red"
                else:
                    text += f"{extract_time:.2f} seconds"
                    color = "#66BB6A"
            self.gif_estimates_label.configure(text=text, text_color=color)
            self.gif_estimates_label.pack(pady=(0, 5))

    def generate_key(self):
        """Generate a new encryption key and copy it to the clipboard for image stego."""
        # Use SteganographyLogic to generate the key
        self.key = self.image_logic.generate_key()
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, self.key)
        pyperclip.copy(self.key)
        messagebox.showinfo("Key Generated", "Key copied to clipboard.")
        self.history_manager.add_entry("Key Generation", "Generated a new encryption key for Image-Stego.")
        self.update_estimated_times()

    def generate_gif_key(self):
        """Generate a new encryption key and copy it to the clipboard for GIF stego."""
        # This is correctly using gif_logic to generate the key
        self.key = self.gif_logic.generate_key()
        self.gif_key_entry.delete(0, "end")
        self.gif_key_entry.insert(0, self.key)
        pyperclip.copy(self.key)
        messagebox.showinfo("Key Generated", "Key copied to clipboard.")
        self.history_manager.add_entry("Key Generation", "Generated a new encryption key for GIF-Stego.")
        self.update_estimated_times()

    def validate_inputs(self, password_entry, author_entry, for_embedding=True):
        """Validate password and author inputs."""
        password = password_entry.get().strip()
        author = author_entry.get().strip()

        # Sanitize password: remove control characters, limit length
        if password:
            password = "".join(c for c in password if c.isprintable())
            if len(password.encode('utf-8')) > 100:
                messagebox.showerror("Error", "Password must not exceed 100 bytes.")
                return False, None, None

        # Sanitize author: limit to 50 bytes, remove control characters
        if author:
            author = "".join(c for c in author if c.isprintable())
            author_bytes = author.encode('utf-8', errors='replace')
            if len(author_bytes) > 50:
                messagebox.showerror("Error", "Author name must not exceed 50 bytes.")
                return False, None, None
            # Truncate to 50 bytes if necessary
            author = author_bytes[:50].decode('utf-8', errors='ignore')

        # Require password for embedding
        if for_embedding and not password:
            messagebox.showerror("Error", "Password is required for embedding.")
            return False, None, None

        # If not embedding, ensure password is provided if required
        if not for_embedding and not password:
            messagebox.showerror("Error", "Password is required for extraction if it was set during embedding.")
            return False, None, None

        return True, password, author
    
    def drop_carrier_image(self, event):
        """Handle dropped files for carrier image."""
        if self.operation_in_progress or self.image_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        files = self.root.splitlist(event.data)
        if len(files) > 1:
            messagebox.showerror("Error", "Please drop only one image file.")
            return

        file_path = files[0]
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            messagebox.showerror("Error", "Please drop a PNG, JPG, or JPEG file.")
            return

        self.carrier_image_path = file_path
        self.carrier_image_status.configure(text="Loading...", text_color="yellow")
        self.load_image_button.configure(state="disabled")
        threading.Thread(target=self._load_carrier_image, daemon=True).start()

    def load_carrier_image(self, file_path=None):
        """Load the carrier image and compute its hash for integrity."""
        if self.operation_in_progress or self.image_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        if not file_path:
            new_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
            # If user cancels, reset everything
            if not new_path:
                self.reset_fields()
                return
            self.carrier_image_path = new_path
        else:
            self.carrier_image_path = file_path

        print(f"Carrier image path: {self.carrier_image_path}")
        self.carrier_image_status.configure(text="Loading...", text_color="yellow")
        self.load_image_button.configure(state="disabled")
        threading.Thread(target=self._load_carrier_image, daemon=True).start()

    def _load_carrier_image(self):
        """Load the carrier image and compute its hash."""
        with self.image_load_lock:
            try:
                with open(self.carrier_image_path, "rb") as f:
                    self.carrier_image_hash = hashlib.sha256(f.read()).hexdigest()

                # Update status and enable buttons
                self.root.after(0, lambda: self.carrier_image_status.configure(
                    text=f"Image selected ({os.path.basename(self.carrier_image_path)})", 
                    text_color="green"
                ))
                
                # Enable all action buttons when an image is successfully loaded
                self.root.after(0, lambda: self.embed_button.configure(state="normal"))
                self.root.after(0, lambda: self.extract_button.configure(state="normal"))
                self.root.after(0, lambda: self.metadata_button.configure(state="normal"))
                self.root.after(0, lambda: self.generate_key_button.configure(state="normal"))
                
                # Enable the key entry and authentication fields with updated placeholders
                self.root.after(0, lambda: self.key_entry.configure(
                    state="normal", 
                    placeholder_text="Enter or generate a key"
                ))
                self.root.after(0, lambda: self.password_entry.configure(
                    state="normal", 
                    placeholder_text="Enter password (optional)"
                ))
                self.root.after(0, lambda: self.author_entry.configure(
                    state="normal", 
                    placeholder_text="Enter author name (optional)"
                ))
                
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Error", f"Failed to load image: {str(e)}"))
                self.root.after(0, lambda e=e: self.carrier_image_status.configure(text=f"Failed to load image: {str(e)}", text_color="red"))
                
                # Keep buttons disabled if loading fails
                self.root.after(0, lambda: self.embed_button.configure(state="disabled"))
                self.root.after(0, lambda: self.extract_button.configure(state="disabled"))
                self.root.after(0, lambda: self.metadata_button.configure(state="disabled"))
                self.root.after(0, lambda: self.generate_key_button.configure(state="disabled"))
                
            finally:
                self.root.after(0, lambda: self.load_image_button.configure(state="normal"))
                self.root.after(0, self.update_estimated_times)

    def drop_data_file(self, event):
        """Handle dropped files for data to hide in Image-Stego."""
        files = self.root.splitlist(event.data)
        if len(files) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            return

        self.data_file_path = files
        self.data_file_status.configure(
            text=f"{len(self.data_file_path)} files selected" if self.data_file_path else "No files selected",
            text_color="green" if self.data_file_path else "red"
        )
        self.update_estimated_times()

    def load_data_file(self, file_paths=None):
        """Load data files to embed for image stego."""
        if not file_paths:
            self.data_file_path = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])
        else:
            self.data_file_path = file_paths

        if len(self.data_file_path) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            self.data_file_path = []
            self.data_file_status.configure(text="No files selected", text_color="red")
        else:
            self.data_file_status.configure(
                text=f"{len(self.data_file_path)} files selected" if self.data_file_path else "No files selected",
                text_color="green" if self.data_file_path else "red"
            )
        self.update_estimated_times()

    def validate_gif(self, gif_path):
        """Validate the file format as GIF."""
        try:
            with Image.open(gif_path) as img:
                return img.format == "GIF"
        except Exception as e:
            return False

    def drop_carrier_gif(self, event):
        """Handle dropped files for carrier GIF."""
        if self.operation_in_progress or self.gif_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        files = self.root.splitlist(event.data)
        if len(files) > 1:
            messagebox.showerror("Error", "Please drop only one GIF file.")
            return

        file_path = files[0]
        if not file_path.lower().endswith('.gif'):
            messagebox.showerror("Error", "Please drop a GIF file.")
            return

        self.carrier_gif_path = file_path
        if not self.validate_gif(self.carrier_gif_path):
            messagebox.showerror("Error", "Invalid GIF format!")
            self.carrier_gif_path = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            self.update_estimated_times()
            return

        self.carrier_gif_status.configure(text="Loading...", text_color="yellow")
        self.load_gif_button.configure(state="disabled")
        threading.Thread(target=self._load_carrier_gif, daemon=True).start()

    def load_carrier_gif(self, file_path=None):
        """Load the carrier GIF and compute its hash for integrity."""
        if self.operation_in_progress or self.gif_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        if not file_path:
            new_path = filedialog.askopenfilename(filetypes=[("GIF files", "*.gif")])
            # If user cancels, reset everything
            if not new_path:
                self.reset_gif_fields()
                return
            self.carrier_gif_path = new_path
        else:
            self.carrier_gif_path = file_path

        if not self.validate_gif(self.carrier_gif_path):
            messagebox.showerror("Error", "Invalid GIF format!")
            self.carrier_gif_path = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            self.update_estimated_times()
            return

        self.carrier_gif_status.configure(text="Loading...", text_color="yellow")
        self.load_gif_button.configure(state="disabled")
        threading.Thread(target=self._load_carrier_gif, daemon=True).start()

    def _load_carrier_gif(self):
        """Load the carrier GIF and compute its hash."""
        with self.gif_load_lock:
            try:
                with open(self.carrier_gif_path, "rb") as f:
                    self.carrier_gif_hash = hashlib.sha256(f.read()).hexdigest()

                # Update status and enable buttons
                gif_filename = os.path.basename(self.carrier_gif_path)
                self.root.after(0, lambda: self.carrier_gif_status.configure(
                    text=f"GIF selected ({gif_filename})", 
                    text_color="green"
                ))
                
                # Enable buttons when GIF is loaded successfully
                self.root.after(0, lambda: self.gif_embed_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_extract_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_metadata_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_generate_key_button.configure(state="normal"))
                
                # Enable input fields with updated placeholders
                self.root.after(0, lambda: self.gif_key_entry.configure(
                    state="normal", 
                    placeholder_text="Enter or generate a key"
                ))
                self.root.after(0, lambda: self.gif_password_entry.configure(
                    state="normal", 
                    placeholder_text="Enter password (optional)"
                ))
                self.root.after(0, lambda: self.gif_author_entry.configure(
                    state="normal", 
                    placeholder_text="Enter author name (optional)"
                ))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load GIF: {str(e)}"))
                self.root.after(0, lambda: self.carrier_gif_status.configure(
                    text=f"Failed to load GIF: {str(e)}", 
                    text_color="red"
                ))
                
                # Keep buttons disabled if loading fails
                self.root.after(0, lambda: self.gif_embed_button.configure(state="disabled"))
                self.root.after(0, lambda: self.gif_extract_button.configure(state="disabled"))
                self.root.after(0, lambda: self.gif_metadata_button.configure(state="disabled"))
                self.root.after(0, lambda: self.gif_generate_key_button.configure(state="disabled"))
                
            finally:
                self.root.after(0, lambda: self.load_gif_button.configure(state="normal"))
                self.root.after(0, self.update_estimated_times)

    def drop_gif_data_file(self, event):
        """Handle dropped files for data to hide in GIF-Stego."""
        files = self.root.splitlist(event.data)
        if len(files) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            return

        self.gif_data_file_path = files
        self.gif_data_file_status.configure(
            text=f"{len(self.gif_data_file_path)} files selected" if self.gif_data_file_path else "No files selected",
            text_color="green" if self.gif_data_file_path else "red"
        )
        self.update_estimated_times()

    def load_gif_data_file(self, file_paths=None):
        """Load data files to embed for GIF stego."""
        if not file_paths:
            self.gif_data_file_path = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])
        else:
            self.gif_data_file_path = file_paths

        if len(self.gif_data_file_path) > self.MAX_FILES_SELECTION:
            messagebox.showerror("Error", f"You can only select up to {self.MAX_FILES_SELECTION} files at a time.")
            self.gif_data_file_path = []
            self.gif_data_file_status.configure(text="No files selected", text_color="red")
        else:
            self.gif_data_file_status.configure(
                text=f"{len(self.gif_data_file_path)} files selected" if self.gif_data_file_path else "No files selected",
                text_color="green" if self.gif_data_file_path else "red"
            )
        self.update_estimated_times()

    def update_progress(self, value):
        """Update the progress bar and label for image stego."""
        self.progress.set(value / 100)
        self.progress_label.configure(text=f"Progress: {int(value)}%")
        self.root.update_idletasks()

    def update_gif_progress(self, value):
        """Update the progress bar and label for GIF stego."""
        self.gif_progress.set(value / 100)
        self.gif_progress_label.configure(text=f"Progress: {int(value)}%")
        self.root.update_idletasks()

    def reset_fields(self):
        """Reset all fields to their initial state for image stego."""
        # Reset data paths and states
        self.carrier_image_path = None
        self.data_file_path = None
        self.stego_image = None
        self.carrier_image_hash = None
        
        # Reset progress bar
        self.progress.set(0)
        self.progress_label.configure(text="Progress: 0%")
        self.root.update_idletasks()
        
        # Reset status labels to initial state
        self.carrier_image_status.configure(text="No image selected", text_color="red")
        self.data_file_status.configure(text="No files selected", text_color="red")
        
        # Reset estimates
        self.estimates_visible = False
        self.estimates_label.pack_forget()
        
        # Clear and disable all input fields with proper initial state
        self.key_entry.delete(0, "end")
        self.key_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52"
        )
        
        self.password_entry.delete(0, "end")
        self.password_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52",
            show="*"  # Ensure password masking is set
        )
        
        self.author_entry.delete(0, "end")
        self.author_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52"
        )
        
        # Disable all action buttons and reset their appearance
        self.embed_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.extract_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.metadata_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.generate_key_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        
        # Enable the browse button
        self.load_image_button.configure(state="normal")
        
        # Final UI update
        self.root.update_idletasks()

    def reset_gif_fields(self):
        """Reset all fields to their initial state for GIF stego."""
        # Reset data paths and states
        self.carrier_gif_path = None
        self.gif_data_file_path = None
        self.carrier_gif_hash = None
        
        # Reset progress bar
        self.gif_progress.set(0)
        self.gif_progress_label.configure(text="Progress: 0%")
        self.root.update_idletasks()
        
        # Reset status labels to initial state
        self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
        self.gif_data_file_status.configure(text="No files selected", text_color="red")
        
        # Reset estimates
        self.estimates_visible = False
        self.gif_estimates_label.pack_forget()
        
        # Clear and disable all input fields with proper initial state
        self.gif_key_entry.delete(0, "end")
        self.gif_key_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52"
        )
        
        self.gif_password_entry.delete(0, "end")
        self.gif_password_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52",
            show="*"  # Ensure password masking is set
        )
        
        self.gif_author_entry.delete(0, "end")
        self.gif_author_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            placeholder_text_color="gray52"
        )
        
        # Disable all action buttons and reset their appearance
        self.gif_embed_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_extract_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_metadata_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        self.gif_generate_key_button.configure(
            state="disabled",
            text_color_disabled="#8fbf8f"
        )
        
        # Enable the browse button
        self.load_gif_button.configure(state="normal")
        
        # Final UI update
        self.root.update_idletasks()

    def set_button_state(self, button, state, operation=False):
        """Enable/disable buttons during processing."""
        button.configure(state=state)
        if operation:
            self.operation_in_progress = (state == "disabled")

    def start_embed(self):
        """Start the image embedding process."""
        if self.operation_in_progress:
            return

        # Check for carrier image first
        if not self.carrier_image_path:
            messagebox.showerror("Error", "Please select a carrier image first.")
            return

        # Check for data files
        if not self.data_file_path:
            messagebox.showerror("Error", "Please select files to hide first.")
            return

        # Check for encryption key
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please generate or enter an encryption key first.")
            return

        # Check for password
        password = self.password_entry.get().strip()
        if not password:
            messagebox.showerror("Error", "Please enter a password for embedding.")
            return

        # If all checks pass, proceed with validation and embedding
        valid, password, author = self.validate_inputs(self.password_entry, self.author_entry)
        if not valid:
            return
        threading.Thread(target=lambda: self._embed_data_thread(password, author), daemon=True).start()

    def _embed_data_thread(self, password, author):
        """Thread for embedding data into image."""
        self.set_button_state(self.embed_button, "disabled", operation=True)
        if not self.carrier_image_path or not self.data_file_path:
            self.root.after(0, lambda: messagebox.showerror("Error", "Select a carrier image and at least one file to embed."))
            self.set_button_state(self.embed_button, "normal", operation=True)
            return

        key_str = self.key_entry.get().strip()
        if not key_str:
            self.root.after(0, lambda: messagebox.showerror("Error", "Please provide a valid encryption key."))
            self.set_button_state(self.embed_button, "normal", operation=True)
            return

        if not self.image_logic.get_cipher(key_str, self.root):
            self.set_button_state(self.embed_button, "normal", operation=True)
            return

        self.current_operation = "embed"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            # Call embed_data from img.py with validated inputs
            self.stego_image = self.image_logic.embed_data(
                image_path=self.carrier_image_path,
                data_file_paths=self.data_file_path,
                key_str=key_str,
                password=password,
                author=author,
                update_progress_callback=lambda value: self.root.after(0, lambda v=value: self.update_progress(v))
            )

            # Use root.after to handle file dialog in main thread
            def save_stego_image():
                try:
                    save_path = filedialog.asksaveasfilename(
                        defaultextension=".png",
                        filetypes=[("PNG files", "*.png")],
                        initialfile=""  # Empty initial filename
                    )
                    if save_path:
                        self.stego_image.save(save_path, format="PNG", compress_level=0)
                        self.update_progress(100)
                        messagebox.showinfo("Success", f"{len(self.data_file_path)} files embedded successfully!")
                        self.history_manager.add_entry(
                            "Embed",
                            f"Embedded {len(self.data_file_path)} files into {save_path} (Image-Stego)"
                        )
                        self.update_history_view()
                        self.reset_fields()
                    else:
                        self.update_progress(0)
                except Exception as save_error:
                    messagebox.showerror("Error", f"Failed to save image: {str(save_error)}")
                    self.update_progress(0)
                finally:
                    self.set_button_state(self.embed_button, "normal", operation=True)

            self.root.after(0, save_stego_image)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Embedding failed: {str(e)}"))
            self.root.after(0, lambda: self.update_progress(0))
            self.set_button_state(self.embed_button, "normal", operation=True)

    def start_extract(self):
        """Start the image extraction process."""
        if self.operation_in_progress:
            return

        # Check for carrier image first
        if not self.carrier_image_path:
            messagebox.showerror("Error", "Please select a carrier image first.")
            return

        # Check for encryption key
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please generate or enter an encryption key first.")
            return

        # Check for password
        password = self.password_entry.get().strip()
        if not password:
            messagebox.showerror("Error", "Please enter the password used during embedding.")
            return

        # If all checks pass, proceed with validation and extraction
        valid, password, author = self.validate_inputs(self.password_entry, self.author_entry, for_embedding=False)
        if not valid:
            return
        threading.Thread(target=lambda: self._extract_data_thread(password), daemon=True).start()

    def _extract_data_thread(self, password):
        self.set_button_state(self.extract_button, "disabled", operation=True)
        if not self.carrier_image_path:
            messagebox.showerror("Error", "Select a carrier image.")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.extract_button, "normal", operation=True)
            return

        with open(self.carrier_image_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if self.carrier_image_hash != current_hash:
            messagebox.showerror("Error", "Carrier image has been modified since loading!")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.extract_button, "normal", operation=True)
            return

        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.extract_button, "normal", operation=True)
            return

        if not self.image_logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.extract_button, "normal", operation=True)
            return

        self.current_operation = "extract"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            files_data, author, timestamp_readable = self.image_logic.extract_data(
                self.carrier_image_path,
                key_str,
                password,
                lambda value: self.root.after(0, lambda v=value: self.update_progress(v)),
                carrier_filename=self.carrier_image_path
            )

            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if not output_folder:
                self.root.after(0, lambda: messagebox.showinfo("Cancelled", "Extraction cancelled by user."))
                self.root.after(0, lambda: self.update_progress(0))
                self.root.after(0, self.reset_fields)  # Reset immediately when cancelled
                self.set_button_state(self.extract_button, "normal", operation=True)
                return

            stego_name = os.path.splitext(os.path.basename(self.carrier_image_path))[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            subfolder_name = f"Extracted_{stego_name}_{timestamp}"
            output_subfolder = os.path.join(output_folder, subfolder_name)
            os.makedirs(output_subfolder, exist_ok=True)

            for i, (new_filename, ext, file_data) in enumerate(files_data):
                output_filename = f"{new_filename}{ext}"
                output_path = os.path.join(output_subfolder, output_filename)
                with open(output_path, "wb") as output_file:
                    output_file.write(file_data)
                self.root.after(0, lambda v=75 + (25 * (i + 1) // len(files_data)): self.update_progress(v))

            self.root.after(0, lambda: self.update_progress(100))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extracted {len(files_data)} files to {output_subfolder}\n\n"
                f"Metadata:\nAuthor: {author}\nTimestamp: {timestamp_readable}"
            ))
            self.history_manager.add_entry(
                "Extract",
                f"Extracted {len(files_data)} files from {self.carrier_image_path} to {output_subfolder} (Image-Stego)"
            )
            self.update_history_view()
            self.root.after(0, self.reset_fields)  # Reset immediately after success

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Extraction failed: {str(e)}"))
            self.root.after(0, lambda: self.update_progress(0))
            self.root.after(0, self.reset_fields)  # Reset immediately on error
        finally:
            self.set_button_state(self.extract_button, "normal", operation=True)

    def start_view_metadata(self):
        """Start the image metadata viewing process."""
        if self.operation_in_progress:
            return
        threading.Thread(target=self._view_metadata_thread, daemon=True).start()

    def _view_metadata_thread(self):
        """Thread for viewing metadata from image."""
        self.set_button_state(self.metadata_button, "disabled", operation=True)
        if not self.carrier_image_path:
            messagebox.showerror("Error", "Select a carrier image.")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.metadata_button, "normal", operation=True)
            return

        with open(self.carrier_image_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if self.carrier_image_hash != current_hash:
            messagebox.showerror("Error", "Carrier image has been modified since loading!")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.metadata_button, "normal", operation=True)
            return

        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.metadata_button, "normal", operation=True)
            return

        if not self.image_logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
            self.set_button_state(self.metadata_button, "normal", operation=True)
            return

        self.current_operation = "metadata"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            password = self.password_entry.get().strip()
            files_data, author, timestamp = self.image_logic.extract_data(
                self.carrier_image_path, key_str, password,
                lambda value: self.root.after(0, lambda v=value: self.update_progress(v))
            )

            self.root.after(0, lambda: self.update_progress(100))
            self.root.after(0, lambda: messagebox.showinfo(
                "Metadata",
                f"Metadata for {self.carrier_image_path}\n\n"
                f"Author: {author}\nTimestamp: {timestamp}\nFiles Embedded: {len(files_data)}"
            ))
            self.history_manager.add_entry(
                "View Metadata",
                f"Viewed metadata from {self.carrier_image_path} (Image-Stego)"
            )
            self.update_history_view()
            self.root.after(100, self.reset_fields)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to view metadata: {str(e)}"))
            self.root.after(0, lambda: self.update_progress(0))
        finally:
            self.set_button_state(self.metadata_button, "normal", operation=True)

    def start_gif_embed(self):
        """Start the GIF embedding process."""
        if self.operation_in_progress:
            return

        # Check for carrier GIF first
        if not self.carrier_gif_path:
            messagebox.showerror("Error", "Please select a carrier GIF first.")
            return

        # Check for data files
        if not self.gif_data_file_path:
            messagebox.showerror("Error", "Please select files to hide first.")
            return

        # Check for encryption key
        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please generate or enter an encryption key first.")
            return

        # Check for password
        password = self.gif_password_entry.get().strip()
        if not password:
            messagebox.showerror("Error", "Please enter a password for embedding.")
            return

        # If all checks pass, proceed with validation and embedding
        valid, password, author = self.validate_inputs(self.gif_password_entry, self.gif_author_entry)
        if not valid:
            return
        threading.Thread(target=lambda: self._gif_embed_data_thread(password, author), daemon=True).start()

    def _gif_embed_data_thread(self, password, author):
        """Thread for embedding data into GIF."""
        self.set_button_state(self.gif_embed_button, "disabled", operation=True)
        if not self.carrier_gif_path or not self.gif_data_file_path:
            messagebox.showerror("Error", "Select a carrier GIF and at least one file to embed.")
            self.set_button_state(self.gif_embed_button, "normal", operation=True)
            return

        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.set_button_state(self.gif_embed_button, "normal", operation=True)
            return

        if not self.gif_logic.get_cipher(key_str, self.root):
            self.set_button_state(self.gif_embed_button, "normal", operation=True)
            return

        self.current_operation = "embed"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            output_data = self.gif_logic.embed_data(
                self.carrier_gif_path,
                self.gif_data_file_path,
                key_str,
                password,
                author,
                lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
            )

            save_path = filedialog.asksaveasfilename(
                defaultextension=".gif",
                filetypes=[("GIF files", "*.gif")],
                initialfile=""  # Empty initial filename
            )
            
            if save_path:
                with open(save_path, "wb") as output_file:
                    output_file.write(output_data)
                self.update_gif_progress(100)
                messagebox.showinfo("Success", f"{len(self.gif_data_file_path)} files embedded successfully!")
                self.history_manager.add_entry(
                    "Embed",
                    f"Embedded {len(self.gif_data_file_path)} files into {save_path} (GIF-Stego)"
                )
                self.update_history_view()
                self.root.after(100, self.reset_gif_fields)

        except Exception as e:
            messagebox.showerror("Error", f"Embedding failed: {str(e)}")
            self.update_gif_progress(0)
        finally:
            self.set_button_state(self.gif_embed_button, "normal", operation=True)

    def start_gif_extract(self):
        """Start the GIF extraction process."""
        if self.operation_in_progress:
            return

        # Check for carrier GIF first
        if not self.carrier_gif_path:
            messagebox.showerror("Error", "Please select a carrier GIF first.")
            return

        # Check for encryption key
        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please generate or enter an encryption key first.")
            return

        # Check for password
        password = self.gif_password_entry.get().strip()
        if not password:
            messagebox.showerror("Error", "Please enter the password used during embedding.")
            return

        # If all checks pass, proceed with validation and extraction
        valid, password, author = self.validate_inputs(self.gif_password_entry, self.gif_author_entry, for_embedding=False)
        if not valid:
            return
        threading.Thread(target=lambda: self._gif_extract_data_thread(password), daemon=True).start()

    def _gif_extract_data_thread(self, password):
        self.set_button_state(self.gif_extract_button, "disabled", operation=True)
        if not self.carrier_gif_path:
            messagebox.showerror("Error", "Select a carrier GIF.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        with open(self.carrier_gif_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if self.carrier_gif_hash != current_hash:
            messagebox.showerror("Error", "Carrier GIF has been modified since loading!")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        if not self.gif_logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        self.current_operation = "extract"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            files_data, author, timestamp = self.gif_logic.extract_data(
                self.carrier_gif_path, key_str, password,
                lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
            )

            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if not output_folder:
                self.root.after(0, lambda: messagebox.showinfo("Cancelled", "Extraction cancelled by user."))
                self.root.after(0, lambda: self.update_gif_progress(0))
                self.root.after(0, self.reset_gif_fields)  # Reset immediately when cancelled
                self.set_button_state(self.gif_extract_button, "normal", operation=True)
                return

            carrier_filename = os.path.splitext(os.path.basename(self.carrier_gif_path))[0]
            extraction_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            subfolder_name = f"Extracted_{carrier_filename}_{extraction_time}"
            output_subfolder = os.path.join(output_folder, subfolder_name)
            os.makedirs(output_subfolder, exist_ok=True)

            for i, (filename, ext, file_data) in enumerate(files_data):
                output_filename = f"{filename.strip()}{ext.strip()}"
                output_filename = "".join(c for c in output_filename if c.isalnum() or c in ('.', '_', '-'))
                output_path = os.path.join(output_subfolder, output_filename)
                with open(output_path, "wb") as output_file:
                    output_file.write(file_data)
                self.root.after(0, lambda v=75 + (25 * (i + 1) // len(files_data)): self.update_gif_progress(v))

            self.root.after(0, lambda: self.update_gif_progress(100))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extracted {len(files_data)} files to {output_subfolder}\n\n"
                f"Metadata:\nAuthor: {author}\nTimestamp: {timestamp}"
            ))
            self.history_manager.add_entry(
                "Extract",
                f"Extracted {len(files_data)} files from {self.carrier_gif_path} to {output_subfolder} (GIF-Stego)"
            )
            self.update_history_view()
            self.root.after(0, self.reset_gif_fields)  # Reset immediately after success

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Extraction failed: {str(e)}"))
            self.root.after(0, lambda: self.update_gif_progress(0))
            self.root.after(0, self.reset_gif_fields)  # Reset immediately on error
        finally:
            self.set_button_state(self.gif_extract_button, "normal", operation=True)

    def start_gif_view_metadata(self):
        """Start the GIF metadata viewing process."""
        if self.operation_in_progress:
            return
        threading.Thread(target=self._gif_view_metadata_thread, daemon=True).start()

    def _gif_view_metadata_thread(self):
        """Thread for viewing metadata from GIF."""
        self.set_button_state(self.gif_metadata_button, "disabled", operation=True)
        if not self.carrier_gif_path:
            messagebox.showerror("Error", "Select a carrier GIF.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)
            return

        with open(self.carrier_gif_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if self.carrier_gif_hash != current_hash:
            messagebox.showerror("Error", "Carrier GIF has been modified since loading!")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)
            return

        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Error", "Please provide a valid encryption key.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)
            return

        if not self.gif_logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)
            return

        self.current_operation = "metadata"
        self.estimates_visible = True
        self.update_estimated_times()

        try:
            password = self.gif_password_entry.get().strip()
            author, timestamp = self.gif_logic.view_metadata(
                self.carrier_gif_path, key_str, password,
                lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
            )

            self.root.after(0, lambda: self.update_gif_progress(100))
            self.root.after(0, lambda: messagebox.showinfo(
                "Metadata",
                f"Metadata for {self.carrier_gif_path}\n\n"
                f"Author: {author}\nTimestamp: {timestamp}"
            ))
            self.history_manager.add_entry(
                "View Metadata",
                f"Viewed metadata from {self.carrier_gif_path} (GIF-Stego)"
            )
            self.update_history_view()
            self.root.after(100, self.reset_gif_fields)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to view metadata: {str(e)}"))
            self.root.after(0, lambda: self.update_gif_progress(0))
        finally:
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)

    def cleanup(self):
        """Clean up resources before closing the application."""
        self.carrier_image_path = None
        self.carrier_gif_path = None
        self.data_file_path = None
        self.gif_data_file_path = None
        self.stego_image = None
        gc.collect()
        
if __name__ == "__main__":
    try:
        root = TkinterDnD.Tk()
        app = SteganographyApp(root)
    except RuntimeError as e:
        if "tkdnd" in str(e).lower():
            messagebox.showwarning(
                "Warning",
                "Failed to load tkdnd library for drag-and-drop support. Falling back to basic window."
            )
            root = ctk.CTk()
            app = SteganographyApp(root)
            # Disable drag-and-drop functionality
            app.image_section.drop_target_register()  # Unregister DND
            app.data_section.drop_target_register()
            app.gif_section.drop_target_register()
            app.gif_data_section.drop_target_register()
        else:
            raise e
    root.protocol("WM_DELETE_WINDOW", lambda: [app.cleanup(), root.destroy()])
    root.mainloop()