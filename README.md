
  
  HideNSeek
  
    A Modern Steganography Application to Hide and Reveal Data in Images and GIFs 🔒
  

  
    Explore the docs »
    
    
    View Demo
    ·
    Report Bug
    ·
    Request Feature
  

  
    
    
    
    
    
  



Table of Contents

About the Project
Built With


Getting Started
Prerequisites
Installation


Usage
Screenshots
Technical Details
Roadmap
Contributing
License
Contact
Acknowledgments


About the Project
HideNSeek is a Python-based steganography application that allows users to hide and extract data within images (PNG, JPG, JPEG) and GIFs. Featuring a modern, dark-themed GUI built with CustomTkinter, HideNSeek combines security, usability, and style. Whether you're concealing sensitive files or exploring steganography, HideNSeek offers a seamless experience with encryption, drag-and-drop support, and detailed operation history.
Key Features:

🖼️ Image Steganography: Embed and extract data in PNG, JPG, or JPEG files using LSB techniques.
🎞️ GIF Steganography: Hide data in GIFs with frame-based encoding.
🔐 Fernet Encryption: Secure your data with symmetric encryption.
🛡️ Authentication: Add passwords and author metadata.
📂 Drag-and-Drop: Easily load files via drag-and-drop.
📜 Operation History: Track all actions in a dedicated tab.
⏳ Progress Tracking: Animated progress bars with time estimates.
🌐 Cross-Platform: Works on Windows, macOS, and Linux.

HideNSeek is perfect for users who want to securely share data in plain sight, wrapped in a sleek and intuitive interface.
Built With

Python
CustomTkinter
Pillow
Cryptography
TkinterDnD2


Getting Started
Follow these steps to set up HideNSeek on your local machine.
Prerequisites

Python 3.8 or higher: Ensure Python is installed. Download from python.org.
pip: Python’s package manager (usually included with Python).

Installation

Clone the Repository:
git clone https://github.com/your-username/hidenseek.git
cd hidenseek


Install Dependencies:
pip install -r requirements.txt

This installs:

customtkinter: For the GUI.
pillow: For image and GIF processing.
numpy: For array operations in steganography.
cryptography: For Fernet encryption.
tkinterdnd2: For drag-and-drop functionality.


Run the Application:
python main.py

The app will launch in a 900x700px window with a dark-themed interface.



Usage
HideNSeek is designed for ease of use, with a tabbed interface to handle different tasks. Here’s how to use it:
1. Launch the App
Run main.py to open the GUI. The sidebar includes four tabs: Image-Stego, GIF-Stego, History, and Help.
2. Embed Data

Select a Carrier:
In the Image-Stego or GIF-Stego tab, click Browse Image/GIF or drag-and-drop a carrier file (PNG/JPG/JPEG for Image-Stego, GIF for GIF-Stego).


Choose Data to Hide:
Click Browse Files or drag-and-drop up to 20 files to embed.


Set Encryption Key:
Enter a key or click Generate to create one (automatically copied to clipboard).


Add Authentication (Optional):
Enter a password and author name.


Embed:
Click Embed Data and save the output file (PNG or GIF).
Monitor the progress bar and estimated time.



3. Extract Data

Load Stego File:
Select the stego image/GIF via Browse Image/GIF or drag-and-drop.


Enter Key and Password:
Provide the encryption key and password (if used) from the embedding step.


Extract:
Click Extract Data and choose an output folder.
Extracted files are saved in a subfolder named Extracted_[carrier-name]_[timestamp].



4. View Metadata

Load Stego File:
Select the stego image/GIF.


Enter Key and Password:
Provide the encryption key and password.


View Metadata:
Click View Metadata to see the embedded author and timestamp.



5. Check History

Go to the History tab to view a log of all operations, including timestamps, operation type, and details.

For more detailed instructions, click the Help tab in the app.

Screenshots



Image-Stego Tab
GIF-Stego Tab
History Tab








Embed and extract data in images.
Hide files in GIFs with ease.
Track your operation history.



  
  Watch HideNSeek in action—embedding and extracting data seamlessly!



Technical Details
Steganography Techniques

Image Steganography:
Uses Least Significant Bit (LSB) encoding to hide data in pixel values.
Minimizes visual distortion by altering only the least significant bits.


GIF Steganography:
Embeds data across GIF frames, leveraging frame-based encoding.
Preserves GIF animation functionality.



Security Features

Encryption:
Uses Fernet (symmetric encryption) from the cryptography library.
Requires a key for both embedding and extraction.


Authentication:
Optional password protection and author metadata.


Integrity Checks:
Computes SHA-256 hashes to detect tampering.



Performance

Threading: Handles long tasks (embedding/extraction) in separate threads to keep the GUI responsive.
Progress Tracking: Displays real-time progress with animated bars and time estimates.
Memory Management: Implements cleanup methods and garbage collection to free resources.

UI Design

Built with CustomTkinter.
Dark theme with green buttons (#4CAF50, hover: #388E3C).
Fixed window size (900x700px), non-resizable.
Sidebar navigation with tabbed content.

Project Structure

main.py: Core app with GUI and logic.
img.py: SteganographyLogic for image steganography.
gif.py: GIFSteganographyLogic for GIF steganography.
history.json: Stores operation history.
assets/: Contains screenshots and demo GIFs.
requirements.txt: Lists dependencies.


Roadmap

 Support for additional file formats (e.g., BMP, MP4).
 Batch processing for embedding multiple carriers.
 Advanced encryption options (e.g., AES-256).
 UI themes and customization.
 Integration with cloud storage for saving stego files.

See the open issues for a full list of proposed features and known bugs.

Contributing
Contributions are welcome! To contribute:

Fork the Project 🍴.
Create your Feature Branch (git checkout -b feature/AmazingFeature).
Commit your Changes (git commit -m 'Add some AmazingFeature').
Push to the Branch (git push origin feature/AmazingFeature).
Open a Pull Request 🚀.

Please ensure your code is well-documented and follows the project’s style.

License
Distributed under the MIT License. See LICENSE for more information.

Contact
Your Name - your-email@example.com
Project Link: https://github.com/your-username/hidenseek

Acknowledgments

CustomTkinter
Pillow
Cryptography
TkinterDnD2
Inspired by Best-README-Template



  HideNSeek: Securely hide your data with style! ⭐ Give us a star on GitHub to support the project! ⭐
