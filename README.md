HideNSeek - Steganography Application
HideNSeek is a Python-based GUI application for performing steganography operations on images and GIFs. It allows users to embed data into carrier files (PNG, JPG, JPEG, or GIF), extract hidden data, and view metadata, with support for encryption and authentication.
Features

Image Steganography: Embed and extract data in PNG, JPG, or JPEG images using least significant bit (LSB) techniques.
GIF Steganography: Embed and extract data in GIF files with frame-based steganography.
Encryption: Secure data with Fernet encryption using user-provided or generated keys.
Authentication: Optional password protection and author metadata for embedded data.
Drag-and-Drop Support: Easily load carrier files and data files via drag-and-drop.
Operation History: Track embedding, extraction, and metadata viewing operations.
Progress Tracking: Visual progress bars and estimated time for operations.
Cross-Platform: Runs on Windows, macOS, and Linux with a modern GUI using CustomTkinter.

Prerequisites

Python 3.8 or higher
Required Python packages (install via pip):pip install customtkinter pillow numpy cryptography tkinterdnd2



Installation

Clone the repository:
git clone https://github.com/your-username/hidenseek.git
cd hidenseek


Install dependencies:
pip install -r requirements.txt


Run the application:
python main.py



Usage

Launch the Application:

Run main.py to open the GUI.


Select a Tab:

Image-Stego: For PNG, JPG, or JPEG steganography.
GIF-Stego: For GIF steganography.
History: View past operations.
Help: Access usage instructions.


Embedding Data:

Load a carrier image/GIF using "Browse" or drag-and-drop (PNG/JPG/JPEG for Image-Stego, GIF for GIF-Stego).
Select up to 20 files to hide using "Browse Files" or drag-and-drop.
Enter or generate an encryption key.
(Optional) Add a password and author name.
Click "Embed Data" and save the output file.


Extracting Data:

Load a stego image/GIF.
Enter the encryption key and (if used) password.
Click "Extract Data" and choose an output folder.


Viewing Metadata:

Load a stego image/GIF.
Enter the encryption key and (if used) password.
Click "View Metadata" to see author and timestamp details.



Project Structure

main.py: Main application script with GUI and core logic.
img.py: Contains SteganographyLogic class for image steganography.
gif.py: Contains GIFSteganographyLogic class for GIF steganography.
history.json: Stores operation history (auto-generated).
requirements.txt: Lists dependencies.

Notes

Security: Ensure the encryption key and password are securely stored, as they are required for extraction.
File Size: The carrier file must have sufficient capacity to hold the data (estimated times are provided).
Integrity Checks: The application verifies file integrity using SHA-256 hashes to prevent tampering.
Limitations: Maximum of 20 files can be embedded at once.

Contributing
Contributions are welcome! Please:

Fork the repository.
Create a feature branch (git checkout -b feature-name).
Commit changes (git commit -m 'Add feature').
Push to the branch (git push origin feature-name).
Open a pull request.

License
This project is licensed under the MIT License. See the LICENSE file for details.
Acknowledgments

Built with CustomTkinter for the GUI.
Uses Pillow for image processing.
Encryption powered by Cryptography.

