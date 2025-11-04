# core/contact_sales_context.py
from core.models import ContactMessage

def contact_sales_context(request):
    """Add contact sales unread count to context"""
    if request.user.is_authenticated and hasattr(request.user, 'role'):
        try:
            unread_count = ContactMessage.objects.filter(is_read=False).count()
            return {
                'contact_sales_unread': unread_count if unread_count > 0 else None,
            }
        except Exception:
            return {
                'contact_sales_unread': None,
            }
    
    return {
        'contact_sales_unread': None,
    }