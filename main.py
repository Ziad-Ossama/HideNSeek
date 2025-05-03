import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
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
import logging

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
        self.root.title("HideNSeek")
        self.root.geometry("900x700")

        # Load and set the application icon
        icon_path = os.path.join("assets", "logo.png")
        if os.path.exists(icon_path):
            try:
                # For taskbar icon we still need to use PhotoImage
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, icon_photo)
                print(f"Successfully loaded icon from {icon_path}")
            except Exception as e:
                print(f"Error loading icon: {str(e)}")
            
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

        # Load and display the logo
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                # Use CTkImage for better HighDPI support
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(120, 120)
                )
                
                # Create and pack the logo label
                logo_label = ctk.CTkLabel(self.sidebar_frame, image=logo_image, text="")
                logo_label.pack(pady=(20, 10))
                print(f"Successfully loaded sidebar logo from {logo_path}")
            except Exception as e:
                print(f"Error loading sidebar logo: {str(e)}")

        # Add app title below the logo
        ctk.CTkLabel(self.sidebar_frame, text="HideNSeek", font=("Helvetica", 20, "bold")).pack(pady=(0, 20))

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
            state="disabled" , 
            show="*"
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
            state="disabled" , 
            show="*"
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
                            "4. Add a password and (Optional) author name.\n"
                            "5. Click 'Embed Data' to hide data, 'Extract Data' to retrieve it, or 'View Metadata' to see details.\n"
                            "6. Check the history tab to see past operations.\n\n"
                            "Note: Ensure the key and password match during extraction!")

    def generate_key(self):
        """Generate a new encryption key and copy it to the clipboard for image stego."""
        # Use SteganographyLogic to generate the key
        self.key = self.image_logic.generate_key()
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, self.key)
        pyperclip.copy(self.key)
        messagebox.showinfo("Key Generated", "Key copied to clipboard.")
        self.history_manager.add_entry("Key Generation", "Generated a new encryption key for Image-Stego.")

    def generate_gif_key(self):
        """Generate a new encryption key and copy it to the clipboard for GIF stego."""
        # This is correctly using gif_logic to generate the key
        self.key = self.gif_logic.generate_key()
        self.gif_key_entry.delete(0, "end")
        self.gif_key_entry.insert(0, self.key)
        pyperclip.copy(self.key)
        messagebox.showinfo("Key Generated", "Key copied to clipboard.")
        self.history_manager.add_entry("Key Generation", "Generated a new encryption key for GIF-Stego.")

    def analyze_lsb_entropy(self, image_path):
        """Analyze LSB entropy of an image to determine its suitability as a carrier."""
        img = Image.open(image_path).convert("RGB")
        pixels = np.array(img)
        flat = pixels.flatten()
        lsb_bits = flat & 1
        ratio = np.sum(lsb_bits) / lsb_bits.size
        deviation = abs(0.5 - ratio) * 2
        entropy_score = (1 - deviation) * 100

        if entropy_score >= 95:
            return f"✅ Excellent carrier image (LSB Entropy: {entropy_score:.2f}%)"
        elif entropy_score >= 85:
            return f"🟡 Good carrier (LSB Entropy: {entropy_score:.2f}%)"
        elif entropy_score >= 70:
            return f"⚠️ Fair carrier – Consider a more random image (LSB Entropy: {entropy_score:.2f}%)"
        else:
            return f"❌ Poor carrier – LSBs too predictable (LSB Entropy: {entropy_score:.2f}%)"

    def drop_carrier_image(self, event):
        """Handle dropped files for carrier image."""
        if self.operation_in_progress or self.image_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        files = self.root.splitlist(event.data)
        if len(files) > 1:
            messagebox.showerror("Carrier Fail", "Please Drop Only One Image File.")
            return

        file_path = files[0]
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            messagebox.showerror("Carrier Fail", "Please Drop a PNG, JPG, or JPEG File.")
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
                
                # Get the filename from the path
                filename = os.path.basename(self.carrier_image_path)
                
                # First show the filename that was selected
                self.root.after(0, lambda fname=filename: self.carrier_image_status.configure(
                    text=f"Image selected: {fname}", 
                    text_color="green"
                ))
                
                # Create a frame to hold multiple status messages if it doesn't exist
                if not hasattr(self, 'entropy_label'):
                    self.entropy_label = ctk.CTkLabel(
                        self.image_section, 
                        text="", 
                        text_color="orange", 
                        font=("Helvetica", 12, "bold")
                    )
                
                # Make sure the label is added to the UI
                try:
                    # First, show the label if it was previously hidden
                    self.entropy_label.pack(pady=(0, button_pady))
                except:
                    # If there's an error (like if it's already packed), pack it again
                    self.entropy_label.pack_forget()
                    self.entropy_label.pack(pady=(0, button_pady))
                
                # Then analyze LSB randomness and display it in the separate label
                entropy_msg = self.analyze_lsb_entropy(self.carrier_image_path)
                self.root.after(0, lambda msg=entropy_msg: self.entropy_label.configure(
                    text=msg, 
                    text_color="orange"
                ))
                print(f"LSB Entropy Analysis: {entropy_msg}")
                
                # Enable all action buttons when an image is successfully loaded
                self.root.after(0, lambda: self.embed_button.configure(state="normal"))
                self.root.after(0, lambda: self.extract_button.configure(state="normal"))
                self.root.after(0, lambda: self.metadata_button.configure(state="normal"))
                self.root.after(0, lambda: self.generate_key_button.configure(state="normal"))
                
                # Enable the key entry and authentication fields with updated placeholders
                self.root.after(0, lambda: self.key_entry.configure(
                    state="normal", 
                    placeholder_text="Enter or generate a key", 
                    show="*"
                ))
                self.root.after(0, lambda: self.password_entry.configure(
                    state="normal", 
                    placeholder_text="Enter password", 
                    show="*"
                ))
                self.root.after(0, lambda: self.author_entry.configure(
                    state="normal", 
                    placeholder_text="Enter author name (optional)"
                ))
                
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Carrier Fail", f"Failed to Load Image"))
                self.root.after(0, lambda e=e: self.carrier_image_status.configure(text=f"Failed to Load Image", text_color="red"))
                self.root.after(0, self.reset_fields)
                
            finally:
                self.root.after(0, lambda: self.load_image_button.configure(state="normal"))

    def _load_carrier_image_thread(self, new_path):
        """Thread to load a carrier image."""
        try:
            # Verify the image can be opened
            try:
                Image.open(new_path).verify()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Carrier Fail", f"Invalid Image File"))
                # Reset all fields regardless of whether there was a previous image
                self.root.after(0, self.reset_fields)
                return
                
            # Update the carrier path and start loading
            self.carrier_image_path = new_path
            self._load_carrier_image()
            
        except Exception as e:
            logging.error(f"Failed to load carrier image")
            self.root.after(0, lambda: messagebox.showerror("Carrier Fail", f"Failed to Load Image"))
            # Reset all fields regardless of whether there was a previous image
            self.root.after(0, self.reset_fields)
        finally:
            self.root.after(0, lambda: self.load_image_button.configure(state="normal"))

    def drop_data_file(self, event):
        """Handle dropped files for data to hide in Image-Stego."""
        MAX_FILES = 20
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per file for images
        MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB total

        files = self.root.splitlist(event.data)
        if len(files) > MAX_FILES:
            messagebox.showerror("Data Fail", f"You Can Only Select Up to {MAX_FILES} Files at a Time.")
            return

        # Check file sizes
        total_size = 0
        oversized_files = []
        for path in files:
            file_size = os.path.getsize(path)
            if file_size > MAX_FILE_SIZE:
                oversized_files.append(f"'{os.path.basename(path)}' ({file_size / (1024*1024):.1f} MB)")
            total_size += file_size
            if total_size > MAX_TOTAL_SIZE:
                messagebox.showerror("Data Fail", 
                    f"Total Size of Dropped Files ({total_size / (1024*1024):.1f} MB) "
                    f"Exceeds The Maximum Limit of {MAX_TOTAL_SIZE / (1024*1024):.1f} MB")
                return

        if oversized_files:
            messagebox.showerror("Error",
                f"The Following Files Exceed The {MAX_FILE_SIZE / (1024*1024):.1f} MB Per-File Limit:\n\n" +
                "\n".join(oversized_files))
            return

        self.data_file_path = files
        self.data_file_status.configure(
            text=f"{len(self.data_file_path)} Files Selected (Total: {total_size / (1024*1024):.1f} MB)" 
            if self.data_file_path else "No Files Selected",
            text_color="green" if self.data_file_path else "red"
        )

    def load_data_file(self, file_paths=None):
        """Load data files to embed for image stego."""
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per file for images
        MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB total
        MAX_FILES = 20

        if not file_paths:
            self.data_file_path = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])
        else:
            self.data_file_path = file_paths

        if len(self.data_file_path) > MAX_FILES:
            messagebox.showerror("Data Fail", f"You Can Only Select Up to {MAX_FILES} Files at a Time.")
            self.data_file_path = []
            self.data_file_status.configure(text="No Files Selected", text_color="red")
            return

        # Check file sizes
        total_size = 0
        oversized_files = []
        for path in self.data_file_path:
            file_size = os.path.getsize(path)
            if file_size > MAX_FILE_SIZE:
                oversized_files.append(f"'{os.path.basename(path)}' ({file_size / (1024*1024):.1f} MB)")
            total_size += file_size
            if total_size > MAX_TOTAL_SIZE:
                messagebox.showerror("Data Fail", 
                    f"Total size of selected files ({total_size / (1024*1024):.1f} MB) "
                    f"Exceeds The Maximum Limit of {MAX_TOTAL_SIZE / (1024*1024):.1f} MB")
                self.data_file_path = []
                self.data_file_status.configure(text="No Files Selected", text_color="red")
                return

        if oversized_files:
            messagebox.showerror("Data Fail",
                f"The Following Files Exceed The {MAX_FILE_SIZE / (1024*1024):.1f} MB Per-File Limit:\n\n" +
                "\n".join(oversized_files))
            self.data_file_path = []
            self.data_file_status.configure(text="No Files Selected", text_color="red")
            return

        self.data_file_status.configure(
            text=f"{len(self.data_file_path)} Files Selected (Total: {total_size / (1024*1024):.1f} MB)" 
            if self.data_file_path else "No Files Selected",
            text_color="green" if self.data_file_path else "red"
        )
        
    def start_embed(self):
        """Start the embedding process."""
        if self.operation_in_progress:
            return
            
        # Check for carrier image first
        if not self.carrier_image_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier Image.")
            return
            
        # Check for data files
        if not self.data_file_path:
            messagebox.showerror("Data Fail", "Please Select One or More Data Files to Embed.")
            return

        # Check for encryption key
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Embeding Error", "Please Generate or Enter an Encryption Key.")
            return
        
        # Check for password
        password = self.password_entry.get().strip()
        if not password:
            messagebox.showerror("Embeding Error", "Please Enter a Password.")
            return
        
        # Validate password and author inputs
        valid, password, author = self.validate_inputs(self.password_entry, self.author_entry, for_embedding=True)
        if not valid:
            return
            
        # Start embedding in a separate thread to keep UI responsive
        threading.Thread(target=lambda: self._embed_data_thread(password, author), daemon=True).start()

    def _embed_data_thread(self, password, author):
        """Embed data into the carrier image in a separate thread."""
        self.set_button_state(self.embed_button, "disabled", operation=True)
        try:
            # Validate carrier and data file paths
            if not self.carrier_image_path or not self.data_file_path:
                messagebox.showerror("Embeding Error", "Missing carrier image or data files.")
                self.root.after(0, lambda: self.update_progress(0))
                self.set_button_state(self.embed_button, "normal", operation=True)
                return

            # Verify carrier image hash
            with open(self.carrier_image_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if self.carrier_image_hash != current_hash:
                messagebox.showerror("Embeding Error", "Carrier Image has been Modified since Loading!")
                self.root.after(0, lambda: self.update_progress(0))
                self.set_button_state(self.embed_button, "normal", operation=True)
                return

            # Get encryption key
            key_str = self.key_entry.get().strip()
            if not key_str:
                messagebox.showerror("Embeding Error", "Please Provide a valid encryption key.")
                self.root.after(0, lambda: self.update_progress(0))
                self.set_button_state(self.embed_button, "normal", operation=True)
                return

            # Initialize cipher with the key
            if not self.image_logic.get_cipher(key_str, self.root):
                self.root.after(0, lambda: self.update_progress(0))
                self.set_button_state(self.embed_button, "normal", operation=True)
                return

            # Update operation type and estimates
            self.current_operation = "embed"
            self.estimates_visible = True

            # Embed the data
            self.stego_image = self.image_logic.embed_data(
                self.carrier_image_path,
                self.data_file_path,
                key_str,
                password,
                author,
                lambda value: self.root.after(0, lambda v=value: self.update_progress(v))
            )

            # Prompt user to save the embedded image
            def save_stego_image():
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                    initialfile=""  # Empty initial filename
                )
                
                if save_path:
                    # Save the embedded image
                    self.stego_image.save(save_path)
                    self.update_progress(100)
                    messagebox.showinfo("Embedding Success", "Data embedded successfully!")
                    self.history_manager.add_entry(
                        "Embed",
                        f"Embedded {len(self.data_file_path)} files into {save_path} (Image-Stego)"
                    )
                    self.update_history_view()
                    self.root.after(100, self.reset_fields)
                else:
                    # User canceled saving
                    messagebox.showinfo("Embedding Cancelled", "Embedding operation cancelled by user.")
                    # Clear embedded data from memory but keep settings
                    self.stego_image = None
                    # Reset progress bar only
                    self.root.after(0, lambda: self.update_progress(0))
                    # Force garbage collection to free memory
                    import gc
                    gc.collect()
            
            # Schedule save dialog on the main thread
            self.root.after(0, save_stego_image)

        except Exception as e:
            logging.error(f"Embedding failed: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Embeding Failed",str(e)))
            self.root.after(0, lambda: self.update_progress(0))
            self.root.after(0, self.reset_fields)
        finally:
            self.set_button_state(self.embed_button, "normal", operation=True)

    def start_extract(self):
        """Start the image extraction process."""
        if self.operation_in_progress:
            return

        # Check for carrier image first
        if not self.carrier_image_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier Image.")
            return

        # Check for encryption key
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Extraction Error", "Please Generate or Enter an Encryption Key.")
            return

        # Check for password
        password = self.password_entry.get().strip()
        if not password:
            messagebox.showerror("Extraction Error", "Please Enter the Password Used During Embedding.")
            return

        # If all checks pass, proceed with validation and extraction
        valid, password, author = self.validate_inputs(self.password_entry, self.author_entry, for_embedding=False)
        if not valid:
            return
        threading.Thread(target=lambda: self._extract_data_thread(password), daemon=True).start()

    def _extract_data_thread(self, password):
        """Extract data from the carrier image in a separate thread."""
        try:
            self.set_button_state(self.extract_button, "disabled", operation=True)
            if not self.carrier_image_path:
                messagebox.showerror("Carrier Fail", "Select a carrier image.")
                self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
                self.set_button_state(self.extract_button, "normal", operation=True)
                return

            with open(self.carrier_image_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if self.carrier_image_hash != current_hash:
                messagebox.showerror("Carrier Fail", "Carrier image has been modified since loading!")
                self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
                self.set_button_state(self.extract_button, "normal", operation=True)
                return

            key_str = self.key_entry.get().strip()
            if not key_str:
                messagebox.showerror("Extraction Error", "Please provide a valid encryption key.")
                self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
                self.set_button_state(self.extract_button, "normal", operation=True)
                return

            if not self.image_logic.get_cipher(key_str, self.root):
                self.root.after(0, lambda: self.update_progress(0))  # Reset progress on error
                self.set_button_state(self.extract_button, "normal", operation=True)
                return

            self.current_operation = "extract"
            self.estimates_visible = True


            files_data, author, timestamp_readable = self.image_logic.extract_data(
                self.carrier_image_path,
                key_str,
                password,
                lambda value: self.root.after(0, lambda v=value: self.update_progress(v)),
                carrier_filename=self.carrier_image_path
            )

            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if not output_folder:
                self.root.after(0, lambda: messagebox.showinfo("Extraction Canceled", "Extraction cancelled by user."))
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
                "Extraction Success",
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
            logging.error(f"Extraction failed: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Extraction Error", str(e)))
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
        """View metadata from a stego image in a separate thread."""
        self.set_button_state(self.metadata_button, "disabled", operation=True)
        
        if not self.carrier_image_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier Image.")
            self.set_button_state(self.metadata_button, "normal", operation=True)
            return
        
        try:
            self.update_progress(10)
            
            # First check if this is a steganography image
            is_stego, message = self.detect_image_steganography(self.carrier_image_path)
            if not is_stego:
                messagebox.showinfo("Information", "This Is Not a Steganography Image.")
                self.update_progress(0)
                self.set_button_state(self.metadata_button, "normal", operation=True)
                return
            else:
                print("[STEGO DETECTION] This is a stego image.")
                
            # Get encryption key
            key_str = self.key_entry.get().strip()
            if not key_str:
                messagebox.showerror("Extraction Error", "Please Provide an Encryption Key.")
                self.update_progress(0)
                self.set_button_state(self.metadata_button, "normal", operation=True)
                return
                
            # Get password 
            password = self.password_entry.get().strip()
            if not password:
                messagebox.showerror("Extraction Error", "Please Enter The Password Used During Embedding.")
                self.update_progress(0)
                self.set_button_state(self.metadata_button, "normal", operation=True)
                return
            
            self.update_progress(20)
            
            # Initialize cipher with the key
            if not self.image_logic.get_cipher(key_str, self.root):
                self.update_progress(0)
                self.set_button_state(self.metadata_button, "normal", operation=True)
                return
                
            self.update_progress(30)
            
            # Try to extract metadata
            try:
                # Use image_logic to extract data
                files_data, author, timestamp = self.image_logic.extract_data(
                    self.carrier_image_path,
                    key_str,
                    password,
                    lambda value: self.root.after(0, lambda v=value: self.update_progress(v)),
                    carrier_filename=self.carrier_image_path
                )
                
                self.update_progress(100)
                
                # Display the metadata
                messagebox.showinfo(
                    "Metadata Information",
                    f"Metadata successfully extracted!\n\n"
                    f"File contains {len(files_data)} embedded files\n"
                    f"Author: {author}\n"
                    f"Timestamp: {timestamp}"
                )
                
                self.history_manager.add_entry(
                    "View Metadata",
                    f"Viewed metadata from {self.carrier_image_path} (Image-Stego)"
                )
                self.update_history_view()
                
            except ValueError as extract_error:
                error_str = str(extract_error).lower()
                
                # Check for specific errors
                if "key mismatch" in error_str or "incorrect key" in error_str:
                    messagebox.showerror("Extraction Error", "The Encryption Key or The Password is Incorrect.")
                elif "password mismatch" in error_str or "incorrect password" in error_str:
                    messagebox.showerror("Extraction Error", "The Encryption Key or The Password is Incorrect.")
                else:
                    messagebox.showerror("Extraction Error", f"Error Reading Image Metadata")
            
        except Exception as e:
            logging.error(f"Failed to view Image Metadata")
            messagebox.showerror("Extraction Error", f"Failed to view Image Metadata")
            
        finally:
            self.update_progress(0)
            self.set_button_state(self.metadata_button, "normal", operation=True)

    def detect_image_steganography(self, image_path):
        """Detect if an image contains hidden data using our LSB steganography technique.
        Based on the proven detection logic from stego_detect.py"""
        try:
            print(f"[StegoDetector] Checking image: {image_path}")
            
            # Attempt to open and process the image
            try:
                print("[StegoDetector] Loading and converting image to RGB...")
                carrier_image = Image.open(image_path).convert('RGB')
                print("[StegoDetector] Converting image to numpy array...")
                image_array = np.array(carrier_image, dtype=np.uint8)
                print("[StegoDetector] Flattening image array...")
                flat_image = image_array.flatten()
                print(f"[StegoDetector] Image array flattened, size: {len(flat_image)} pixels")
            except Exception as e:
                print(f"[StegoDetector] Error processing image: {str(e)}")
                return False, f"Error processing image: {str(e)}"

            # Extract bits from LSBs
            print("[StegoDetector] Extracting bits from LSBs...")
            bits = []
            i = 0
            found_termination = False
            while i < len(flat_image):
                bit = flat_image[i] & 1
                bits.append(str(bit))
                i += 1
                if i % 1000000 == 0:
                    print(f"[StegoDetector] Processed {i} pixels...")
                if i >= 16 and ''.join(bits[-16:]) == '1111111111111110':
                    print("[StegoDetector] Termination sequence '1111111111111110' found!")
                    found_termination = True
                    break

            if not found_termination:
                print("[StegoDetector] Reached end of image without finding termination sequence.")
                return False, "No steganography detected: No termination sequence found."

            print(f"[StegoDetector] Extracted {i} bits before termination sequence.")

            # Convert bits to bytes
            print("[StegoDetector] Converting bits to bytes...")
            data_bits = bits[:-16]
            print(f"[StegoDetector] Total data bits (excluding termination): {len(data_bits)}")
            byte_array = bytearray()
            for j in range(0, len(data_bits), 8):
                if j + 8 <= len(data_bits):
                    byte = ''.join(data_bits[j:j+8])
                    byte_array.append(int(byte, 2))
            full_data = bytes(byte_array)
            print(f"[StegoDetector] Converted to {len(full_data)} bytes of data.")

            # Check for data length
            print("[StegoDetector] Checking data length prefix...")
            if len(full_data) < 4:
                print("[StegoDetector] Data length prefix missing or invalid.")
                return False, "No steganography detected: Invalid data length."

            data_length = struct.unpack(">I", full_data[:4])[0]
            print(f"[StegoDetector] Data length from prefix: {data_length} bytes")
            
            # Use a reasonable size limit directly
            MAX_REASONABLE_SIZE = 1024 * 1024 * 500  # 500 MB max
            if data_length > MAX_REASONABLE_SIZE:
                print(f"[StegoDetector] Data length ({data_length}) exceeds maximum allowed size.")
                return False, "No steganography detected: Data length exceeds maximum."

            if len(full_data) < 8:  # At least need length (4) + magic marker (4)
                print("[StegoDetector] Not enough data to check magic marker.")
                return False, "No steganography detected: Insufficient data."

            # Check for magic marker
            print("[StegoDetector] Checking for magic marker...")
            hidden_data = full_data[4:]
            # Use the hardcoded MAGIC_MARKER value
            MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
            if hidden_data.startswith(MAGIC_MARKER):
                print(f"[StegoDetector] Magic marker {MAGIC_MARKER.hex()} found!")
                return True, "Steganography detected in the image!"
            else:
                print(f"[StegoDetector] Magic marker not found at start of hidden data.")
                # It might still be steganography but not from our application
                return True, "Possible steganography detected, but not from this application."

        except Exception as e:
            print(f"[StegoDetector] Error during detection: {str(e)}")
            return False, f"Detection error: {str(e)}"

    def _load_carrier_gif_thread(self, new_path):
        """Thread to load a carrier GIF."""
        try:
            # Verify the GIF is valid
            if not self.validate_gif(new_path):
                # Reset function is called inside validate_gif if it fails
                return
                
            # Update the carrier path and start loading
            self.carrier_gif_path = new_path
            self._load_carrier_gif()
            
        except Exception as e:
            logging.error(f"Failed to load carrier GIF")
            self.root.after(0, lambda: messagebox.showerror("Carrier Fail", f"Failed to Load GIF"))
            # Reset all fields regardless of whether there was a previous GIF
            self.root.after(0, self.reset_gif_fields)
        finally:
            self.root.after(0, lambda: self.load_gif_button.configure(state="normal"))

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
                
                # Check if this is a steganography GIF (without showing UI notifications)
                is_stego, _ = self.detect_gif_steganography(self.carrier_gif_path)
                if is_stego:
                    print("[STEGO DETECTION] This is a stego GIF.")
                else:
                    print("[STEGO DETECTION] This is not a stego GIF.")
                
                # Enable buttons when GIF is loaded successfully
                self.root.after(0, lambda: self.gif_embed_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_extract_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_metadata_button.configure(state="normal"))
                self.root.after(0, lambda: self.gif_generate_key_button.configure(state="normal"))
                
                # Enable input fields with updated placeholders
                self.root.after(0, lambda: self.gif_key_entry.configure(
                    state="normal", 
                    placeholder_text="Enter or generate a key" , 
                    show="*"
                ))
                self.root.after(0, lambda: self.gif_password_entry.configure(
                    state="normal", 
                    placeholder_text="Enter password (optional)" , 
                    show="*"
                ))
                self.root.after(0, lambda: self.gif_author_entry.configure(
                    state="normal", 
                    placeholder_text="Enter author name (optional)"
                ))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Carrier Fail", f"Failed to Load GIF"))
                self.root.after(0, lambda: self.carrier_gif_status.configure(
                    text=f"Failed to Load GIF", 
                    text_color="red"
                ))
                
                # Reset all fields to initial state instead of just disabling buttons
                self.root.after(0, self.reset_gif_fields)
                
            finally:
                self.root.after(0, lambda: self.load_gif_button.configure(state="normal"))

    def drop_carrier_gif(self, event):
        """Handle dropped files for carrier GIF."""
        if self.operation_in_progress or self.gif_load_lock.locked():
            messagebox.showwarning("Warning", "Please wait for the current operation to finish.")
            return

        files = self.root.splitlist(event.data)
        if len(files) > 1:
            messagebox.showerror("Carrier Fail", "Please Drop Only One GIF File.")
            return

        file_path = files[0]
        if not file_path.lower().endswith('.gif'):
            messagebox.showerror("Carrier Fail", "Please Drop a GIF File.")
            return
        
        # Validate the GIF before setting the carrier path
        if not self.validate_gif(file_path):
            # Do not show another error message here; validate_gif already shows "Not a Valid GIF File (Invalid Header)"
            self.carrier_gif_path = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            self.root.after(0, self.reset_gif_fields)  # Reset fields to initial state
            return

        # If validation passes, set the carrier path and proceed with loading
        self.carrier_gif_path = file_path
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
            # Do not show another error message here; validate_gif already shows "Not a Valid GIF File (Invalid Header)"
            self.carrier_gif_path = None
            self.carrier_gif_status.configure(text="No GIF selected", text_color="red")
            return

        self.carrier_gif_status.configure(text="Loading...", text_color="yellow")
        self.load_gif_button.configure(state="disabled")
        threading.Thread(target=self._load_carrier_gif, daemon=True).start()

    def drop_gif_data_file(self, event):
        """Handle dropped files for data to hide in GIF-Stego."""
        MAX_FILES = 20
        MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file for GIFs
        MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB total

        files = self.root.splitlist(event.data)
        if len(files) > MAX_FILES:
            messagebox.showerror("Data Fail", f"You Can Only Select Up to {MAX_FILES} Files at a Time.")
            return

        # Check file sizes
        total_size = 0
        oversized_files = []
        for path in files:
            file_size = os.path.getsize(path)
            if file_size > MAX_FILE_SIZE:
                oversized_files.append(f"'{os.path.basename(path)}' ({file_size / (1024*1024):.1f} MB)")
            total_size += file_size
            if total_size > MAX_TOTAL_SIZE:
                messagebox.showerror("Data Fail", 
                    f"Total size of Dropped Files ({total_size / (1024*1024):.1f} MB) "
                    f"Exceeds the Maximum Limit of {MAX_TOTAL_SIZE / (1024*1024):.1f} MB")
                return

        if oversized_files:
            messagebox.showerror("Data Fail",
                f"The Following Files Exceed the {MAX_FILE_SIZE / (1024*1024):.1f} MB Per-File Limit:\n\n" +
                "\n".join(oversized_files))
            return

        self.gif_data_file_path = files
        self.gif_data_file_status.configure(
            text=f"{len(self.gif_data_file_path)} Files Selected (Total: {total_size / (1024*1024):.1f} MB)" 
            if self.gif_data_file_path else "No Files Selected",
            text_color="green" if self.gif_data_file_path else "red"
        )

    def load_gif_data_file(self, file_paths=None):
        """Load data files to embed for GIF stego."""
        MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file for GIFs
        MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB total
        MAX_FILES = 20

        if not file_paths:
            self.gif_data_file_path = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])
        else:
            self.gif_data_file_path = file_paths

        if len(self.gif_data_file_path) > MAX_FILES:
            messagebox.showerror("Data Fail", f"You Can Only Select Up to {MAX_FILES} Files at a Time.")
            self.gif_data_file_path = []
            self.gif_data_file_status.configure(text="No Files Selected", text_color="red")
            return

        # Check file sizes
        total_size = 0
        oversized_files = []
        for path in self.gif_data_file_path:
            file_size = os.path.getsize(path)
            if file_size > MAX_FILE_SIZE:
                oversized_files.append(f"'{os.path.basename(path)}' ({file_size / (1024*1024):.1f} MB)")
            total_size += file_size
            if total_size > MAX_TOTAL_SIZE:
                messagebox.showerror("Data Fail", 
                    f"Total size of Selected Files ({total_size / (1024*1024):.1f} MB) "
                    f"Exceeds the Maximum Limit of {MAX_TOTAL_SIZE / (1024*1024):.1f} MB")
                self.gif_data_file_path = []
                self.gif_data_file_status.configure(text="No Files Selected", text_color="red")
                return

        if oversized_files:
            messagebox.showerror("Data Fail",
                f"The Following Files Exceed the {MAX_FILE_SIZE / (1024*1024):.1f} MB Per-File Limit:\n\n" +
                "\n".join(oversized_files))
            self.gif_data_file_path = []
            self.gif_data_file_status.configure(text="No Files Selected", text_color="red")
            return

        self.gif_data_file_status.configure(
            text=f"{len(self.gif_data_file_path)} Files Selected (Total: {total_size / (1024*1024):.1f} MB)" 
            if self.gif_data_file_path else "No Files Selected",
            text_color="green" if self.gif_data_file_path else "red"
        )

    def start_gif_embed(self):
        """Start the GIF embedding process."""
        if self.operation_in_progress:
            return

        # Check for carrier GIF first
        if not self.carrier_gif_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier GIF.")
            return

        # Check for data files
        if not self.gif_data_file_path:
            messagebox.showerror("Data Fail", "Please Select Files to Hide.")
            return

        # Check for encryption key
        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Embeding Error", "Please Generate or Enter an Encryption Key.")
            return

        # Check for password
        gif_password = self.gif_password_entry.get().strip()
        if not gif_password:
            messagebox.showerror("Embeding Error", "Please Enter a Password.")
            return

        # If all checks pass, proceed with validation and embedding
        valid, gif_password, author = self.validate_inputs(self.gif_password_entry, self.gif_author_entry)
        if not valid:
            return
        threading.Thread(target=lambda: self._gif_embed_data_thread(gif_password, author), daemon=True).start()

    def _gif_embed_data_thread(self, password, author):
        """Embed data into the carrier GIF in a separate thread."""
        self.set_button_state(self.gif_embed_button, "disabled", operation=True)
        try:
            # Validate carrier and data file paths
            if not self.carrier_gif_path or not self.gif_data_file_path:
                messagebox.showerror("Carrier Fail", "Missing carrier GIF or data files.")
                self.root.after(0, lambda: self.update_gif_progress(0))
                self.set_button_state(self.gif_embed_button, "normal", operation=True)
                return

            # Verify carrier GIF hash
            with open(self.carrier_gif_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if self.carrier_gif_hash != current_hash:
                messagebox.showerror("Carrier Fail", "Carrier GIF has been Modified Since Loading!")
                self.root.after(0, lambda: self.update_gif_progress(0))
                self.set_button_state(self.gif_embed_button, "normal", operation=True)
                return

            # Get encryption key
            key_str = self.gif_key_entry.get().strip()
            if not key_str:
                messagebox.showerror("Embeding Error", "Please Provide a Valid Encryption Key.")
                self.root.after(0, lambda: self.update_gif_progress(0))
                self.set_button_state(self.gif_embed_button, "normal", operation=True)
                return
            # Initialize cipher with the key
            if not self.gif_logic.get_cipher(key_str, self.root):
                self.root.after(0, lambda: self.update_gif_progress(0))
                self.set_button_state(self.gif_embed_button, "normal", operation=True)
                return

            # Update operation type and estimates
            self.current_operation = "embed"
            self.estimates_visible = True


            # Embed the data
            output_data = self.gif_logic.embed_data(
                self.carrier_gif_path,
                self.gif_data_file_path,
                key_str,
                password,
                author,
                lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
            )

            # Prompt user to save the embedded GIF - pass output_data as a parameter to avoid scope issues
            def save_stego_gif(embedded_data):
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".gif",
                    filetypes=[("GIF files", "*.gif")],
                    initialfile=""  # Empty initial filename
                )
                
                if save_path:
                    # Save the embedded GIF
                    with open(save_path, "wb") as output_file:
                        output_file.write(embedded_data)
                    self.update_gif_progress(100)
                    messagebox.showinfo("Embeding Success", f"{len(self.gif_data_file_path)} files embedded successfully!")
                    self.history_manager.add_entry(
                        "Embed",
                        f"Embedded {len(self.gif_data_file_path)} files into {save_path} (GIF-Stego)"
                    )
                    self.update_history_view()
                    self.root.after(100, self.reset_gif_fields)
                else:
                    # User canceled saving
                    messagebox.showinfo("Embeding Canceled", "Embedding operation cancelled by user.")
                    # Reset progress bar only
                    self.root.after(0, lambda: self.update_gif_progress(0))
                    # Force garbage collection to free memory
                    import gc
                    gc.collect()
            
            # Schedule save dialog on the main thread with the output_data as an argument
            self.root.after(0, lambda: save_stego_gif(output_data))

        except Exception as e:
            logging.error(f"Embedding failed: {str(e)}")
            messagebox.showerror("Embeding Error", {str(e)})
            self.update_gif_progress(0)
            self.root.after(0, self.reset_gif_fields)
        finally:
            self.set_button_state(self.gif_embed_button, "normal", operation=True)

    def start_gif_extract(self):
        """Start the GIF extraction process."""
        if self.operation_in_progress:
            return

        # Check for carrier GIF first
        if not self.carrier_gif_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier GIF.")
            return

        # Check for encryption key
        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Extraction Error", "Please Generate or Enter an Encryption Key.")
            return

        # Check for password
        password = self.gif_password_entry.get().strip()
        if not password:
            messagebox.showerror("Extraction Error", "Please Enter the Password Used During Embedding.")
            return

        # If all checks pass, proceed with validation and extraction
        valid, password, author = self.validate_inputs(self.gif_password_entry, self.gif_author_entry, for_embedding=False)
        if not valid:
            return
        threading.Thread(target=lambda: self._gif_extract_data_thread(password), daemon=True).start()

    def _gif_extract_data_thread(self, password):
        self.set_button_state(self.gif_extract_button, "disabled", operation=True)
        if not self.carrier_gif_path:
            messagebox.showerror("Carrier Fail", "Select a carrier GIF.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        with open(self.carrier_gif_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        if self.carrier_gif_hash != current_hash:
            messagebox.showerror("Carrier Fail", "Carrier GIF has been modified since loading!")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        key_str = self.gif_key_entry.get().strip()
        if not key_str:
            messagebox.showerror("Extraction Error", "Please Provide a Valid Encryption Key.")
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        if not self.gif_logic.get_cipher(key_str, self.root):
            self.root.after(0, lambda: self.update_gif_progress(0))  # Reset progress on error
            self.set_button_state(self.gif_extract_button, "normal", operation=True)
            return

        self.current_operation = "extract"
        self.estimates_visible = True


        try:
            files_data, author, timestamp = self.gif_logic.extract_data(
                self.carrier_gif_path, key_str, password,
                lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
            )

            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if not output_folder:
                self.root.after(0, lambda: messagebox.showinfo("Extraction Canceled", "Extraction cancelled by user."))
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
                "Extraction Success",
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
            logging.error(f"Extraction failed: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Extraction Error", {str(e)} ))
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
        """View metadata from a stego GIF in a separate thread."""
        self.set_button_state(self.gif_metadata_button, "disabled", operation=True)
        
        if not self.carrier_gif_path:
            messagebox.showerror("Carrier Fail", "Please Select a Carrier GIF.")
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)
            return
        
        try:
            self.update_gif_progress(10)
            
            # First check if this is a steganography GIF
            is_stego, message = self.detect_gif_steganography(self.carrier_gif_path)
            if not is_stego:
                messagebox.showinfo("Information", "This is not a stego GIF.")
                self.update_gif_progress(0)
                self.set_button_state(self.gif_metadata_button, "normal", operation=True)
                return
            else:
                print("[STEGO DETECTION] This is a stego GIF.")
                
            # Get encryption key
            key_str = self.gif_key_entry.get().strip()
            if not key_str:
                messagebox.showerror("Extraction Error", "Please Provide an Encryption Key.")
                self.update_gif_progress(0)
                self.set_button_state(self.gif_metadata_button, "normal", operation=True)
                return
                
            # Get password if provided
            gif_password = self.gif_password_entry.get().strip()
            if not gif_password:
                messagebox.showerror("Extraction Error", "Please Provide a Password.")
                self.update_gif_progress(0)
                self.set_button_state(self.gif_metadata_button, "normal", operation=True)
                return
            
            self.update_gif_progress(20)
            
            # Initialize cipher with the key
            if not self.gif_logic.get_cipher(key_str, self.root):
                self.update_gif_progress(0)
                self.set_button_state(self.gif_metadata_button, "normal", operation=True)
                return
                
            self.update_gif_progress(30)
            
            # Try to extract metadata
            try:
                # Use gif_logic to extract metadata
                author, timestamp, file_count = self.gif_logic.view_metadata(
                    self.carrier_gif_path,
                    key_str,
                    gif_password,
                    lambda value: self.root.after(0, lambda v=value: self.update_gif_progress(v))
                )
                
                self.update_gif_progress(100)
                
                # Display the metadata
                messagebox.showinfo(
                    "Metadata Information",
                    f"Metadata Successfully Extracted!\n\n"
                    f"File Contains {file_count} Embedded Files\n"
                    f"Author: {author}\n"
                    f"Timestamp: {timestamp}"
                )
                
                self.history_manager.add_entry(
                    "View Metadata",
                    f"Viewed metadata from {self.carrier_gif_path} (GIF-Stego)"
                )
                self.update_history_view()
                
            except ValueError as extract_error:
                error_str = str(extract_error).lower()
                
                # Check for specific errors
                if "incorrect encryption key" in error_str or "key mismatch" in error_str:
                    messagebox.showerror("Extraction Error", "The Password or The Encryption Key is Incorrect.")
                elif "incorrect password" in error_str or "password mismatch" in error_str:
                    messagebox.showerror("Extraction Error", "The Password or The Encryption Key is Incorrect.")
                else:
                    messagebox.showerror("Extraction Error", f"Error reading GIF Metadata")
            
        except Exception as e:
            logging.error(f"Extraction Error : {str(e)}")
            messagebox.showerror("Extraction Error",{str(e)} )
            
        finally:
            self.update_gif_progress(0)
            self.set_button_state(self.gif_metadata_button, "normal", operation=True)

    def detect_gif_steganography(self, gif_path):
        """Detect if a GIF contains hidden data using our GIF steganography technique."""
        try:
            print(f"[StegoDetector] Checking GIF: {gif_path}")
            
            # Check if the file exists
            if not os.path.exists(gif_path):
                print(f"[StegoDetector] GIF file does not exist: {gif_path}")
                return False, "GIF file does not exist"
                
            # Try to read the GIF file
            try:
                print(f"[StegoDetector] Reading GIF file: {gif_path}")
                with open(gif_path, "rb") as f:
                    gif_data = f.read()
                print(f"[StegoDetector] GIF data loaded, size: {len(gif_data)} bytes")
            except Exception as e:
                print(f"[StegoDetector] Failed to read GIF file: {str(e)}")
                return False, f"Failed to read GIF file: {str(e)}"
                
            # Check for valid GIF header
            if not gif_data.startswith(b'GIF8'):
                print("[StegoDetector] Not a valid GIF file (invalid header)")
                return False, "Not a valid GIF file"
                
            # Find the GIF trailer byte (0x3B)
            trailer_pos = gif_data.rfind(b'\x3B')
            if trailer_pos == -1:
                print("[StegoDetector] Invalid GIF: No trailer byte found")
                return False, "Invalid GIF: No trailer byte found"
                
            # Check if there's data after the GIF trailer
            if trailer_pos + 1 >= len(gif_data):
                print("[StegoDetector] No data after GIF trailer - this is a normal GIF")
                return False, "No steganography detected: No data after GIF trailer"
                
            # Check the data after trailer
            remaining_data = gif_data[trailer_pos + 1:]
            print(f"[StegoDetector] Found {len(remaining_data)} bytes of data after GIF trailer")
            
            # Need at least 4 bytes for length + 4 for magic marker
            if len(remaining_data) < 8:
                print("[StegoDetector] Insufficient data after GIF trailer")
                return False, "No steganography detected: Insufficient data after GIF trailer"
                
            # Extract length prefix
            try:
                data_length = struct.unpack(">I", remaining_data[:4])[0]
                print(f"[StegoDetector] Data length from prefix: {data_length} bytes")
                
                # Check if length is reasonable
                if data_length <= 0 or data_length > 1024 * 1024 * 100:  # 100MB max
                    print(f"[StegoDetector] Invalid data length: {data_length}")
                    return False, f"No steganography detected: Invalid data length ({data_length})"
                    
                # Check if there's enough data as specified by length
                if 4 + data_length > len(remaining_data):
                    print("[StegoDetector] Incomplete data after GIF trailer")
                    return False, "No steganography detected: Incomplete data after GIF trailer"
                    
                # Check for the magic marker - directly using the byte sequence
                MAGIC_MARKER = b'\xDE\xAD\xBE\xEF'
                if remaining_data[4:8] == MAGIC_MARKER:
                    print(f"[StegoDetector] Magic marker {MAGIC_MARKER.hex()} found!")
                    return True, "Steganography detected in the GIF!"
                else:
                    print("[StegoDetector] Magic marker not found after length prefix")
                    # Might still be steganography but not from our app
                    return True, "Possible steganography detected, but not from this application."
                    
            except Exception as e:
                print(f"[StegoDetector] Error analyzing data after trailer: {str(e)}")
                return False, f"Detection error: {str(e)}"
                
        except Exception as e:
            print(f"[StegoDetector] Error during detection: {str(e)}")
            return False, f"Detection error: {str(e)}"

    def validate_gif(self, gif_path):
        """Validate if a file is a valid GIF."""
        try:
            # Check if the file exists
            if not os.path.exists(gif_path):
                self.root.after(0, lambda: messagebox.showerror("Carrier fail", "GIF file does not exist."))
                self.root.after(0, self.reset_gif_fields)  # Reset all fields if invalid
                return False
                
            # Check file extension
            if not gif_path.lower().endswith('.gif'):
                self.root.after(0, lambda: messagebox.showerror("Carrier Fail", "Not a GIF file. Please Select a File with .gif Extension."))
                self.root.after(0, self.reset_gif_fields)  # Reset all fields if invalid
                return False
                
            # Try to open with PIL
            try:
                Image.open(gif_path).verify()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Carrier Fail", f"Invalid GIF Format"))
                self.root.after(0, self.reset_gif_fields)  # Reset all fields if invalid
                return False
                
            # Check if the file starts with the GIF signature
            with open(gif_path, 'rb') as f:
                header = f.read(6)
                if not header.startswith(b'GIF8'):
                    self.root.after(0, lambda: messagebox.showerror("Carrier Fail", "Not a Valid GIF File (Invalid Header)."))
                    self.root.after(0, self.reset_gif_fields)  # Reset all fields if invalid
                    return False
                    
            return True
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Carrier Fail", "Failed to Validate GIF"))
            self.root.after(0, self.reset_gif_fields)  # Reset all fields if invalid
            return False
    
    def validate_inputs(self, password_entry, author_entry, for_embedding=True):
        """Validate user inputs for password and author."""
        try:
            password = password_entry.get().strip()
            author = author_entry.get().strip()
            
            # For extraction, we just return the values
            if not for_embedding:
                return True, password, author
                
            # Additional validation for embedding
            if not author:
                author = "Anonymous"  # Default author name if none provided
                
            return True, password, author
        except Exception as e:
            logging.error(f"Input validation error: {str(e)}")
            messagebox.showerror("Validation Error ", {str(e)} )
            return False, None, None

    def update_history_view(self):
        """Update the history view with the latest entries."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in self.history_manager.get_history():
            self.history_tree.insert("", "end", values=(
                entry["timestamp"], entry["operation"], entry["details"]
            ))

    def update_progress(self, value):
        """Update the progress bar value and label."""
        self.progress.set(value / 100)  # CustomTkinter progress bars use 0-1 range
        self.progress_label.configure(text=f"Progress: {value}%")
        # Force update to ensure progress is displayed immediately
        self.root.update_idletasks()

    def update_gif_progress(self, value):
        """Update the GIF progress bar value and label."""
        self.gif_progress.set(value / 100)
        self.gif_progress_label.configure(text=f"Progress: {value}%")
        # Force update to ensure progress is displayed immediately
        self.root.update_idletasks()

    def reset_fields(self):
        """Reset all fields to their initial state for image stego."""
        # Reset operation flag first
        self.operation_in_progress = False
        
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
        self.carrier_image_status.configure(text="No Image Selected", text_color="red")
        self.data_file_status.configure(text="No Files Selected", text_color="red")
        
        # Hide the entropy label if it exists
        if hasattr(self, 'entropy_label'):
            self.entropy_label.pack_forget()
        
        # Reset estimates
        self.estimates_visible = False
        if hasattr(self, 'estimates_label'):
            self.estimates_label.pack_forget()
        
        # Clear and disable all input fields with proper initial state
        self.key_entry.delete(0, "end")
        self.key_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70" , 
            show="*"
        )
        
        self.password_entry.delete(0, "end")
        self.password_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            show="*"  # Ensure password masking is set
        )
        
        self.author_entry.delete(0, "end")
        self.author_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70"
        )
        
        self.root.focus_set()

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
        # Reset operation flag first
        self.operation_in_progress = False
        
        # Reset data paths and states
        self.carrier_gif_path = None
        self.gif_data_file_path = None
        self.carrier_gif_hash = None
        
        # Reset progress bar
        self.gif_progress.set(0)
        self.gif_progress_label.configure(text="Progress: 0%")
        self.root.update_idletasks()
        
        # Reset status labels to initial state
        self.carrier_gif_status.configure(text="No GIF Selected", text_color="red")
        self.gif_data_file_status.configure(text="No Files Selected", text_color="red")
        
        # Reset estimates
        self.estimates_visible = False
        if hasattr(self, 'gif_estimates_label'):
            self.gif_estimates_label.pack_forget()
        
        # Clear and disable all input fields with proper initial state
        self.gif_key_entry.delete(0, "end")
        self.gif_key_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70" , 
            show="*"
        )
        
        self.gif_password_entry.delete(0, "end")
        self.gif_password_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70",
            show="*"  # Ensure password masking is set
        )
        
        self.gif_author_entry.delete(0, "end")
        self.gif_author_entry.configure(
            state="disabled",
            placeholder_text="",
            fg_color="#2b2b2b",
            bg_color="#2b2b2b",
            text_color="gray70"
        )

        self.root.focus_set()

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
        """Set button state and update operation in progress flag."""
        button.configure(state=state)
        if operation:
            self.operation_in_progress = (state == "disabled")
        self.root.update_idletasks()  # Force UI update
    
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
