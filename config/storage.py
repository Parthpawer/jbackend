"""
Custom Cloudinary storage backend that converts every uploaded image to JPEG
before sending it to Cloudinary. This significantly reduces file sizes and
protects Cloudinary credit limits without noticeable quality loss.

Quality 85 is a sweet spot: visually lossless but ~40–60 % smaller than PNG.
"""
import io
from PIL import Image
from cloudinary_storage.storage import MediaCloudinaryStorage


class JPEGCloudinaryStorage(MediaCloudinaryStorage):
    """
    Converts any uploaded image to JPEG (quality=85) before sending to
    Cloudinary. Falls back gracefully if the file cannot be interpreted as
    an image (e.g. corrupt upload).
    """

    QUALITY = 85  # 1–95 — change here to tune the trade-off

    def _open(self, name, mode="rb"):
        return super()._open(name, mode)

    def _save(self, name, content):
        """Intercept the save, convert to JPEG, then delegate to Cloudinary."""
        try:
            # Read the original bytes
            content.seek(0)
            image = Image.open(content)

            # Convert palette/transparent modes so JPEG can handle them
            if image.mode in ("RGBA", "P", "LA"):
                # Paste onto a white background to flatten transparency
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Encode as JPEG into an in-memory buffer
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=self.QUALITY, optimize=True)
            buffer.seek(0)

            # Rename to ensure a .jpg extension so Next.js / browsers recognise it
            if not name.lower().endswith((".jpg", ".jpeg")):
                base = name.rsplit(".", 1)[0]
                name = f"{base}.jpg"

            # Replace the content object with our JPEG buffer
            content = buffer

        except Exception:
            # If anything goes wrong, fall back to uploading the original file
            import logging
            logging.getLogger(__name__).warning(
                "JPEGCloudinaryStorage: failed to convert image to JPEG, "
                "uploading original file instead.",
                exc_info=True,
            )
            content.seek(0)

        return super()._save(name, content)
