
![Logo](https://github.com/Ziad-Ossama/HideNSeek/blob/722334e022db5b411b7f5fd2a660adad52e630c9/assets/Add%20a%20heading.png)


# HideNSeek – Multi-File Image and GIF Steganography

HideNSeek is a desktop application that hides multiple files inside static images (PNG/JPEG) and animated GIFs using advanced steganography.

The app uses AES-128 encryption (via Fernet), HMAC for file integrity, password protection, and zlib compression. It's designed with CustomTkinter and supports drag-and-drop, making it secure, fast, and user-friendly.


## Features

- 🔐 AES-128 encryption with Fernet
- 🔒 Password-based protection using PBKDF2-HMAC
- ✅ HMAC verification to detect tampering
- 📦 Multi-file support: 20 files in images, 40 in GIFs
- 🖼️ LSB-based embedding for images
- 🎞️ Trailer-byte appending for GIFs
- 🔍 View metadata without extracting
- 📂 Operation history saved to JSON
- 💡 Entropy analysis for carrier images
- 🖱️ GUI with drag-and-drop (CustomTkinter + tkinterDnD2)

## Project Structure
    HideNSeek/
    ├── main.py # GUI with CustomTkinter

    ├── img.py # LSB image steganography logic

    ├── gif.py # GIF trailer-byte steganography logic

    ├── assets/ # Logo and icons

    ├── history.json # Operation history log
    
    └── README.md # Project documentation
## Requirements

- Python 3.8+
- Pip packages:
  - `pillow`
  - `cryptography`
  - `numpy`
  - `customtkinter`
  - `tkinterdnd2`
  - `pyperclip`


## Installation
1.  **Clone the repository:**

```bash
> git clone https://github.com/Ziad-Ossama/HideNSeek
```
2.  **Navigate To Project's Directory:**

```bash
> cd HideNSeek
```
3.  **Install Dependencies:**

```bash
> pip install -r requirements.txt
```
## Deployment

To Run this Application run

```bash
> python main.py
```


## Screenshots
**Image-Stego Page:**

![Image-Stego Page](https://github.com/Ziad-Ossama/HideNSeek/blob/5f3e4b4842883cc96a635f9a676213957b2eae15/assets/Image-Stego_page.png)

**Gif-Stego Page:**

![Gif-Stego Page](https://github.com/Ziad-Ossama/HideNSeek/blob/5f3e4b4842883cc96a635f9a676213957b2eae15/assets/Gif-Stego_page.png)

**History Page:**

![History Page](https://github.com/Ziad-Ossama/HideNSeek/blob/5f3e4b4842883cc96a635f9a676213957b2eae15/assets/History-Stego_page.png)
