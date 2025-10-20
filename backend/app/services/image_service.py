from __future__ import annotations

import base64
import os
from datetime import datetime

import google.generativeai as genai

import logging
from app.config import settings


# Resolve static dir relative to this file to avoid CWD dependence in tests/runtime
_THIS_DIR = os.path.dirname(__file__)
_APP_DIR = os.path.dirname(_THIS_DIR)  # /app/app
# Serve path in main.py mounts '/static' to real dir '/app/static', so save under that root
_PROJECT_ROOT = os.path.dirname(_APP_DIR)  # /app
STATIC_DIR = os.path.join(_PROJECT_ROOT, "static", "images")


class ImageService:
    def __init__(self):
        # Ensure HTTP mode for AI Studio key environments
        os.environ.setdefault("GOOGLE_GENAI_USE_GRPC", "false")
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for image generation")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._ensure_static_dir()
        self._model_name = "models/gemini-2.5-flash-image"
        self._logger = logging.getLogger(__name__)

    def _ensure_static_dir(self):
        os.makedirs(STATIC_DIR, exist_ok=True)

    def generate_product_image(self, product_name: str) -> str:
        """
        Generate a real product image using Gemini image model and save under /static/images.
        Returns a URL path like "/static/images/<file>.png".
        Raises RuntimeError on failure (no placeholders).
        """
        prompt = (
            f"Professional product photography of fresh {product_name}, high quality, vibrant colors, "
            f"Ethiopian market context, clean white background, studio lighting, 4k"
        )

        model = genai.GenerativeModel(self._model_name)
        # Try with explicit mime_type first; fall back to default if not supported by SDK
        try:
            resp = model.generate_content(
                [prompt],
                generation_config={"mime_type": "image/png", "temperature": 0.2},
            )
        except Exception:
            resp = model.generate_content([prompt])

        # Parse inline image bytes from response
        # Find first inline image part
        try:
            parts = []
            for cand in getattr(resp, "candidates", []) or []:
                content = getattr(cand, "content", None)
                for p in (getattr(content, "parts", []) if content else []):
                    parts.append(p)
            inline = None
            mime = None
            for p in parts:
                inline = getattr(p, "inline_data", None)
                if inline and getattr(inline, "mime_type", "").startswith("image/"):
                    mime = getattr(inline, "mime_type", None)
                    break
                # dict-like fallback
                if isinstance(p, dict) and "inline_data" in p:
                    cand_inline = p["inline_data"]
                    if cand_inline.get("mime_type", "").startswith("image/"):
                        inline = cand_inline
                        mime = cand_inline.get("mime_type")
                        break
            if not inline:
                raise RuntimeError("No inline image found in response")
            data_b64 = getattr(inline, "data", None) or inline.get("data")  # type: ignore[attr-defined]
            if data_b64 is None:
                raise RuntimeError("Inline image missing data field")
            # If already bytes, use directly; else decode base64 string
            if isinstance(data_b64, (bytes, bytearray)):
                img_bytes = bytes(data_b64)
            else:
                # Robust base64 decode: strip data URL prefix and any Python bytes literal markers
                s = str(data_b64).strip()
                if s.startswith("data:") and "," in s:
                    s = s.split(",", 1)[1]
                # Strip surrounding quotes or b'' wrappers
                if (s.startswith("b'") and s.endswith("'")) or (s.startswith('b"') and s.endswith('"')):
                    s = s[2:-1]
                s = s.strip().strip('"').strip("'")
                s += "=" * ((4 - (len(s) % 4)) % 4)
                try:
                    img_bytes = base64.b64decode(s)
                except Exception:
                    img_bytes = base64.urlsafe_b64decode(s)
        except Exception as e:
            raise RuntimeError(f"Failed to parse image response: {e}")

        # Choose file extension based on mime type or sniff bytes
        def _ext_from(m: str | None, b: bytes) -> str:
            if m == "image/png" or (len(b) > 8 and b[:8] == b"\x89PNG\r\n\x1a\n"):
                return ".png"
            if m == "image/jpeg" or (len(b) > 2 and b[:2] == b"\xff\xd8"):
                return ".jpg"
            if m == "image/webp" or (len(b) > 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"):
                return ".webp"
            return ".bin"

        ext = _ext_from(mime, img_bytes)
        self._logger.info(
            "Image generated: mime=%s size=%dB chosen_ext=%s sig=%s",
            mime,
            len(img_bytes),
            ext,
            img_bytes[:8].hex() if len(img_bytes) >= 8 else img_bytes.hex(),
        )
        fname = f"{product_name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}{ext}"
        fpath = os.path.join(STATIC_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(img_bytes)
        return f"/static/images/{fname}"
