"""
Tests for file validation utilities.
"""
import pytest
import os
from io import BytesIO
from PIL import Image
from utils.file_validation import (
    allowed_file,
    validate_file_size,
    validate_image_content,
    validate_image_dimensions,
    generate_unique_filename,
    validate_upload,
    FileValidationError,
    MAX_FILE_SIZE,
    MAX_IMAGE_DIMENSION
)


class TestAllowedFile:
    """Tests for allowed_file function."""
    
    def test_allowed_extensions(self):
        """Test that allowed extensions are accepted."""
        assert allowed_file('test.png') == True
        assert allowed_file('test.jpg') == True
        assert allowed_file('test.jpeg') == True
        assert allowed_file('test.webp') == True
    
    def test_case_insensitive(self):
        """Test that extension check is case insensitive."""
        assert allowed_file('test.PNG') == True
        assert allowed_file('test.JPG') == True
        assert allowed_file('test.WEBP') == True
    
    def test_disallowed_extensions(self):
        """Test that disallowed extensions are rejected."""
        assert allowed_file('test.gif') == False
        assert allowed_file('test.bmp') == False
        assert allowed_file('test.exe') == False
        assert allowed_file('test.pdf') == False
    
    def test_no_extension(self):
        """Test files without extensions are rejected."""
        assert allowed_file('testfile') == False


class TestValidateFileSize:
    """Tests for validate_file_size function."""
    
    def test_file_within_limit(self):
        """Test that files within size limit pass validation."""
        # Create a 1 MB file
        content = b'x' * (1 * 1024 * 1024)
        file_stream = BytesIO(content)
        
        # Should not raise
        validate_file_size(file_stream)
        
        # Stream should be reset
        assert file_stream.tell() == 0
    
    def test_file_exceeds_limit(self):
        """Test that files exceeding size limit raise error."""
        # Create a 6 MB file (exceeds 5 MB limit)
        content = b'x' * (6 * 1024 * 1024)
        file_stream = BytesIO(content)
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_size(file_stream)
        
        assert "trop volumineux" in str(exc_info.value).lower()
    
    def test_custom_max_size(self):
        """Test validation with custom max size."""
        content = b'x' * (2 * 1024 * 1024)  # 2 MB
        file_stream = BytesIO(content)
        
        # Should pass with 3 MB limit
        validate_file_size(file_stream, max_size=3 * 1024 * 1024)
        
        # Should fail with 1 MB limit
        file_stream.seek(0)
        with pytest.raises(FileValidationError):
            validate_file_size(file_stream, max_size=1 * 1024 * 1024)


