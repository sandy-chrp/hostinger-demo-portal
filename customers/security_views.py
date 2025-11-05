# customers/security_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from .models import SecurityViolation, CustomerActivity
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
@login_required
def log_security_violation(request):
    """Enhanced security violation logging"""
    try:
        data = json.loads(request.body)
        violation_type = data.get('violation_type', 'unknown')
        description = data.get('description', '')
        severity = data.get('severity', 'medium')
        
        # Create violation record
        violation = SecurityViolation.objects.create(
            user=request.user,
            violation_type=violation_type,
            description=description,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            page_url=data.get('page_url', ''),
            severity=severity,
            timestamp=timezone.now()
        )
        
        # Check violation count
        recent_violations = SecurityViolation.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).count()
        
        response_data = {
            'success': True,
            'violation_id': violation.id,
            'recent_violations': recent_violations
        }
        
        # Auto-logout after 3 violations
        if recent_violations >= 3:
            response_data['action'] = 'logout'
            response_data['message'] = 'Multiple violations detected. Logging out for security.'
            
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Security violation logging error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@login_required
def security_logout(request):
    """Secure logout endpoint"""
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'success': True, 'redirect': '/auth/signin/'})
    else:
        logout(request)
        return redirect('/auth/signin/')

def get_client_ip(request):
    """Get real client IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip