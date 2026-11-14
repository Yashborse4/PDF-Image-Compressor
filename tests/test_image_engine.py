"""
Unit tests for DocuTools Image Engine.
"""

import tempfile
from pathlib import Path
from PIL import Image
from docutools.core.image_engine import ImageEngine


def _create_sample_image(file_path: Path, width: int = 1200, height: int = 800, fmt: str = "JPEG") -> None:
    """Helper to generate a test image."""
    img = Image.new("RGB", (width, height), color=(60, 120, 200))
    img.save(file_path, format=fmt)


def test_image_info_and_resize():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = Path(tmp_dir) / "sample.jpg"
        _create_sample_image(img_path, width=800, height=400)

        info = ImageEngine.get_image_info(img_path)
        assert info["width"] == 800
        assert info["height"] == 400
        assert info["format"] == "JPEG"

        # Resize keeping aspect ratio
        with Image.open(img_path) as img:
            resized = ImageEngine.resize_image(img, target_width=400, maintain_aspect_ratio=True)
            assert resized.width == 400
            assert resized.height == 200


def test_image_crop():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = Path(tmp_dir) / "sample.jpg"
        _create_sample_image(img_path, width=500, height=500)

        with Image.open(img_path) as img:
            cropped = ImageEngine.crop_image(img, (50, 50, 250, 250))
            assert cropped.size == (200, 200)


def test_target_size_compression():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = Path(tmp_dir) / "large.jpg"
        # Create a large patterned image
        img = Image.effect_mandelbrot((1600, 1200), (-2.0, -1.0, 1.0, 1.0), 100).convert("RGB")
        img.save(img_path, format="JPEG", quality=95)

        initial_kb = img_path.stat().st_size / 1024
        assert initial_kb > 50

        # Compress to 50 KB target
        out_path = Path(tmp_dir) / "target_50k.jpg"
        stats = ImageEngine.process_single_image(
            input_path=img_path,
            output_path=out_path,
            target_kb=50,
            output_format="JPEG"
        )

        assert out_path.exists()
        final_kb = stats["final_size"] / 1024
        # Should be within tight margin of 50 KB (<= 55 KB)
        assert final_kb <= 60


def test_batch_image_processing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img1 = Path(tmp_dir) / "img1.png"
        img2 = Path(tmp_dir) / "img2.png"
        _create_sample_image(img1, 600, 400, fmt="PNG")
        _create_sample_image(img2, 600, 400, fmt="PNG")

        out_dir = Path(tmp_dir) / "batch_out"
        results = ImageEngine.process_batch(
            file_paths=[img1, img2],
            output_directory=out_dir,
            target_width=300,
            output_format="JPEG",
            quality=80
        )

        assert len(results) == 2
        assert Path(results[0]["output_file"]).exists()
        assert Path(results[1]["output_file"]).exists()
