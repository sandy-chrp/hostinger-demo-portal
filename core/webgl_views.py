# core/webgl_views.py - CORRECTED VERSION WITH PROPER EXTRACTION

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, FileResponse
from django.conf import settings
from demos.models import Demo
from pathlib import Path
import mimetypes
import os
import zipfile
import shutil
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt


def extract_webgl_zip(demo):
    """
    Extract WebGL ZIP file to local directory for serving
    Returns: (success: bool, extract_path: Path or None, error_message: str or None)
    """
    try:
        if not demo.webgl_file:
            return False, None, "No WebGL file attached"
        
        # Get extraction root
        extract_root = Path(settings.WEBGL_EXTRACT_ROOT)
        extract_root.mkdir(parents=True, exist_ok=True)
        
        # Create demo-specific directory
        extract_dir = extract_root / f'demo_{demo.slug}'
        
        # Check if already extracted and valid
        if extract_dir.exists() and list(extract_dir.rglob('index.html')):
            return True, extract_dir, None
        
        # Remove old extraction if exists
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Get ZIP file path
        if hasattr(demo.webgl_file, 'path'):
            # Local storage
            zip_path = Path(demo.webgl_file.path)
        else:
            # S3 or other storage - download temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                for chunk in demo.webgl_file.chunks():
                    tmp.write(chunk)
                zip_path = Path(tmp.name)
        
        # Verify it's a ZIP file
        if not zipfile.is_zipfile(zip_path):
            return False, None, "File is not a valid ZIP archive"
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Verify extraction
        if not extract_dir.exists() or not list(extract_dir.rglob('*')):
            return False, None, "Extraction completed but no files found"
        
        # Update demo record
        demo.webgl_extracted_path = f'webgl_extracted/demo_{demo.slug}'
        demo.save()
        
        return True, extract_dir, None
        
    except zipfile.BadZipFile:
        return False, None, "Invalid ZIP file format"
    except PermissionError as e:
        return False, None, f"Permission error: {e}"
    except Exception as e:
        return False, None, f"Extraction error: {str(e)}"


@xframe_options_exempt
def webgl_preview(request, demo_id):
    """
    Admin WebGL preview with iframe embedding allowed
    """
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    
    # Check user permissions
    if not request.user.is_staff:
        messages.error(request, "Access denied")
        return redirect('core:admin_demos')
    
    # Try to extract if not already done
    success, extract_path, error_msg = extract_webgl_zip(demo)
    
    if not success:
        context = {
            'demo': demo,
            'error': error_msg or 'Failed to extract WebGL files',
            'extract_path': demo.webgl_extracted_path or 'Not extracted',
        }
        return render(request, 'admin/demos/webgl_error.html', context)
    
    # Find index.html
    index_files = list(extract_path.rglob('index.html'))
    
    if not index_files:
        context = {
            'demo': demo,
            'error': 'No index.html found in extracted files',
            'extract_path': extract_path,
        }
        return render(request, 'admin/demos/webgl_error.html', context)
    
    # Get relative path to index.html
    index_path = index_files[0]
    rel_path = index_path.relative_to(extract_path)
    
    # Build serve URL
    serve_url = f"/demo/webgl/{demo.slug}/{rel_path}"
    
    context = {
        'demo': demo,
        'webgl_url': serve_url,
        'extract_path': extract_path,
    }
    
    return render(request, 'admin/demos/webgl_preview.html', context)


@xframe_options_exempt
def admin_universal_preview(request, demo_id):
    """
    Universal admin preview for both video and WebGL
    """
    demo = get_object_or_404(Demo, id=demo_id)
    
    if not request.user.is_staff:
        messages.error(request, "Access denied")
        return redirect('core:admin_demos')
    
    if demo.file_type == 'webgl':
        return webgl_preview(request, demo_id)
    
    # Video preview
    context = {'demo': demo}
    return render(request, 'admin/demos/video_preview.html', context)


@xframe_options_exempt
def universal_viewer(request, demo_id):
    """
    Customer-facing universal demo viewer
    """
    demo = get_object_or_404(Demo, id=demo_id, is_active=True)
    
    # Check customer access
    if not request.user.is_authenticated:
        messages.error(request, "Please login to view demos")
        return redirect('customers:signin')
    
    if demo.file_type == 'webgl':
        # Extract if needed
        success, extract_path, error_msg = extract_webgl_zip(demo)
        
        if not success:
            messages.error(request, f"WebGL demo unavailable: {error_msg}")
            return redirect('customers:dashboard')
        
        # Find index.html
        index_files = list(extract_path.rglob('index.html'))
        if not index_files:
            messages.error(request, "WebGL demo files corrupted")
            return redirect('customers:dashboard')
        
        rel_path = index_files[0].relative_to(extract_path)
        webgl_url = f"/demo/webgl/{demo.slug}/{rel_path}"
        
        context = {
            'demo': demo,
            'webgl_url': webgl_url,
        }
        return render(request, 'customers/webgl_viewer.html', context)
    
    # Video viewer
    context = {'demo': demo}
    return render(request, 'customers/video_viewer.html', context)

