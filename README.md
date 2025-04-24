🌟 HideNSeek - Steganography Application 🌟
Hide your secrets in plain sight with style!
HideNSeek is a sleek, modern Python-based GUI application that brings steganography to life. Embed and extract data in images (PNG, JPG, JPEG) or GIFs with ease, all while enjoying a vibrant, user-friendly interface powered by CustomTkinter. With encryption, drag-and-drop support, and a colorful design, HideNSeek makes data hiding fun and secure! 🎨🔒

🚀 Features

🖼️ Image Steganography: Hide and reveal data in PNG, JPG, or JPEG files using LSB techniques.
🎞️ GIF Steganography: Embed secrets in GIFs with frame-based steganography.
🔐 Encryption: Secure your data with Fernet encryption using custom or auto-generated keys.
🛡️ Authentication: Add optional passwords and author metadata for extra security.
📂 Drag-and-Drop: Load carrier files and data with a simple drag-and-drop.
📜 Operation History: Keep track of all your embedding, extraction, and metadata operations.
⏳ Progress Bars: Watch your tasks progress with vibrant, animated bars and time estimates.
🌐 Cross-Platform: Runs smoothly on Windows, macOS, and Linux.
🎨 Modern UI: A colorful, dark-themed interface that’s easy on the eyes.


🛠️ Getting Started
Prerequisites

🐍 Python 3.8 or higher
📦 Install dependencies with:pip install customtkinter pillow numpy cryptography tkinterdnd2



Installation

Clone the repo:
git clone https://github.com/your-username/hidenseek.git
cd hidenseek


Install dependencies:
pip install -r requirements.txt


Launch the app:
python main.py




🎮 How to Use

Open the App:

Run main.py to dive into the colorful GUI! 🌈


Choose Your Mode:

🖼️ Image-Stego: For PNG, JPG, or JPEG files.
🎞️ GIF-Stego: For GIF files.
📜 History: Review past operations.
❓ Help: Get quick tips and instructions.


Embed Data:

Drag-and-drop or browse to select a carrier image/GIF.
Choose up to 20 files to hide.
Generate or enter an encryption key 🔑.
(Optional) Add a password and author name.
Hit Embed Data and save your stego file! 💾


Extract Data:

Load a stego image/GIF.
Enter the encryption key and password (if used).
Click Extract Data and select an output folder.


View Metadata:

Load a stego file.
Enter the key and password.
Click View Metadata to see author and timestamp details.




📁 Project Structure

main.py: The heart of the app with the GUI and core logic.
img.py: Powers image steganography with SteganographyLogic.
gif.py: Handles GIF steganography with GIFSteganographyLogic.
history.json: Auto-generated file for operation history.
requirements.txt: Lists all dependencies.


⚠️ Important Notes

🔑 Keep Keys Safe: Store your encryption key and password securely—they’re required for extraction!
📏 File Size Matters: Ensure your carrier file has enough capacity (check estimated times in the app).
🛡️ Integrity Checks: SHA-256 hashes ensure your files haven’t been tampered with.
📉 File Limit: Embed up to 20 files at a time for optimal performance.


🤝 Contributing
We’d love your help to make HideNSeek even better! Here’s how to contribute:

Fork the repo 🍴.
Create a feature branch (git checkout -b feature/amazing-feature).
Commit your changes (git commit -m 'Add amazing feature').
Push to the branch (git push origin feature/amazing-feature).
Open a pull request 🚀.


📜 License
This project is licensed under the MIT License. See the LICENSE file for details.

🙌 Acknowledgments

🎨 CustomTkinter for the stunning GUI.
🖼️ Pillow for powerful image processing.
🔒 Cryptography for secure encryption.
🌟 Inspired by the art of steganography and modern design trends.


Hide your data with flair and uncover it with ease—HideNSeek has you covered! 😎
