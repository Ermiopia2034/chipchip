import os
import importlib


def test_image_service_placeholder_on_failure(monkeypatch, tmp_path):
    # Force the image generation path to raise so we hit placeholder
    img_mod = importlib.import_module("app.services.image_service")

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_images(self, *args, **kwargs):  # pragma: no cover - force failure
            raise RuntimeError("no image api")

    # If genai exists, replace GenerativeModel; otherwise set genai to None to take placeholder path
    if getattr(img_mod, "genai", None):
        monkeypatch.setattr(img_mod.genai, "GenerativeModel", FakeModel, raising=True)
    else:
        monkeypatch.setattr(img_mod, "genai", None, raising=False)

    importlib.reload(img_mod)
    # Direct output to a writable tmp directory
    tmp_images = tmp_path / "images"
    tmp_images.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(img_mod, "STATIC_DIR", str(tmp_images), raising=True)
    svc = img_mod.ImageService()
    url = svc.generate_product_image("Tomato")
    assert url.startswith("/static/images/")
    fname = os.path.basename(url)
    # STATIC_DIR is resolved relative to module; verify file exists there
    assert os.path.isfile(os.path.join(img_mod.STATIC_DIR, fname))