def serve_webgl_file(request, slug, filepath):
    """
    Serve extracted WebGL files with proper MIME types
    Handles nested directory structures automatically
    """
    try:
        # Get extraction root
        extract_root = Path(settings.WEBGL_EXTRACT_ROOT)
        demo_dir = extract_root / f'demo_{slug}'
        
        # Check if demo directory exists
        if not demo_dir.exists():
            raise Http404(f"Demo directory not found: demo_{slug}")
        
        # Try to find the file
        # First, try direct path
        full_path = demo_dir / filepath
        
        # If not found, search in subdirectories (common for Unity builds)
        if not full_path.exists():
            # Search for the file in common subdirectories
            search_dirs = [
                'Build',
                'build', 
                'WebGL',
                'webgl',
                'TemplateData',
            ]
            
            found = False
            for subdir in search_dirs:
                alt_path = demo_dir / subdir / filepath
                if alt_path.exists():
                    full_path = alt_path
                    found = True
                    break
            
            # If still not found, do a recursive search
            if not found:
                matches = list(demo_dir.rglob(filepath))
                if matches:
                    full_path = matches[0]  # Use first match
                else:
                    raise Http404(f"File not found: {filepath}")
        
        # Security: Prevent directory traversal
        try:
            full_path = full_path.resolve()
            demo_dir_resolved = demo_dir.resolve()
            
            if not str(full_path).startswith(str(demo_dir_resolved)):
                raise Http404("Invalid file path - security violation")
        except Exception:
            raise Http404("Invalid file path")
        
        # Verify it's a file
        if not full_path.is_file():
            raise Http404(f"Not a file: {filepath}")
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        
        # Custom MIME types for WebGL/Unity files
        ext = full_path.suffix.lower()
        mime_map = {
            '.wasm': 'application/wasm',
            '.data': 'application/octet-stream',
            '.unityweb': 'application/octet-stream',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.mem': 'application/octet-stream',
            '.html': 'text/html',
            '.css': 'text/css',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
        }
        
        # Handle Brotli compressed files
        if full_path.name.endswith('.br'):
            base_name = full_path.name[:-3]  # Remove .br
            base_ext = Path(base_name).suffix.lower()
            mime_type = mime_map.get(base_ext, 'application/octet-stream')
        else:
            mime_type = mime_map.get(ext, mime_type or 'application/octet-stream')
        
        # Open and serve file
        response = FileResponse(
            open(full_path, 'rb'),
            content_type=mime_type
        )
        
        # Add headers for Brotli compressed files
        if full_path.name.endswith('.br'):
            response['Content-Encoding'] = 'br'
        
        # Add CORS headers for WebGL
        response['Access-Control-Allow-Origin'] = '*'
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cache control
        if ext in ['.wasm', '.data', '.unityweb', '.js', '.json']:
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            response['Cache-Control'] = 'public, max-age=86400'
        
        return response
        
    except FileNotFoundError:
        raise Http404(f"File not found: {filepath}")
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")


def serve_webgl_content(request, demo_id):
    """
    Serve main WebGL content (index.html)
    """
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    
    # Extract if needed
    success, extract_path, error_msg = extract_webgl_zip(demo)
    
    if not success:
        return HttpResponse(
            f"<h1>Error</h1><p>{error_msg}</p>",
            content_type='text/html',
            status=500
        )
    
    # Find index.html
    index_files = list(extract_path.rglob('index.html'))
    
    if not index_files:
        return HttpResponse(
            "<h1>Error</h1><p>No index.html found</p>",
            content_type='text/html',
            status=404
        )
    
    index_path = index_files[0]
    
    # Serve index.html with proper headers
    response = FileResponse(
        open(index_path, 'rb'),
        content_type='text/html'
    )
    
    response['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response['Cross-Origin-Opener-Policy'] = 'same-origin'
    
    return response


def serve_webgl_asset(request, demo_id, asset_path):
    """
    Serve WebGL asset files (wasm, data, js, etc.)
    """
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    
    extract_root = Path(settings.WEBGL_EXTRACT_ROOT)
    demo_dir = extract_root / f'demo_{demo.slug}'
    
    full_path = demo_dir / asset_path
    
    # Security check
    if not full_path.resolve().is_relative_to(demo_dir.resolve()):
        raise Http404("Invalid path")
    
    if not full_path.exists():
        raise Http404(f"Asset not found: {asset_path}")
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(full_path))
    
    ext = full_path.suffix.lower()
    mime_map = {
        '.wasm': 'application/wasm',
        '.data': 'application/octet-stream',
        '.js': 'application/javascript',
        '.json': 'application/json',
    }
    mime_type = mime_map.get(ext, mime_type or 'application/octet-stream')
    
    response = FileResponse(open(full_path, 'rb'), content_type=mime_type)
    response['Access-Control-Allow-Origin'] = '*'
    
    return response


def webgl_file_info(request, demo_id):
    """
    Debug view to show WebGL file structure (Admin only)
    """
    if not request.user.is_staff:
        raise Http404()
    
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    
    # Try extraction
    success, extract_path, error_msg = extract_webgl_zip(demo)
    
    if not success:
        context = {
            'demo': demo,
            'success': False,
            'error': error_msg,
        }
        return render(request, 'admin/demos/webgl_info.html', context)
    
    # Get file structure
    files = []
    for file in extract_path.rglob('*'):
        if file.is_file():
            rel_path = file.relative_to(extract_path)
            files.append({
                'path': str(rel_path),
                'size': file.stat().st_size,
                'extension': file.suffix,
            })
    
    context = {
        'demo': demo,
        'success': True,
        'extract_path': extract_path,
        'files': files,
        'file_count': len(files),
    }
    
    return render(request, 'admin/demos/webgl_info.html', context)