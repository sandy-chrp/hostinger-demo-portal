
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import logout
from django.urls import reverse
import os
import mimetypes
from django.utils.deprecation import MiddlewareMixin
from django.http import FileResponse
import os




class CustomerSecurityMiddleware:
    """
    ✅ FIXED: Proper redirect to settings.LOGIN_URL
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # ✅ CHANGED: '/accounts/' → '/auth/'
        self.exempt_paths = [
            '/landing/',
            '/contact/',
            '/contact-sales/',
            '/auth/',              # ✅ YE CHANGE HUA
            '/admin/',
            '/static/',
            '/media/',
            '/__debug__/',
            '/customer/ajax/',
            '/django-admin/',
        ]
    
    def __call__(self, request):
        # AJAX skip
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_response(request)
        
        # Exempt paths skip
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)
        
        # Staff users skip
        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)
        
        # Customer portal check
        if request.path.startswith('/customer/'):
            if not request.user.is_authenticated:
                # ✅ FIXED: Use settings.LOGIN_URL instead of hardcoded path
                return redirect(f'{settings.LOGIN_URL}?next={request.path}')
            
            if not request.user.is_approved and not request.user.is_staff:
                try:
                    return redirect('accounts:pending_approval')
                except:
                    return redirect(settings.LOGIN_URL)
        
        return self.get_response(request)


class ContentProtectionMiddleware(MiddlewareMixin):
    """Middleware to add security headers for content protection"""
    
    def process_response(self, request, response):
        if '/customer/' in request.path and '/webgl-content/' not in request.path:
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://ajax.googleapis.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "img-src 'self' data: https:; "
                "media-src 'self' blob:; "
                "font-src 'self' https://cdnjs.cloudflare.com data:; "
                "connect-src 'self'; "
                "frame-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
            )
            response['Content-Security-Policy'] = csp_policy
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Referrer-Policy'] = 'same-origin'
        
        return response


class WebGLFileMiddleware:
    """Middleware to serve WebGL files without template processing"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if '/webgl-content/' in request.path:
            try:
                response = self.serve_webgl_file(request)
                if response:
                    return response
            except Http404:
                raise
            except Exception as e:
                print(f"WebGL middleware error: {e}")
        
        return self.get_response(request)
    
    def serve_webgl_file(self, request):
        """Serve WebGL files directly without Django template processing"""
        
        path_parts = request.path.split('/webgl-content/')
        if len(path_parts) != 2:
            raise Http404("Invalid WebGL content path")
        
        filepath = path_parts[1]
        
        demo_slug = None
        if '/demos/' in path_parts[0]:
            slug_parts = path_parts[0].split('/demos/')
            if len(slug_parts) == 2:
                demo_slug = slug_parts[1].rstrip('/')
        
        if not demo_slug:
            raise Http404("Demo not found")
        
        try:
            from demos.models import Demo
            demo = Demo.objects.filter(slug=demo_slug, is_active=True, file_type='webgl').first()
            
            if not demo:
                raise Http404("Demo not found")
            
            if request.user.is_authenticated:
                if not demo.can_customer_access(request.user):
                    raise Http404("Access denied")
            
            if demo.extracted_path:
                full_path = os.path.join(settings.MEDIA_ROOT, demo.extracted_path, filepath)
            else:
                full_path = demo.webgl_file.path if demo.webgl_file else None
            
        except Exception as e:
            print(f"Demo lookup error: {e}")
            raise Http404("Demo not found")
        
        if not full_path or not os.path.isfile(full_path):
            raise Http404(f"File not found: {filepath}")
        
        real_path = os.path.realpath(full_path)
        base_path = os.path.realpath(settings.MEDIA_ROOT)
        if not real_path.startswith(base_path):
            raise Http404("Invalid file path")
        
        content_type, _ = mimetypes.guess_type(full_path)
        
        if filepath.endswith('.js'):
            content_type = 'application/javascript; charset=utf-8'
        elif filepath.endswith('.wasm'):
            content_type = 'application/wasm'
        elif filepath.endswith('.data'):
            content_type = 'application/octet-stream'
        elif filepath.endswith('.html'):
            content_type = 'text/html; charset=utf-8'
        elif filepath.endswith('.json'):
            content_type = 'application/json; charset=utf-8'
        elif not content_type:
            content_type = 'application/octet-stream'
        
        try:
            with open(full_path, 'rb') as f:
                file_data = f.read()
            
            response = HttpResponse(file_data, content_type=content_type)
            response['Access-Control-Allow-Origin'] = '*'
            response['X-Content-Type-Options'] = 'nosniff'
            response['Cache-Control'] = 'public, max-age=3600'
            
            return response
            
        except Exception as e:
            print(f"❌ Error reading file {filepath}: {e}")
            raise Http404("Error serving file")


