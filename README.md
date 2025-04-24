HideNSeek - Steganography Application
Table of Contents

Project Overview
Key Objectives


Project Structure
Why Projects Like This Should Be Implemented
Stages and Technologies Used
Stage 1: Core Development
Stage 2: Steganography Logic
Stage 3: Security Implementation
Stage 4: GUI Development
Stage 5: Testing
Stage 6: Deployment


Installation and Prerequisites
Prerequisites


References


Project Overview
HideNSeek is a Python-based steganography application designed to securely hide and extract data within images (PNG, JPG, JPEG) and GIFs. It features a modern, dark-themed GUI built with CustomTkinter, offering an intuitive user experience for embedding, extracting, and viewing metadata. The application integrates Fernet encryption for security, drag-and-drop functionality for ease of use, and operation history tracking, making it a powerful tool for concealing sensitive data in plain sight.
Key Objectives:

Develop a user-friendly steganography tool for images and GIFs.
Implement secure data embedding with encryption and authentication.
Provide a modern GUI with drag-and-drop support and progress tracking.
Ensure cross-platform compatibility (Windows, macOS, Linux).
Document the project for easy setup and usage.


Project Structure
HideNSeek/
│
├── assets/                           # Directory for README images and demo GIFs
│   └── image-stego.png               # Screenshot of the Image-Stego tab
│   └── gif-stego.png                 # Screenshot of the GIF-Stego tab
│   └── history-tab.png               # Screenshot of the History tab
│   └── demo.gif                      # Demo GIF showing app functionality
│
├── src/                              # Source code directory
│   └── main.py                       # Main script with GUI and core logic
│   └── img.py                        # Logic for image steganography (SteganographyLogic)
│   └── gif.py                        # Logic for GIF steganography (GIFSteganographyLogic)
│
├── history.json                      # File to store operation history
│
├── requirements.txt                  # List of Python dependencies
│
├── README.md                         # Project documentation (this file)
│
└── LICENSE                           # MIT License file


Why Projects Like This Should Be Implemented

Enhanced Security: Steganography provides an additional layer of security by hiding data within media files, making it ideal for secure communication.
User Accessibility: A GUI-based tool makes steganography accessible to non-technical users, broadening its practical applications.
Educational Value: Projects like HideNSeek offer hands-on experience with encryption, image processing, and GUI development, fostering learning in cybersecurity and software engineering.
Cross-Platform Utility: Supporting multiple platforms ensures wider usability, catering to diverse user needs.


Stages and Technologies Used
Stage 1: Core Development

Tool/Technology: Python
Description: Developed the foundational structure of the application, including file handling and basic logic for data embedding and extraction.

Stage 2: Steganography Logic

Tool/Technology: Pillow, NumPy
Description: Implemented steganography logic for images (LSB technique) and GIFs (frame-based encoding) using Pillow for image processing and NumPy for efficient array operations.


Stage 3: Security Implementation

Tool/Technology: Cryptography
Description: Integrated Fernet encryption for securing data before embedding, along with SHA-256 hashing for integrity checks and optional password authentication.

Stage 4: GUI Development

Tool/Technology: CustomTkinter, TkinterDnD2
Description: Designed a modern, dark-themed GUI with CustomTkinter, featuring tabs for Image-Stego, GIF-Stego, History, and Help, and added drag-and-drop support using TkinterDnD2.



Stage 5: Testing

Tool/Technology: Manual Testing
Description: Conducted tests to ensure embedding, extraction, and metadata viewing worked correctly across different file formats and platforms, verifying integrity checks and encryption.

Stage 6: Deployment

Tool/Technology: PyInstaller (Optional)
Description: Packaged the application for distribution using PyInstaller, creating executables for Windows, macOS, and Linux to simplify deployment for end users.



Installation and Prerequisites
Prerequisites

Python 3.8+: Download from python.org.
pip: Ensure it’s installed (comes with Python).
tkdnd (for TkinterDnD2):
Windows/macOS: Download from SourceForge, extract, and place in your project directory.
Linux: Install via package manager:sudo apt-get install tkdnd





Installation Steps

Clone the Repository:
git clone https://github.com/your-username/hidenseek.git
cd hidenseek


Install Dependencies:

Use the provided requirements.txt:pip install -r requirements.txt


This installs:
customtkinter==5.2.2
Pillow==10.3.0
numpy==1.26.4
cryptography==42.0.5
pyperclip==1.8.2
tkinterdnd2==0.3.0




Run the Application:
python src/main.py




References

CustomTkinter Documentation: GitHub Repository
Pillow Documentation: Official Site
Cryptography Library: Official Documentation
TkinterDnD2 Guide: GitHub Repository
PyInstaller Setup: Official Documentation

