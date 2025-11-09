import os
from typing import Optional
from uuid import uuid4

import qrcode
from io import BytesIO


DEFAULT_STATIC_DIR = "static"
DEFAULT_QR_SUBDIR = "qrcodes"


def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_qr_image(content: str, filename: Optional[str] = None) -> str:
    """Generate a QR code PNG under static/qrcodes and return the public URL path.

    Returns a path like /static/qrcodes/<filename>.png which can be served by FastAPI.
    """
    if filename is None:
        filename = f"{uuid4().hex}.png"

    output_dir = os.path.join(DEFAULT_STATIC_DIR, DEFAULT_QR_SUBDIR)
    ensure_dirs(output_dir)

    file_path = os.path.join(output_dir, filename)

    img = qrcode.make(content)
    img.save(file_path)

    # Public URL path (FastAPI mounted at /static)
    return f"/static/{DEFAULT_QR_SUBDIR}/{filename}"


def generate_qr_png_bytes(content: str) -> bytes:
    """Return PNG bytes for the QR code of given content."""
    img = qrcode.make(content)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