class TestValidateImageContent:
    """Tests for validate_image_content function."""
    
    def create_test_image(self, width=100, height=100, format="PNG"):
        """Helper to create a test image."""
        img = Image.new('RGB', (width, height), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes
    
    def test_valid_png(self):
        """Test validation of valid PNG image."""
        img_bytes = self.create_test_image(100, 100, "PNG")
        width, height, img_format = validate_image_content(img_bytes)
        
        assert width == 100
        assert height == 100
        assert img_format == "PNG"
        assert img_bytes.tell() == 0  # Stream reset
    
    def test_valid_jpeg(self):
        """Test validation of valid JPEG image."""
        img_bytes = self.create_test_image(200, 150, "JPEG")
        width, height, img_format = validate_image_content(img_bytes)
        
        assert width == 200
        assert height == 150
        assert img_format == "JPEG"
    
    def test_invalid_image(self):
        """Test validation of invalid image data."""
        invalid_bytes = BytesIO(b"This is not an image")
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_image_content(invalid_bytes)
        
        assert "pas une image valide" in str(exc_info.value).lower()


class TestValidateImageDimensions:
    """Tests for validate_image_dimensions function."""
    
    def test_dimensions_within_limit(self):
        """Test that dimensions within limit pass validation."""
        # Should not raise
        validate_image_dimensions(1000, 1000)
        validate_image_dimensions(MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION)
    
    def test_width_exceeds_limit(self):
        """Test that excessive width raises error."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_image_dimensions(MAX_IMAGE_DIMENSION + 1, 100)
        
        assert "trop grande" in str(exc_info.value).lower()
    
    def test_height_exceeds_limit(self):
        """Test that excessive height raises error."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_image_dimensions(100, MAX_IMAGE_DIMENSION + 1)
        
        assert "trop grande" in str(exc_info.value).lower()
    
    def test_custom_max_dimension(self):
        """Test validation with custom max dimension."""
        # Should pass with 1000px limit
        validate_image_dimensions(800, 800, max_dimension=1000)
        
        # Should fail with 500px limit
        with pytest.raises(FileValidationError):
            validate_image_dimensions(800, 800, max_dimension=500)


class TestGenerateUniqueFilename:
    """Tests for generate_unique_filename function."""
    
    def test_basic_filename(self):
        """Test generation of basic filename."""
        filename = generate_unique_filename("test.png")
        
        assert filename.endswith(".png")
        assert "test" in filename
        assert len(filename) > len("test.png")  # Has timestamp
    
    def test_filename_with_prefix(self):
        """Test generation with prefix."""
        filename = generate_unique_filename("test.jpg", prefix="avatar")
        
        assert filename.startswith("avatar_")
        assert filename.endswith(".jpg")
    
    def test_filename_sanitization(self):
        """Test that unsafe filenames are sanitized."""
        unsafe_name = "../../../etc/passwd.png"
        filename = generate_unique_filename(unsafe_name)
        
        # Should not contain path traversal
        assert "../" not in filename
        assert filename.endswith(".png")
    
    def test_uniqueness(self):
        """Test that filenames are unique."""
        import time
        filename1 = generate_unique_filename("test.png")
        time.sleep(0.01)  # Ensure different timestamp
        filename2 = generate_unique_filename("test.png")
        
        assert filename1 != filename2


class TestValidateUpload:
    """Tests for validate_upload function."""
    
    def create_mock_file(self, filename, content=None, width=100, height=100):
        """Helper to create a mock file object."""
        from werkzeug.datastructures import FileStorage
        
        if content is None:
            # Create image content
            img = Image.new('RGB', (width, height), color='blue')
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            content = img_bytes
        
        return FileStorage(
            stream=content,
            filename=filename,
            content_type='image/png'
        )
    
    def test_valid_upload(self):
        """Test validation of valid upload."""
        mock_file = self.create_mock_file("test.png")
        result = validate_upload(mock_file)
        
        assert result['valid'] == True
        assert result['width'] == 100
        assert result['height'] == 100
        assert result['format'] == 'PNG'
    
    def test_no_file(self):
        """Test validation with no file."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_upload(None)
        
        assert "aucun fichier" in str(exc_info.value).lower()
    
    def test_empty_filename(self):
        """Test validation with empty filename."""
        mock_file = self.create_mock_file("")
        mock_file.filename = ""
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_upload(mock_file)
        
        assert "aucun fichier" in str(exc_info.value).lower()
    
    def test_disallowed_extension(self):
        """Test validation with disallowed extension."""
        mock_file = self.create_mock_file("test.gif")
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_upload(mock_file)
        
        assert "type de fichier non autorisé" in str(exc_info.value).lower()
    
    def test_file_too_large(self):
        """Test validation with oversized file."""
        # Create a large content
        large_content = BytesIO(b'x' * (6 * 1024 * 1024))
        mock_file = self.create_mock_file("test.png", content=large_content)
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_upload(mock_file)
        
        assert "trop volumineux" in str(exc_info.value).lower()
    
    def test_image_too_large_dimensions(self):
        """Test validation with oversized image dimensions."""
        mock_file = self.create_mock_file(
            "test.png", 
            width=MAX_IMAGE_DIMENSION + 100, 
            height=100
        )
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_upload(mock_file)
        
        assert "trop grande" in str(exc_info.value).lower()
