# validators.py
from django.core.exceptions import ValidationError
import os

def validate_file_extension(value):
    """Validate file extension"""
    allowed_extensions = ['.png', '.webp', '.jpg', '.jpeg', '.pdf', '.xls', 
                         '.xlsx', '.csv', '.psd', '.doc', '.docx']
    ext = os.path.splitext(value.name)[1].lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Unsupported file extension. Allowed: PNG, WEBP, JPG, PDF, Excel, CSV, PSD, DOC'
        )

def validate_file_size(value):
    """Validate file size (max 10MB)"""
    filesize = value.size
    max_size_mb = 10
    max_size_bytes = max_size_mb * 1024 * 1024  # 10MB in bytes
    
    if filesize > max_size_bytes:
        raise ValidationError(f'Maximum file size is {max_size_mb}MB. Your file is {round(filesize/(1024*1024), 2)}MB')