# core/webgl_views.py - MERGED VERSION (Keeps all existing + Adds progress tracking)

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, FileResponse, JsonResponse, StreamingHttpResponse
from django.conf import settings
from demos.models import Demo
from pathlib import Path
import mimetypes
import os
import zipfile
import shutil
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import unquote
import tempfile
from django.core.cache import cache


# ============================================================================
# ✅ NEW FUNCTION 1: Extract with Progress Tracking
# ============================================================================
def extract_webgl_zip_with_progress(demo, progress_key):
    """
    NEW: Extract WebGL ZIP file with REAL-TIME progress tracking
    Stores progress in cache so frontend can poll it
    """
    def update_progress(stage, percent, message):
        """Update progress in cache"""
        cache.set(progress_key, {
            'stage': stage,
            'percent': percent,
            'message': message,
        }, timeout=300)  # 5 minutes
    
    try:
        update_progress('init', 0, 'Initializing extraction...')
        
        if not demo.webgl_file:
            update_progress('error', 0, 'No WebGL file attached')
            return False, None, "No WebGL file attached"
        
        # Get extraction root
        extract_root = Path(settings.WEBGL_EXTRACT_ROOT)
        extract_root.mkdir(parents=True, exist_ok=True)
        
        # Create demo-specific directory
        extract_dir = extract_root / f'demo_{demo.slug}'
        
        # Check if already extracted
        if extract_dir.exists() and list(extract_dir.rglob('index.html')):
            update_progress('complete', 100, 'Already extracted - Loading...')
            return True, extract_dir, None
        
        # Remove old extraction
        if extract_dir.exists():
            update_progress('cleaning', 5, 'Removing old files...')
            shutil.rmtree(extract_dir)
        
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine storage type
        zip_path = None
        temp_file_path = None
        
        try:
            # Try local storage first
            zip_path = Path(demo.webgl_file.path)
            update_progress('download', 10, 'Using local storage...')
            
            if not zip_path.exists():
                update_progress('error', 0, 'Local file not found')
                return False, None, f"Local file not found"
                
        except (NotImplementedError, AttributeError):
            # File is on S3 - Download with progress
            update_progress('download', 10, 'Downloading from S3...')
            
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    demo.webgl_file.open('rb')
                    
                    # Get file size for progress calculation
                    try:
                        file_size = demo.webgl_file.size
                    except:
                        file_size = None
                    
                    chunk_size = 8192 * 16  # 128KB chunks for faster download
                    downloaded = 0
                    
                    for chunk in demo.webgl_file.chunks(chunk_size=chunk_size):
                        tmp.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress (10-50% for download)
                        if file_size:
                            progress = 10 + int((downloaded / file_size) * 40)
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = file_size / (1024 * 1024)
                            update_progress(
                                'download', 
                                progress, 
                                f'Downloading: {mb_downloaded:.1f}MB / {mb_total:.1f}MB'
                            )
                        else:
                            update_progress(
                                'download', 
                                30, 
                                f'Downloaded: {downloaded / (1024 * 1024):.1f}MB'
                            )
                    
                    demo.webgl_file.close()
                    temp_file_path = tmp.name
                
                update_progress('download', 50, f'Download complete: {downloaded / (1024 * 1024):.1f}MB')
                zip_path = Path(temp_file_path)
                
            except Exception as e:
                error_msg = f"S3 Download failed: {str(e)}"
                update_progress('error', 0, error_msg)
                
                if "403" in str(e) or "Forbidden" in str(e):
                    error_msg = "S3 Access Denied - Check permissions"
                elif "404" in str(e):
                    error_msg = "File not found in S3"
                
                return False, None, error_msg
        
        # Verify ZIP file
        update_progress('validate', 55, 'Validating ZIP file...')
        
        if not zipfile.is_zipfile(zip_path):
            if temp_file_path:
                os.remove(temp_file_path)
            update_progress('error', 0, 'Invalid ZIP file')
            return False, None, "File is not a valid ZIP archive"
        
        # Extract ZIP with progress
        update_progress('extract', 60, 'Extracting files...')
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                update_progress('extract', 65, f'Extracting {total_files} files...')
                
                # Extract with progress tracking
                for i, file in enumerate(file_list):
                    zip_ref.extract(file, extract_dir)
                    
                    # Update progress every 10 files or 1%
                    if i % max(1, total_files // 100) == 0:
                        progress = 65 + int((i / total_files) * 30)
                        update_progress(
                            'extract', 
                            progress, 
                            f'Extracting: {i + 1}/{total_files} files'
                        )
                
                update_progress('extract', 95, 'Extraction complete!')
                
        except zipfile.BadZipFile:
            if temp_file_path:
                os.remove(temp_file_path)
            update_progress('error', 0, 'Corrupted ZIP file')
            return False, None, "Invalid or corrupted ZIP file"
        
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        # Verify extraction
        update_progress('verify', 97, 'Verifying files...')
        
        extracted_files = list(extract_dir.rglob('*'))
        if not extracted_files:
            update_progress('error', 0, 'No files extracted')
            return False, None, "Extraction completed but no files found"
        
        # Check for index.html
        index_files = list(extract_dir.rglob('index.html'))
        if not index_files:
            update_progress('warning', 98, 'No index.html found')
        
        # Update demo record
        demo.extracted_path = f'webgl_extracted/demo_{demo.slug}'
        demo.save(update_fields=['extracted_path'])
        
        update_progress('complete', 100, 'Ready to view!')
        
        return True, extract_dir, None
        
    except Exception as e:
        error_msg = f"Extraction error: {str(e)}"
        update_progress('error', 0, error_msg)
        import traceback
        traceback.print_exc()
        return False, None, error_msg


# ============================================================================
# ✅ NEW FUNCTION 2: Progress API Endpoint
# ============================================================================
@csrf_exempt
def webgl_extraction_progress(request, demo_id):
    """
    NEW: API endpoint to check extraction progress
    Frontend polls this to update progress bar
    """
    demo = get_object_or_404(Demo, id=demo_id)
    progress_key = f'webgl_extract_progress_{demo.id}'
    
    progress_data = cache.get(progress_key)
    
    if not progress_data:
        # Check if already extracted
        extract_root = Path(settings.WEBGL_EXTRACT_ROOT)
        demo_dir = extract_root / f'demo_{demo.slug}'
        
        if demo_dir.exists() and list(demo_dir.rglob('index.html')):
            progress_data = {
                'stage': 'complete',
                'percent': 100,
                'message': 'Already extracted'
            }
        else:
            progress_data = {
                'stage': 'init',
                'percent': 0,
                'message': 'Waiting to start...'
            }
    
    return JsonResponse(progress_data)


# ============================================================================
# ✅ NEW FUNCTION 3: Start Extraction API
# ============================================================================
@csrf_exempt
def start_webgl_extraction(request, demo_id):
    """
    NEW: Start WebGL extraction with progress tracking
    Returns immediately, extraction happens with progress updates
    """
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    progress_key = f'webgl_extract_progress_{demo.id}'
    
    # Start extraction with progress tracking
    success, extract_path, error_msg = extract_webgl_zip_with_progress(demo, progress_key)
    
    return JsonResponse({
        'success': success,
        'error': error_msg,
    })


# ============================================================================
# EXISTING FUNCTION: extract_webgl_zip (Keep as fallback)
# ============================================================================
def extract_webgl_zip(demo):
    """
    EXISTING: Extract WebGL ZIP file to local directory for serving
    Handles both LOCAL and S3 storage (WITHOUT progress tracking)
    This function is kept for backward compatibility
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
            print(f"✅ Already extracted: {extract_dir}")
            return True, extract_dir, None
        
        # Remove old extraction if exists
        if extract_dir.exists():
            print(f"🗑️  Removing old extraction: {extract_dir}")
            shutil.rmtree(extract_dir)
        
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine if using S3 or local storage
        zip_path = None
        temp_file_path = None
        
        try:
            # Try to get local path (will fail if S3)
            zip_path = Path(demo.webgl_file.path)
            print(f"📂 Using LOCAL storage: {zip_path}")
            
            if not zip_path.exists():
                return False, None, f"Local file not found: {zip_path}"
                
        except (NotImplementedError, AttributeError):
            # File is on S3 - need to download it first
            print(f"☁️  File is on S3: {demo.webgl_file.name}")
            
            try:
                # Create temporary file for download
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    print(f"📥 Downloading from S3 to temp file: {tmp.name}")
                    
                    # Open file and read in chunks
                    demo.webgl_file.open('rb')
                    
                    # Download in chunks to handle large files
                    chunk_size = 8192
                    total_size = 0
                    
                    for chunk in demo.webgl_file.chunks(chunk_size=chunk_size):
                        tmp.write(chunk)
                        total_size += len(chunk)
                    
                    demo.webgl_file.close()
                    temp_file_path = tmp.name
                    
                    print(f"✅ Downloaded {total_size} bytes to {temp_file_path}")
                
                zip_path = Path(temp_file_path)
                
            except Exception as e:
                error_msg = f"Failed to download from S3: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Check if it's a permission issue
                if "403" in str(e) or "Forbidden" in str(e):
                    error_msg = "S3 Access Denied - Check bucket permissions and IAM credentials"
                elif "404" in str(e) or "Not Found" in str(e):
                    error_msg = "File not found in S3 bucket"
                
                return False, None, error_msg
        
        # Verify it's a ZIP file
        if not zipfile.is_zipfile(zip_path):
            if temp_file_path:
                os.remove(temp_file_path)
            return False, None, "File is not a valid ZIP archive"
        
        # Extract ZIP
        print(f"📦 Extracting ZIP: {zip_path}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get file list
                file_list = zip_ref.namelist()
                print(f"📄 ZIP contains {len(file_list)} files")
                
                # Extract all files
                zip_ref.extractall(extract_dir)
                
            print(f"✅ Extraction complete")
            
        except zipfile.BadZipFile:
            if temp_file_path:
                os.remove(temp_file_path)
            return False, None, "Invalid or corrupted ZIP file"
        
        # Clean up temp file if used
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"🗑️  Cleaned up temp file: {temp_file_path}")
        
        # Verify extraction
        extracted_files = list(extract_dir.rglob('*'))
        if not extracted_files:
            return False, None, "Extraction completed but no files found"
        
        print(f"📊 Extracted {len(extracted_files)} items")
        
        # Look for index.html
        index_files = list(extract_dir.rglob('index.html'))
        if not index_files:
            print(f"⚠️  Warning: No index.html found in extracted files")
            # List all HTML files found
            html_files = list(extract_dir.rglob('*.html'))
            if html_files:
                print(f"   Found {len(html_files)} HTML files: {[f.name for f in html_files]}")
        else:
            print(f"✅ Found index.html: {index_files[0].relative_to(extract_dir)}")
        
        # Update demo record with extracted path
        demo.extracted_path = f'webgl_extracted/demo_{demo.slug}'
        demo.save(update_fields=['extracted_path'])
        
        return True, extract_dir, None
        
    except PermissionError as e:
        error_msg = f"Permission error: {e}"
        print(f"❌ {error_msg}")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Extraction error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, None, error_msg


# ============================================================================
# EXISTING FUNCTION: webgl_preview
# ============================================================================
@xframe_options_exempt
def webgl_preview(request, demo_id):
    """
    ✅ FIXED: Admin WebGL preview with correct URL generation
    """
    demo = get_object_or_404(Demo, id=demo_id, file_type='webgl')
    
    # Check user permissions
    if not request.user.is_staff:
        messages.error(request, "Access denied")
        return redirect('core:admin_demos')
    
    print(f"\n{'='*60}")
    print(f"🎮 WebGL Preview Request")
    print(f"{'='*60}")
    print(f"Demo ID: {demo.id}")
    print(f"Demo Title: {demo.title}")
    print(f"Demo Slug: {demo.slug}")
    print(f"WebGL File: {demo.webgl_file.name if demo.webgl_file else 'None'}")
    print(f"Extracted Path: {demo.extracted_path or 'Not set'}")
    
    # Try to extract if not already done
    success, extract_path, error_msg = extract_webgl_zip(demo)
    
    if not success:
        print(f"❌ Extraction failed: {error_msg}")
        context = {
            'demo': demo,
            'error': error_msg or 'Failed to extract WebGL files',
            'extract_path': demo.extracted_path or 'Not extracted',
        }
        return render(request, 'admin/demos/webgl_error.html', context)
    
    # Find index.html
    index_files = list(extract_path.rglob('index.html'))
    
    if not index_files:
        print(f"❌ No index.html found")
        context = {
            'demo': demo,
            'error': 'No index.html found in extracted files',
            'extract_path': extract_path,
        }
        return render(request, 'admin/demos/webgl_error.html', context)
    
    # Get relative path to index.html
    index_path = index_files[0]
    rel_path = index_path.relative_to(extract_path)
    
    # ✅ CRITICAL FIX: Use reverse() to generate correct URL
    from django.urls import reverse
    
    serve_url = reverse('customers:serve_webgl_file', kwargs={
        'slug': demo.slug,
        'filepath': str(rel_path).replace('\\', '/')
    })
    
    print(f"✅ Preview ready")
    print(f"   Index: {rel_path}")
    print(f"   Serve URL: {serve_url}")
    print(f"{'='*60}\n")
    
    context = {
        'demo': demo,
        'webgl_url': serve_url,
        'extract_path': extract_path,
    }
    
    return render(request, 'admin/demos/webgl_preview.html', context)
# ============================================================================
# EXISTING FUNCTION: admin_universal_preview
# ============================================================================
@xframe_options_exempt
def admin_universal_preview(request, demo_id):
    """
    EXISTING: Universal admin preview for both video and WebGL
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


# ============================================================================
# EXISTING FUNCTION: universal_viewer
# ============================================================================
@xframe_options_exempt
def universal_viewer(request, demo_id):
    """
    EXISTING: Customer-facing universal demo viewer
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


# ============================================================================
# EXISTING FUNCTION: serve_webgl_file
# ============================================================================
def serve_webgl_file(request, slug, filepath):
    """
    EXISTING: Serve extracted WebGL files with proper MIME types
    Handles nested directory structures, spaces in filenames, and Brotli compression
    """
    try:
        # Decode URL-encoded filepath (handles spaces and special characters)
        filepath = unquote(filepath)
        
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
                'WebGL Build',
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
                filename_only = os.path.basename(filepath)
                matches = list(demo_dir.rglob(filename_only))
                
                if matches:
                    full_path = matches[0]
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
        
        # Custom MIME types for WebGL/Unity files
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
        
        # Handle Brotli compressed files (.br extension)
        if full_path.name.endswith('.br'):
            base_filename = full_path.name[:-3]
            base_ext = os.path.splitext(base_filename)[1].lower()
            mime_type = mime_map.get(base_ext, 'application/octet-stream')
            
            response = FileResponse(
                open(full_path, 'rb'),
                content_type=mime_type
            )
            response['Content-Encoding'] = 'br'
            
        else:
            ext = full_path.suffix.lower()
            mime_type = mime_map.get(ext, mimetypes.guess_type(str(full_path))[0] or 'application/octet-stream')
            
            # Use StreamingHttpResponse for large files (>10MB)
            file_size = full_path.stat().st_size
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                def file_iterator(file_path, chunk_size=8192):
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                
                response = StreamingHttpResponse(
                    file_iterator(full_path, chunk_size=65536),  # 64KB chunks
                    content_type=mime_type
                )
                response['Content-Length'] = file_size
            else:
                response = FileResponse(
                    open(full_path, 'rb'),
                    content_type=mime_type
                )
        
        # Add CORS headers for WebGL
        response['Access-Control-Allow-Origin'] = '*'
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cache control
        ext_for_cache = full_path.suffix.lower()
        if ext_for_cache in ['.wasm', '.data', '.unityweb', '.js', '.json', '.br']:
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            response['Cache-Control'] = 'public, max-age=86400'
        
        return response
        
    except FileNotFoundError:
        raise Http404(f"File not found: {filepath}")
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")


# ============================================================================
# EXISTING FUNCTION: serve_webgl_content
# ============================================================================
def serve_webgl_content(request, demo_id):
    """
    EXISTING: Serve main WebGL content (index.html)
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


# ============================================================================
# EXISTING FUNCTION: serve_webgl_asset
# ============================================================================
def serve_webgl_asset(request, demo_id, asset_path):
    """
    EXISTING: Serve WebGL asset files (wasm, data, js, etc.)
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


# ============================================================================
# EXISTING FUNCTION: webgl_file_info
# ============================================================================
def webgl_file_info(request, demo_id):
    """
    EXISTING: Debug view to show WebGL file structure (Admin only)
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