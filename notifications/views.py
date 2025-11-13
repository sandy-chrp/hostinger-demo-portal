# notifications/views.py
"""
Customer-facing notification views (HTML pages)
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Notification


@login_required
def notification_list_view(request):
    """
    Customer notification list page
    Shows all notifications for logged-in customer
    """
    # Get notifications for current user
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Stats
    total_count = notifications.count()
    unread_count = notifications.filter(is_read=False).count()
    
    # Pagination
    paginator = Paginator(notifications, 15)  # 15 per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notifications': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/notification_list.html', context)