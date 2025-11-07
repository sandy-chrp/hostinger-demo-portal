from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def landing_page(request):
    """
    Main landing page - public access
    Shows company info, features, demo showcases
    """
    # If user already logged in, redirect to dashboard
    if request.user.is_authenticated:
        if hasattr(request.user, 'customer'):
            return redirect('customers:dashboard')
        else:
            return redirect('admin:index')
    
    context = {
        'page_title': 'Welcome to CHRP India',
        'company_name': 'CHRP India',
    }
    
    return render(request, 'landing/index.html', context)

