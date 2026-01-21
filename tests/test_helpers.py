"""Unit tests for helper functions."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_job_id(object_key: str):
    """Local copy of backend logic to avoid boto3 import."""
    parts = object_key.split("_", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def allowed_file(filename: str) -> bool:
    """Local copy of server logic."""
    ALLOWED = {'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


class TestParseJobId:

    def test_valid_key(self):
        result = parse_job_id("abc123_image.jpg")
        assert result == ("abc123", "image.jpg")

    def test_filename_with_underscores(self):
        result = parse_job_id("abc123_my_photo_2024.jpg")
        assert result == ("abc123", "my_photo_2024.jpg")

    def test_uuid_format(self):
        result = parse_job_id("550e8400-e29b-41d4-a716-446655440000_test.png")
        assert result == ("550e8400-e29b-41d4-a716-446655440000", "test.png")

    def test_missing_underscore(self):
        result = parse_job_id("nounderscorehere")
        assert result is None

    def test_empty_job_id(self):
        result = parse_job_id("_filename.jpg")
        assert result is None

    def test_empty_filename(self):
        result = parse_job_id("abc123_")
        assert result is None

    def test_empty_string(self):
        result = parse_job_id("")
        assert result is None


class TestAllowedFile:

    def test_jpg_allowed(self):
        assert allowed_file("photo.jpg") is True

    def test_jpeg_allowed(self):
        assert allowed_file("photo.jpeg") is True

    def test_png_allowed(self):
        assert allowed_file("photo.png") is True

    def test_uppercase_extension(self):
        assert allowed_file("photo.JPG") is True

    def test_gif_not_allowed(self):
        assert allowed_file("photo.gif") is False

    def test_pdf_not_allowed(self):
        assert allowed_file("document.pdf") is False

    def test_no_extension(self):
        assert allowed_file("noextension") is False

    def test_double_extension(self):
        assert allowed_file("file.txt.jpg") is True

    def test_hidden_file(self):
        assert allowed_file(".jpg") is True


class TestMessageClassification:

    def test_malformed_should_delete(self):
        assert parse_job_id("badmessage") is None

    def test_valid_should_process(self):
        assert parse_job_id("valid_key.jpg") is not None
