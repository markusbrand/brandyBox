import pytest

from app.users.background_image import sniff_image_format

def test_sniff_image_format_jpeg():
    # JPEG signature is \xff\xd8\xff
    data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00"
    assert sniff_image_format(data) == ("image/jpeg", ".jpg")

def test_sniff_image_format_png():
    # PNG signature is \x89PNG\r\n\x1a\n
    data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert sniff_image_format(data) == ("image/png", ".png")

def test_sniff_image_format_gif87a():
    # GIF87a signature
    data = b"GIF87a\x01\x00\x01\x00\x80\x00\x00"
    assert sniff_image_format(data) == ("image/gif", ".gif")

def test_sniff_image_format_gif89a():
    # GIF89a signature
    data = b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    assert sniff_image_format(data) == ("image/gif", ".gif")

def test_sniff_image_format_webp():
    # WEBP signature: RIFF....WEBP
    data = b"RIFF\x12\x34\x56\x78WEBPVP8X\x0a"
    assert sniff_image_format(data) == ("image/webp", ".webp")

def test_sniff_image_format_short_data():
    # Less than 12 bytes should return None
    data = b"\xff\xd8\xff"
    assert sniff_image_format(data) is None

    data = b"GIF89a\x01\x00"
    assert sniff_image_format(data) is None

def test_sniff_image_format_invalid_data():
    # Not matching any signature but 12+ bytes long
    data = b"HELLO_WORLD_INVALID_IMAGE"
    assert sniff_image_format(data) is None