class CheckUserStatusMiddleware:
    """
    ✅ FIXED: Proper redirect with settings.LOGIN_URL
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # ✅ Exempt paths
        exempt_paths = [
            '/auth/',         # ✅ YE CHANGE HUA
            '/admin/',
            '/static/',
            '/media/',
            '/django-admin/',
        ]
        
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)
        
        if request.user.is_authenticated:
            if not (request.user.is_staff or request.user.is_superuser):
                
                # Blocked user check
                if hasattr(request.user, 'is_active') and not request.user.is_active:
                    logout(request)
                    messages.error(
                        request, 
                        'Your account has been blocked. Please contact support for assistance.'
                    )
                    try:
                        return redirect('accounts:account_blocked')
                    except:
                        # ✅ FIXED: Use settings.LOGIN_URL
                        return redirect(settings.LOGIN_URL)
                
                # Unapproved user check
                if hasattr(request.user, 'is_approved') and not request.user.is_approved:
                    logout(request)
                    messages.warning(
                        request, 
                        'Your account approval has been revoked. Please contact admin.'
                    )
                    try:
                        return redirect('accounts:pending_approval')
                    except:
                        # ✅ FIXED: Use settings.LOGIN_URL
                        return redirect(settings.LOGIN_URL)
        
        response = self.get_response(request)
        return response


class WebGLCompressionMiddleware:
    """Middleware to compress WebGL responses on-the-fly"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if '/webgl-content/' in request.path:
            if 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', ''):
                if 'Content-Encoding' not in response:
                    content_type = response.get('Content-Type', '')
                    if any(ct in content_type for ct in ['javascript', 'json', 'text', 'css']):
                        if hasattr(response, 'content') and len(response.content) > 1024:
                            try:
                                import gzip
                                compressed = gzip.compress(response.content, compresslevel=6)
                                response.content = compressed
                                response['Content-Encoding'] = 'gzip'
                                response['Content-Length'] = len(compressed)
                            except:
                                pass
        
        return response


class BrotliContentEncodingMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not isinstance(response, FileResponse):
            return response
        
        if hasattr(response, 'filename') and response.filename:
            filename = str(response.filename)
            if filename.endswith('.br'):
                response['Content-Encoding'] = 'br'
                base_name = filename[:-3]
                if base_name.endswith('.wasm'):
                    response['Content-Type'] = 'application/wasm'
                elif base_name.endswith('.js'):
                    response['Content-Type'] = 'application/javascript'
                elif base_name.endswith('.data'):
                    response['Content-Type'] = 'application/octet-stream'
                elif base_name.endswith('.json'):
                    response['Content-Type'] = 'application/json'
                response['Cache-Control'] = 'public, max-age=31536000, immutable'
                response['Access-Control-Allow-Origin'] = '*'
        return response


# ============================================
# SMART CSP MIDDLEWARE
# ============================================

class SmartCSPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        from django.conf import settings
        self.debug = settings.DEBUG

    def __call__(self, request):
        response = self.get_response(request)
        
        if self.debug:
            # Development: Remove CSP
            self._remove_csp_headers(response)
            print("🔓 [DEV] CSP Disabled")
        else:
            # Production: Add CSP
            self._add_production_csp(response)
            print("🔒 [PROD] CSP Enabled")
        
        return response
    
    def _remove_csp_headers(self, response):
        csp_headers = [
            'Content-Security-Policy',
            'Content-Security-Policy-Report-Only',
            'X-Content-Security-Policy',
            'X-WebKit-CSP',
        ]
        
        for header in csp_headers:
            if header in response:
                del response[header]
    
    def _add_production_csp(self, response):
        from django.conf import settings
        
        csp_directives = {
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://embed.tawk.to",
                "https://va.tawk.to",
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
            ],
            'img-src': ["'self'", "data:", "blob:", "https:"],
            'connect-src': ["'self'", "https://embed.tawk.to", "https://va.tawk.to", "wss://tawk.to"],
            'frame-src': ["'self'", "https://embed.tawk.to"],
        }
        
        csp_parts = []
        for directive, values in csp_directives.items():
            values_str = ' '.join(values)
            csp_parts.append(f"{directive} {values_str}")
        
        response['Content-Security-Policy'] = '; '.join(csp_parts)