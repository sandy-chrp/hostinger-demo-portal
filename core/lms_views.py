# core/lms_views.py - LMS/SCORM Content Serving & Preview

from django.shortcuts import render, get_object_or_404
from django.http import FileResponse, Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from demos.models import Demo
import os
import mimetypes
import zipfile
import logging

logger = logging.getLogger(__name__)


def extract_lms_package(demo):
    """Extract LMS/SCORM ZIP package (same pattern as WebGL)"""
    if not demo.lms_file:
        return False, "No LMS file attached"
    
    zip_path = demo.lms_file.path
    if not os.path.exists(zip_path):
        return False, "LMS file not found"
    
    extract_dir = os.path.join(
        settings.MEDIA_ROOT,
        'lms_extracted',
        f'demo_{demo.slug}'
    )
    
    try:
        if os.path.exists(extract_dir):
            import shutil
            shutil.rmtree(extract_dir)
        
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        entry_file = find_lms_entry_point(extract_dir)
        if not entry_file:
            return False, "Invalid LMS package structure"
        
        demo.extracted_path = f'lms_extracted/demo_{demo.slug}'
        demo.save(skip_extraction=True)
        
        return True, entry_file
        
    except Exception as e:
        logger.error(f"LMS extraction failed: {str(e)}")
        return False, str(e)


def find_lms_entry_point(extract_dir):
    """Find main HTML entry point in SCORM package"""
    entry_points = [
        'index.html',
        'story.html',
        'index_lms.html',
        'scormdriver/indexAPI.html',
        'res/index.html',
    ]
    
    for filename in entry_points:
        if os.path.exists(os.path.join(extract_dir, filename)):
            return filename
    
    for root, dirs, files in os.walk(extract_dir):
        html_files = [f for f in files if f.lower().endswith('.html')]
        if html_files:
            rel_path = os.path.relpath(os.path.join(root, html_files[0]), extract_dir)
            return rel_path.replace('\\', '/')
    
    return None


@login_required
def lms_preview(request, demo_id):
    """Admin LMS preview (matches video watch view structure)"""
    demo = get_object_or_404(Demo, id=demo_id, file_type='lms')
    
    if not demo.extracted_path or not os.path.exists(
        os.path.join(settings.MEDIA_ROOT, demo.extracted_path)
    ):
        success, entry_or_error = extract_lms_package(demo)
        if not success:
            return render(request, 'admin/demos/extraction_error.html', {
                'demo': demo,
                'error': entry_or_error
            })
    
    extract_dir = os.path.join(settings.MEDIA_ROOT, demo.extracted_path)
    entry_file = find_lms_entry_point(extract_dir)
    
    if not entry_file:
        return render(request, 'admin/demos/extraction_error.html', {
            'demo': demo,
            'error': "No valid LMS entry point found"
        })
    
    lms_url = f"/demo/lms/{demo.slug}/{entry_file}"
    
    context = {
        'demo': demo,
        'lms_url': lms_url,
        'entry_file': entry_file,
        'business_categories': demo.target_business_categories.all(),
        'business_subcategories': demo.target_business_subcategories.all(),
        'demo_requests_count': demo.demo_requests.count(),
    }
    
    return render(request, 'admin/demos/lms_preview.html', context)


@login_required
def lms_extraction_progress(request, demo_id):
    """Check LMS extraction status (AJAX)"""
    try:
        demo = get_object_or_404(Demo, id=demo_id, file_type='lms')
        extract_dir = os.path.join(settings.MEDIA_ROOT, 'lms_extracted', f'demo_{demo.slug}')
        
        if os.path.exists(extract_dir) and demo.extracted_path:
            return JsonResponse({
                'status': 'complete',
                'entry_file': find_lms_entry_point(extract_dir),
                'message': 'LMS package extracted'
            })
        return JsonResponse({'status': 'processing'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def lms_file_info(request, demo_id):
    """Debug endpoint showing LMS file structure"""
    demo = get_object_or_404(Demo, id=demo_id, file_type='lms')
    
    info = {
        'demo_id': demo.id,
        'title': demo.title,
        'extracted_path': demo.extracted_path,
        'files': [],
    }
    
    if demo.extracted_path:
        extract_dir = os.path.join(settings.MEDIA_ROOT, demo.extracted_path)
        if os.path.exists(extract_dir):
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, extract_dir)
                    info['files'].append({
                        'path': rel_path.replace('\\', '/'),
                        'size_kb': round(os.path.getsize(file_path) / 1024, 2)
                    })
            info['entry_file'] = find_lms_entry_point(extract_dir)
            info['total_files'] = len(info['files'])
    
    return JsonResponse(info, json_dumps_params={'indent': 2})


def serve_lms_file(request, slug, filepath):
    """Serve LMS extracted files"""
    try:
        from urllib.parse import unquote
        filepath = unquote(filepath)
        
        demo = Demo.objects.filter(slug=slug, file_type='lms').first()
        if not demo or not demo.extracted_path:
            raise Http404("LMS content not found")
        
        extract_dir = os.path.join(settings.MEDIA_ROOT, demo.extracted_path)
        file_path = os.path.join(extract_dir, filepath)
        
        # Security check
        if not os.path.abspath(file_path).startswith(os.path.abspath(extract_dir)):
            raise Http404("Invalid path")
        
        if not os.path.exists(file_path):
            raise Http404(f"File not found: {filepath}")
        
        # MIME types
        mime_type, _ = mimetypes.guess_type(file_path)
        if file_path.endswith('.html'):
            mime_type = 'text/html'
        elif file_path.endswith('.js'):
            mime_type = 'application/javascript'
        elif file_path.endswith('.css'):
            mime_type = 'text/css'
        
        response = FileResponse(open(file_path, 'rb'), content_type=mime_type or 'application/octet-stream')
        response['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        raise Http404(f"Error: {str(e)}")