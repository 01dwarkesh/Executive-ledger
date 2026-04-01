import base64
import os
from PIL import Image
import io


def convert_to_grayscale(image_path: str) -> str:
    """
    Converts an image at image_path to grayscale in-place.
    Returns the same path on success.
    """
    with Image.open(image_path) as img:
        gray = img.convert("L").convert("RGBA")
        gray.save(image_path)
    return image_path


def save_mockup_from_base64(base64_str: str, item_id: str, upload_dir: str) -> str:
    """
    Decodes a base64 PNG string and saves it to uploads/mockups/{item_id}_mockup.png.
    Returns the static URL path.
    """
    data = base64_str.split(",", 1)[-1]
    img_bytes = base64.b64decode(data)

    dir_path = os.path.join(upload_dir, "mockups")
    os.makedirs(dir_path, exist_ok=True)

    filename = f"{item_id}_mockup.png"
    full_path = os.path.join(dir_path, filename)

    with open(full_path, "wb") as f:
        f.write(img_bytes)

    return f"/uploads/mockups/{filename}"
