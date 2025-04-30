from PIL import Image
import numpy as np

def flanchy_score(image_path):
    img = Image.open(image_path)
    pixels = np.array(img)
    
    if len(pixels.shape) == 3:
        # RGB image, flatten across channels
        lsb_plane = pixels & 1
        ones = np.sum(lsb_plane)
        total = lsb_plane.size
    else:
        # Grayscale
        lsb_plane = pixels & 1
        ones = np.sum(lsb_plane)
        total = lsb_plane.size

    ratio = ones / total
    deviation = abs(0.5 - ratio) * 2  # Deviation from ideal
    flanchy_score = (1 - deviation) * 100

    print(f"LSB 1s ratio: {ratio:.4f}")
    print(f"Flanchy randomness score: {flanchy_score:.2f}%")
    return flanchy_score

def flanchy_making(image_path):
    img = Image.open(image_path)
    pixels = np.array(img)
    lsb_plane = pixels & 1
    Image.fromarray((lsb_plane * 255).astype(np.uint8)).save("lsb_visual.png")
# Example usage
flanchy_making("untouched.jpg")
flanchy_score("lsb_visual.png")
