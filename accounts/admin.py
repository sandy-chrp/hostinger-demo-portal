# accounts/admin.py (COMPLETE WITH RBAC)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    CustomUser, 
    BusinessCategory, 
    BusinessSubCategory, 
    EmailOTP,
    # RBAC Models
    Role,
    Permission
)


# =============================================
# RBAC ADMIN PANELS
# =============================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'codename', 
        'module_badge', 
        'is_active_badge',
        'roles_count'
    ]
    list_filter = ['module', 'is_active', 'created_at']
    search_fields = ['name', 'codename', 'description']
    ordering = ['module', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Permission Information', {
            'fields': ('name', 'codename', 'description', 'module')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def module_badge(self, obj):
        colors = {
            'customers': 'info',
            'demos': 'primary',
            'demo_requests': 'warning',
            'enquiries': 'success',
            'notifications': 'secondary',
            'business_categories': 'dark',
            'settings': 'danger',
            'analytics': 'info',
            'system': 'dark'
        }
        color = colors.get(obj.module, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_module_display()
        )
    module_badge.short_description = 'Module'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="badge badge-success">✓ Active</span>'
            )
        return format_html(
            '<span class="badge badge-danger">✗ Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def roles_count(self, obj):
        count = obj.roles.count()
        if count > 0:
            return format_html(
                '<span class="badge badge-primary">{} role(s)</span>',
                count
            )
        return format_html('<span class="text-muted">No roles</span>')
    roles_count.short_description = 'Assigned to Roles'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'priority',
        'users_count_badge',
        'permissions_count_badge',
        'is_active_badge',
        'system_role_badge'
    ]
    list_filter = ['is_active', 'is_system_role', 'priority', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-priority', 'name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['permissions']
    
    fieldsets = (
        ('Role Information', {
            'fields': ('name', 'description', 'priority')
        }),
        ('Permissions', {
            'fields': ('permissions',)
        }),
        ('Status & Type', {
            'fields': ('is_active', 'is_system_role')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def users_count_badge(self, obj):
        count = obj.get_users_count()
        if count > 0:
            return format_html(
                '<span class="badge badge-success">{} user(s)</span>',
                count
            )
        return format_html('<span class="text-muted">No users</span>')
    users_count_badge.short_description = 'Users'
    
    def permissions_count_badge(self, obj):
        count = obj.permissions.filter(is_active=True).count()
        return format_html(
            '<span class="badge badge-info">{} permission(s)</span>',
            count
        )
    permissions_count_badge.short_description = 'Permissions'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="badge badge-success">✓ Active</span>'
            )
        return format_html(
            '<span class="badge badge-danger">✗ Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def system_role_badge(self, obj):
        if obj.is_system_role:
            return format_html(
                '<span class="badge badge-warning">🔒 System</span>'
            )
        return format_html(
            '<span class="badge badge-light">Custom</span>'
        )
    system_role_badge.short_description = 'Type'
    
    def delete_model(self, request, obj):
        """Prevent deletion of system roles"""
        if obj.is_system_role:
            from django.contrib import messages
            messages.error(
                request, 
                f'Cannot delete system role: {obj.name}'
            )
            return
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Prevent bulk deletion of system roles"""
        system_roles = queryset.filter(is_system_role=True)
        if system_roles.exists():
            from django.contrib import messages
            messages.error(
                request,
                'Cannot delete system roles. Non-system roles will be deleted.'
            )
            queryset = queryset.filter(is_system_role=False)
        
        super().delete_queryset(request, queryset)


# =============================================
# CUSTOM USER ADMIN (WITH RBAC)
# =============================================

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    list_display = [
        'email',
        'full_name',
        'role_badge',  # NEW
        'organization',
        'mobile',
        'approval_status',
        'is_staff_badge',
        'created_at'
    ]
    
    list_filter = [
        'is_approved',
        'is_email_verified',
        'is_staff',
        'is_superuser',
        'role',  # NEW
        'business_category',
        'created_at'
    ]
    
    search_fields = [
        'email',
        'first_name',
        'last_name',
        'username',
        'organization',
        'mobile'
    ]
    
    ordering = ['-created_at']
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'last_login',
        'date_joined',
        'permissions_summary'  # NEW
    ]
    
    fieldsets = (
        ('Login Credentials', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name',
                'mobile',
                'country_code'
            )
        }),
        ('Business Information', {
            'fields': (
                'organization',
                'job_title',
                'business_category',
                'business_subcategory'
            )
        }),
        # NEW RBAC SECTION
        ('Role & Permissions', {
            'fields': (
                'role',
                'additional_permissions',
                'permissions_summary'
            ),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': (
                'is_approved',
                'is_email_verified',
                'is_active',
                'is_staff',
                'is_superuser'
            )
        }),
        ('Signup Information', {
            'fields': ('referral_source', 'referral_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'last_login',
                'date_joined'
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Login Credentials', {
            'fields': ('username', 'email', 'password1', 'password2')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'mobile', 'country_code')
        }),
        ('Business Information', {
            'fields': ('organization', 'job_title', 'business_category')
        }),
        # NEW
        ('Role & Permissions', {
            'fields': ('role',)
        }),
        ('Account Status', {
            'fields': ('is_approved', 'is_staff', 'is_superuser')
        }),
    )
    
    filter_horizontal = ['additional_permissions']  # NEW
    
    # NEW METHOD
    def role_badge(self, obj):
        """Display user's role with badge"""
        if obj.is_superuser:
            return format_html(
                '<span class="badge badge-danger">🔑 Superuser</span>'
            )
        
        if obj.role:
            colors = {
                'Super Admin': 'danger',
                'Admin': 'primary',
                'Demo Manager': 'info',
                'Customer Support': 'success',
                'Viewer': 'secondary'
            }
            color = colors.get(obj.role.name, 'secondary')
            return format_html(
                '<span class="badge badge-{}">{}</span>',
                color,
                obj.role.name
            )
        
        return format_html(
            '<span class="badge badge-light">No Role</span>'
        )
    role_badge.short_description = 'Role'
    
    # NEW METHOD
    def permissions_summary(self, obj):
        """Show user's permissions summary"""
        if obj.is_superuser:
            return format_html(
                '<div class="alert alert-danger">'
                '<strong>Superuser:</strong> Has all permissions'
                '</div>'
            )
        
        perms_by_module = obj.get_permissions_by_module()
        
        if not perms_by_module:
            return format_html(
                '<div class="alert alert-warning">'
                'No permissions assigned'
                '</div>'
            )
        
        html = '<div style="max-height: 300px; overflow-y: auto;">'
        html += '<table class="table table-sm table-bordered">'
        html += '<thead><tr><th>Module</th><th>Permissions</th></tr></thead>'
        html += '<tbody>'
        
        for module, perms in perms_by_module.items():
            html += f'<tr>'
            html += f'<td><strong>{module.replace("_", " ").title()}</strong></td>'
            html += f'<td><span class="badge badge-info">{len(perms)}</span> permissions</td>'
            html += f'</tr>'
        
        html += '</tbody></table></div>'
        
        return format_html(html)
    permissions_summary.short_description = 'Permissions Summary'
    
    def approval_status(self, obj):
        """Existing method"""
        if obj.is_approved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span>'
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">⏳ Pending</span>'
        )
    approval_status.short_description = 'Approval'
    
    def is_staff_badge(self, obj):
        """Existing method"""
        if obj.is_staff:
            return format_html(
                '<span class="badge badge-success">✓ Staff</span>'
            )
        return format_html(
            '<span class="badge badge-light">Customer</span>'
        )
    is_staff_badge.short_description = 'Type'
    
    def save_model(self, request, obj, form, change):
        """Override to handle role assignment"""
        super().save_model(request, obj, form, change)
        
        # Log role change
        if change and 'role' in form.changed_data:
            from django.contrib import messages
            if obj.role:
                messages.success(
                    request,
                    f'Role "{obj.role.name}" assigned to {obj.email}'
                )
            else:
                messages.info(
                    request,
                    f'Role removed from {obj.email}'
                )


# =============================================
# EXISTING ADMINS
# =============================================

@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    readonly_fields = ['created_at']


@admin.register(BusinessSubCategory)
class BusinessSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'sort_order', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'sort_order', 'name']
    readonly_fields = ['created_at']


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp', 'verified', 'created_at', 'expires_at']
    list_filter = ['verified', 'created_at']
    search_fields = ['email']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'expires_at']