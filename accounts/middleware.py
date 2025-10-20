# accounts/middleware.py
from django.utils.deprecation import MiddlewareMixin

class RBACMiddleware(MiddlewareMixin):
    """Simple RBAC middleware - adds permission checking to users"""
    
    def process_request(self, request):
        """Add permission check method to authenticated users"""
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            
            def has_permission(permission_code):
                """Check if user has specific permission"""
                user = request.user
                
                # Superuser has all permissions
                if user.is_superuser:
                    return True
                
                # Check role permissions
                if hasattr(user, 'role') and user.role:
                    return user.role.permissions.filter(
                        codename=permission_code,
                        is_active=True
                    ).exists()
                
                return False
            
            # Attach method to user
            request.user.has_permission = has_permission
        
        return None


class SystemInfoMiddleware(MiddlewareMixin):
    """Middleware to capture system information on login"""
    
    def process_request(self, request):
        """Capture IP address for employees"""
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            
            # Only for employees
            if hasattr(user, 'user_type') and user.user_type == 'employee':
                
                # Get current IP
                current_ip = self.get_client_ip(request)
                
                # Update if changed
                if current_ip and (not hasattr(user, 'last_login_ip') or user.last_login_ip != current_ip):
                    try:
                        user.last_login_ip = current_ip
                        user.save(update_fields=['last_login_ip'])
                    except Exception:
                        # Ignore errors (e.g., during migrations)
                        pass
        
        return None
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip