"""
Custom Storage Backends for S3 + Local Hybrid System
Handles MIME types for WebGL/Unity files with proper Brotli support
"""

from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import mimetypes
import os


class MediaStorage(S3Boto3Storage):
    """
    S3 Storage for media files with WebGL/Unity MIME type support
    """
    location = 'media'
    file_overwrite = False
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Register custom MIME types for WebGL/Unity files
        self._register_custom_mimetypes()
    
    def _register_custom_mimetypes(self):
        """Register custom MIME types for WebGL and Unity builds"""
        custom_types = {
            # WebAssembly
            '.wasm': 'application/wasm',
            
            # Brotli compressed WebGL files
            '.wasm.br': 'application/wasm',
            '.js.br': 'application/javascript',
            '.data.br': 'application/octet-stream',
            '.framework.js.br': 'application/javascript',
            '.loader.js.br': 'application/javascript',
            '.symbols.json.br': 'application/json',
            
            # Unity WebGL files
            '.unityweb': 'application/octet-stream',
            '.data': 'application/octet-stream',
            
            # Standard web files
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.html': 'text/html',
            '.css': 'text/css',
            
            # 3D model formats
            '.gltf': 'model/gltf+json',
            '.glb': 'model/gltf-binary',
        }
        
        for ext, mime_type in custom_types.items():
            mimetypes.add_type(mime_type, ext)
    
    def _get_content_type(self, name):
        """
        Override to properly set content type for WebGL files
        """
        # Check for Brotli compressed files
        if name.endswith('.br'):
            # Get base extension before .br
            base_name = name[:-3]  # Remove .br
            base_ext = os.path.splitext(base_name)[1].lower()
            
            # Map to correct MIME type
            brotli_mime_map = {
                '.wasm': 'application/wasm',
                '.js': 'application/javascript',
                '.data': 'application/octet-stream',
                '.json': 'application/json',
            }
            
            return brotli_mime_map.get(base_ext, 'application/octet-stream')
        
        # For non-Brotli files, use standard detection
        content_type, _ = mimetypes.guess_type(name)
        
        # Fallback to custom mappings if needed
        if not content_type:
            ext = os.path.splitext(name)[1].lower()
            custom_map = getattr(settings, 'AWS_S3_FILE_MIME_TYPES', {})
            content_type = custom_map.get(ext, 'application/octet-stream')
        
        return content_type or 'application/octet-stream'
    
    def get_object_parameters(self, name):
        """
        Set custom headers for WebGL files, especially Brotli compression
        """
        params = super().get_object_parameters(name)
        
        # Add Content-Encoding for Brotli files
        if name.endswith('.br'):
            params['ContentEncoding'] = 'br'
            params['ContentType'] = self._get_content_type(name)
        
        # Ensure proper MIME type
        if 'ContentType' not in params:
            params['ContentType'] = self._get_content_type(name)
        
        # Cache control for WebGL assets (1 year)
        if any(name.endswith(ext) for ext in ['.wasm', '.data', '.js', '.unityweb', '.br']):
            params['CacheControl'] = 'public, max-age=31536000, immutable'
        
        return params


class StaticStorage(S3Boto3Storage):
    """
    S3 Storage for static files
    """
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True


# Utility function for checking file type
def is_webgl_file(filename):
    """Check if a file is a WebGL/Unity asset"""
    webgl_extensions = [
        '.wasm', '.wasm.br',
        '.data', '.data.br',
        '.js', '.js.br',
        '.unityweb',
        '.framework.js', '.framework.js.br',
        '.loader.js', '.loader.js.br',
        '.json', '.symbols.json.br',
    ]
    return any(filename.lower().endswith(ext) for ext in webgl_extensions)