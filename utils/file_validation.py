"""
File validation utilities for secure file uploads.

This module provides comprehensive validation for user-uploaded files,
including size checks, type verification, and dimension validation for images.
"""
from werkzeug.utils import secure_filename
from PIL import Image
import os
from typing import Optional, Tuple
from flask import current_app


# Configuration constants
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_DIMENSION = 4096  # 4096 pixels


class FileValidationError(Exception):
    """Exception raised when file validation fails."""
    pass


def allowed_file(filename: str) -> bool:
    """
    Check if the file extension is allowed.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if extension is allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_size(file_stream, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate that file size is within acceptable limits.
    
    Args:
        file_stream: File-like object
        max_size: Maximum allowed size in bytes
        
    Raises:
        FileValidationError: If file exceeds max_size
    """
    # Seek to end to get file size
    file_stream.seek(0, os.SEEK_END)
    file_size = file_stream.tell()
    file_stream.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise FileValidationError(
            f"Le fichier est trop volumineux. Taille maximale : {max_size_mb:.1f} MB"
        )


def validate_image_content(file_stream) -> Tuple[int, int, str]:
    """
    Validate that the file is actually an image and get its properties.
    
    Args:
        file_stream: File-like object
        
    Returns:
        Tuple of (width, height, format)
        
    Raises:
        FileValidationError: If file is not a valid image
    """
    try:
        with Image.open(file_stream) as img:
            width, height = img.size
            img_format = img.format
            file_stream.seek(0)  # Reset stream
            return width, height, img_format
    except Exception as e:
        file_stream.seek(0)
        raise FileValidationError(
            "Le fichier n'est pas une image valide ou est corrompu."
        )


def validate_image_dimensions(width: int, height: int, 
                              max_dimension: int = MAX_IMAGE_DIMENSION) -> None:
    """
    Validate that image dimensions are within acceptable limits.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        max_dimension: Maximum allowed dimension
        
    Raises:
        FileValidationError: If dimensions exceed max_dimension
    """
    if width > max_dimension or height > max_dimension:
        raise FileValidationError(
            f"L'image est trop grande. Dimensions maximales : {max_dimension}x{max_dimension} pixels"
        )


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a unique, secure filename.
    
    Args:
        original_filename: Original filename from upload
        prefix: Optional prefix for the filename
        
    Returns:
        Unique, sanitized filename
    """
    # Secure the filename
    filename = secure_filename(original_filename)
    
    # Add timestamp to ensure uniqueness
    import time
    timestamp = int(time.time() * 1000)
    
    # Split extension
    name, ext = os.path.splitext(filename)
    
    # Generate new filename
    if prefix:
        new_filename = f"{prefix}_{timestamp}{ext}"
    else:
        new_filename = f"{timestamp}_{name}{ext}"
    
    return new_filename


def validate_upload(file, file_type: str = "image") -> dict:
    """
    Comprehensive validation for uploaded files.
    
    Args:
        file: FileStorage object from Flask request
        file_type: Type of file expected ('image', 'document', etc.)
        
    Returns:
        Dictionary with validation results and metadata
        
    Raises:
        FileValidationError: If any validation check fails
    """
    if not file or file.filename == '':
        raise FileValidationError("Aucun fichier sélectionné")
    
    # Check file extension
    if not allowed_file(file.filename):
        raise FileValidationError(
            f"Type de fichier non autorisé. Extensions autorisées : {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    validate_file_size(file.stream)
    
    # For images, validate content and dimensions
    if file_type == "image":
        width, height, img_format = validate_image_content(file.stream)
        validate_image_dimensions(width, height)
        
        return {
            'valid': True,
            'width': width,
            'height': height,
            'format': img_format,
            'original_filename': file.filename
        }
    
    return {
        'valid': True,
        'original_filename': file.filename
    }


def save_validated_file(file, upload_folder: str, prefix: str = "") -> str:
    """
    Validate and save an uploaded file.
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Directory to save the file
        prefix: Optional prefix for the filename
        
    Returns:
        Relative path to saved file
        
    Raises:
        FileValidationError: If validation fails
    """
    # Validate the file
    validation_result = validate_upload(file)
    
    # Generate unique filename
    new_filename = generate_unique_filename(file.filename, prefix)
    
    # Ensure upload folder exists
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(upload_folder, new_filename)
    file.save(file_path)
    
    # Return relative path for database storage
    return new_filename


def process_and_save_image(file, upload_folder: str, prefix: str = "", 
                           target_size: Tuple[int, int] = (600, 800)) -> str:
    """
    Validate, resize, convert to JPG and save an image.
    
    Args:
        file: FileStorage object from Flask request
        upload_folder: Target directory
        prefix: Filename prefix
        target_size: Max dimensions (width, height) - default (600, 800)
        
    Returns:
        Filename of the saved JPG image
        
    Raises:
        FileValidationError: If validation fails
    """
    # 1. Validation de base
    validate_upload(file, file_type="image")
    
    try:
        # 2. Ouverture et traitement
        img = Image.open(file)
        
        # Conversion en RGB (nécessaire pour JPG si source est PNG/RGBA)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # 3. Redimensionnement (garde les proportions)
        # thumbnail modifie l'image en place
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # 4. Génération du nom de fichier (.jpg) - déterministe pour écraser l'ancien
        if prefix:
            new_filename = f"{prefix}.jpg"
        else:
            original_name = os.path.splitext(secure_filename(file.filename))[0]
            new_filename = f"{original_name}.jpg"
            
        # 5. Sauvegarde
        os.makedirs(upload_folder, exist_ok=True)
        save_path = os.path.join(upload_folder, new_filename)
        
        # Sauvegarde en JPG optimisé
        img.save(save_path, 'JPEG', quality=85, optimize=True)
        
        return new_filename
        
    except Exception as e:
        raise FileValidationError(f"Erreur lors du traitement de l'image : {str(e)}")
