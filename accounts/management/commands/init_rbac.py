# accounts/management/commands/init_rbac.py
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Role, Permission

class Command(BaseCommand):
    help = 'Initialize RBAC system with default roles and permissions'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🚀 Starting RBAC initialization...'))
        
        try:
            with transaction.atomic():
                # Create Permissions
                self.create_permissions()
                
                # Create Roles
                self.create_roles()
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*70))
                self.stdout.write(self.style.SUCCESS('✅ RBAC SYSTEM INITIALIZED SUCCESSFULLY!'))
                self.stdout.write(self.style.SUCCESS('='*70))
                self.stdout.write(self.style.SUCCESS('✅ All permissions created/updated'))
                self.stdout.write(self.style.SUCCESS('✅ All roles configured with permissions'))
                self.stdout.write(self.style.WARNING('\n⚠️  NEXT STEPS:'))
                self.stdout.write('   1. Assign roles to users via User Management')
                self.stdout.write('   2. Test permissions with different role logins')
                self.stdout.write('   3. Customize as needed\n')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR: {str(e)}'))
            raise
    
    def create_permissions(self):
        """Create all system permissions organized by module"""
        self.stdout.write('\n📝 Creating/Updating permissions...')
        
        permissions_data = [
            # ===== USER MANAGEMENT (6) =====
            ('View Users', 'view_users', 'View employee user list and details', 'User Management'),
            ('Add User', 'add_user', 'Create new employee accounts', 'User Management'),
            ('Edit User', 'edit_user', 'Edit employee information and roles', 'User Management'),
            ('Delete User', 'delete_user', 'Delete employee accounts', 'User Management'),
            ('Manage User Roles', 'manage_user_roles', 'Assign and modify user roles', 'User Management'),
            ('View User Details', 'view_user_details', 'View detailed user information', 'User Management'),
            
            # ===== CUSTOMER MANAGEMENT (6) =====
            ('View Customers', 'view_customers', 'View customer list and details', 'Customer Management'),
            ('Add Customer', 'add_customer', 'Create new customer accounts', 'Customer Management'),
            ('Edit Customer', 'edit_customer', 'Edit customer information', 'Customer Management'),
            ('Delete Customer', 'delete_customer', 'Delete customer accounts', 'Customer Management'),
            ('Approve Customer', 'approve_customer', 'Approve/reject customer registrations', 'Customer Management'),
            ('Block Customer', 'block_customer', 'Block/unblock customer accounts', 'Customer Management'),
            
            # ===== DEMO MANAGEMENT (5) =====
            ('View Demos', 'view_demos', 'View demo list and details', 'Demo Management'),
            ('Add Demo', 'add_demo', 'Upload and create new demos', 'Demo Management'),
            ('Edit Demo', 'edit_demo', 'Edit demo information and content', 'Demo Management'),
            ('Delete Demo', 'delete_demo', 'Delete demos from system', 'Demo Management'),
            ('Manage Demo Access', 'manage_demo_access', 'Control demo visibility and access', 'Demo Management'),
            
            # ===== DEMO REQUESTS (4) =====
            ('View Demo Requests', 'view_demo_requests', 'View demo booking requests', 'Demo Requests'),
            ('Approve Demo Request', 'approve_demo_request', 'Approve demo bookings', 'Demo Requests'),
            ('Reject Demo Request', 'reject_demo_request', 'Reject demo bookings', 'Demo Requests'),
            ('Reschedule Demo', 'reschedule_demo', 'Reschedule demo appointments', 'Demo Requests'),
            
            # ===== ENQUIRIES (3) =====
            ('View Enquiries', 'view_enquiries', 'View business enquiries', 'Enquiries'),
            ('Respond to Enquiry', 'respond_enquiry', 'Respond to customer enquiries', 'Enquiries'),
            ('Delete Enquiry', 'delete_enquiry', 'Delete enquiries from system', 'Enquiries'),
            
            # ===== NOTIFICATIONS (4) =====
            ('View Notifications', 'view_notifications', 'View system notifications', 'Notifications'),
            ('Send Notification', 'send_notification', 'Send notifications to users', 'Notifications'),
            ('Manage Templates', 'manage_templates', 'Manage notification templates', 'Notifications'),
            ('Create Announcement', 'create_announcement', 'Create system announcements', 'Notifications'),
            # Notification Permissions
            {
                'code': 'view_notifications',
                'name': 'View Notifications',
                'description': 'Can view notification center',
                'category': 'notifications'
            },
            {
                'code': 'send_notification',
                'name': 'Send Notifications',
                'description': 'Can send bulk notifications to users',
                'category': 'notifications'
            },
            {
                'code': 'create_announcement',
                'name': 'Create Announcements',
                'description': 'Can create system-wide announcements',
                'category': 'notifications'
            },
            {
                'code': 'manage_templates',
                'name': 'Manage Notification Templates',
                'description': 'Can create and edit notification templates',
                'category': 'notifications'
            },
            
            # ===== BUSINESS CATEGORIES (8) =====
            ('View Categories', 'view_categories', 'View demo categories', 'Business Categories'),
            ('Add Category', 'add_category', 'Add new demo categories', 'Business Categories'),
            ('Edit Category', 'edit_category', 'Edit demo categories', 'Business Categories'),
            ('Delete Category', 'delete_category', 'Delete demo categories', 'Business Categories'),
            ('View Business Categories', 'view_business_categories', 'View business category list', 'Business Categories'),
            ('Add Business Category', 'add_business_category', 'Add new business category', 'Business Categories'),
            ('Edit Business Category', 'edit_business_category', 'Edit business category', 'Business Categories'),
            ('Delete Business Category', 'delete_business_category', 'Delete business category', 'Business Categories'),
            
            # ===== SETTINGS (4) =====
            ('View Settings', 'view_settings', 'View system settings', 'Settings'),
            ('Edit Settings', 'edit_settings', 'Modify system settings', 'Settings'),
            ('Manage Site Info', 'manage_site_info', 'Manage site information', 'Settings'),
            ('Manage Settings', 'manage_settings', 'Full settings management access', 'Settings'),
            
            # ===== ANALYTICS & REPORTS (3) =====
            ('View Analytics', 'view_analytics', 'View analytics and reports', 'Analytics & Reports'),
            ('Export Reports', 'export_reports', 'Export system reports', 'Analytics & Reports'),
            ('View User Activity', 'view_user_activity', 'View user activity logs', 'Analytics & Reports'),
            
            # ===== SYSTEM ADMINISTRATION (4) =====
            ('Manage Roles', 'manage_roles', 'Create and manage user roles', 'System Administration'),
            ('Manage Permissions', 'manage_permissions', 'Assign permissions to roles', 'System Administration'),
            ('Access Admin Panel', 'access_admin_panel', 'Access administrative panel', 'System Administration'),
            ('View System Logs', 'view_system_logs', 'View system logs', 'System Administration'),
        ]
        
        created_count = 0
        updated_count = 0
        
        for name, codename, description, module in permissions_data:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'description': description,
                    'module': module,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created: {name}')
            else:
                # Update existing permission
                updated = False
                if perm.name != name:
                    perm.name = name
                    updated = True
                if perm.description != description:
                    perm.description = description
                    updated = True
                if perm.module != module:
                    perm.module = module
                    updated = True
                
                if updated:
                    perm.save()
                    updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Permissions Summary: '
            f'{created_count} created, {updated_count} updated, '
            f'{Permission.objects.count()} total'
        ))
    
    def create_roles(self):
        """Create default system roles with permission assignments"""
        self.stdout.write('\n👥 Creating/Updating roles...')
        
        roles_created = 0
        roles_updated = 0
        
        # ===== ROLE 1: SUPER ADMIN =====
        super_admin, created = Role.objects.get_or_create(
            name='Super Admin',
            defaults={
                'description': 'Complete system access - manages everything including roles and permissions',
                'is_system_role': True,
                'is_active': True,
                'priority': 100
            }
        )
        super_admin.permissions.set(Permission.objects.all())
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: Super Admin ({Permission.objects.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: Super Admin ({Permission.objects.count()} permissions)')
        
        # ===== ROLE 2: ADMIN =====
        admin, created = Role.objects.get_or_create(
            name='Admin',
            defaults={
                'description': 'Administrative access - manages features except system administration',
                'is_system_role': True,
                'is_active': True,
                'priority': 80
            }
        )
        admin_perms = Permission.objects.filter(
            codename__in=[
                # User Management (view only)
                'view_users', 'view_user_details',
                # Customer Management (all)
                'view_customers', 'add_customer', 'edit_customer', 'approve_customer', 'block_customer',
                # Demo Management (all)
                'view_demos', 'add_demo', 'edit_demo', 'delete_demo', 'manage_demo_access',
                # Demo Requests (all)
                'view_demo_requests', 'approve_demo_request', 'reject_demo_request', 'reschedule_demo',
                # Enquiries
                'view_enquiries', 'respond_enquiry',
                # Notifications
                'view_notifications', 'send_notification',
                # Categories (all)
                'view_categories', 'add_category', 'edit_category', 'delete_category',
                'view_business_categories', 'add_business_category', 'edit_business_category',
                # Settings (view only)
                'view_settings',
                # Analytics
                'view_analytics', 'export_reports',
                # System
                'access_admin_panel'
            ]
        )
        admin.permissions.set(admin_perms)
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: Admin ({admin_perms.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: Admin ({admin_perms.count()} permissions)')
        
        # ===== ROLE 3: DEMO MANAGER =====
        demo_manager, created = Role.objects.get_or_create(
            name='Demo Manager',
            defaults={
                'description': 'Manages demos and demo requests - focused on demo operations',
                'is_system_role': False,
                'is_active': True,
                'priority': 60
            }
        )
        demo_perms = Permission.objects.filter(
            codename__in=[
                'view_customers',
                'view_demos', 'add_demo', 'edit_demo', 'manage_demo_access',
                'view_demo_requests', 'approve_demo_request', 'reject_demo_request', 'reschedule_demo',
                'view_notifications',
                'view_categories',
                'access_admin_panel'
            ]
        )
        demo_manager.permissions.set(demo_perms)
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: Demo Manager ({demo_perms.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: Demo Manager ({demo_perms.count()} permissions)')
        
        # ===== ROLE 4: CUSTOMER SUPPORT =====
        support, created = Role.objects.get_or_create(
            name='Customer Support',
            defaults={
                'description': 'Handles customer enquiries and support - customer-facing role',
                'is_system_role': False,
                'is_active': True,
                'priority': 40
            }
        )
        support_perms = Permission.objects.filter(
            codename__in=[
                'view_customers',
                'view_demos',
                'view_demo_requests',
                'view_enquiries', 'respond_enquiry',
                'view_notifications', 'send_notification',
                'access_admin_panel'
            ]
        )
        support.permissions.set(support_perms)
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: Customer Support ({support_perms.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: Customer Support ({support_perms.count()} permissions)')
        
        # ===== ROLE 5: VIEWER =====
        viewer, created = Role.objects.get_or_create(
            name='Viewer',
            defaults={
                'description': 'Read-only access - can view data but cannot make changes',
                'is_system_role': False,
                'is_active': True,
                'priority': 20
            }
        )
        viewer_perms = Permission.objects.filter(
            codename__in=[
                'view_users', 'view_user_details',
                'view_customers',
                'view_demos',
                'view_demo_requests',
                'view_enquiries',
                'view_notifications',
                'view_categories',
                'view_business_categories',
                'view_analytics',
                'access_admin_panel'
            ]
        )
        viewer.permissions.set(viewer_perms)
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: Viewer ({viewer_perms.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: Viewer ({viewer_perms.count()} permissions)')
        
        # ===== ROLE 6: USER MANAGER (NEW) =====
        user_manager, created = Role.objects.get_or_create(
            name='User Manager',
            defaults={
                'description': 'Manages employee users and role assignments',
                'is_system_role': False,
                'is_active': True,
                'priority': 70
            }
        )
        user_mgr_perms = Permission.objects.filter(
            codename__in=[
                'view_users', 'add_user', 'edit_user', 'view_user_details', 'manage_user_roles',
                'view_customers',
                'manage_roles',
                'access_admin_panel'
            ]
        )
        user_manager.permissions.set(user_mgr_perms)
        if created:
            roles_created += 1
            self.stdout.write(f'  ✓ Created: User Manager ({user_mgr_perms.count()} permissions)')
        else:
            roles_updated += 1
            self.stdout.write(f'  ↻ Updated: User Manager ({user_mgr_perms.count()} permissions)')
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Roles Summary: {roles_created} created, {roles_updated} updated, '
            f'{Role.objects.count()} total'
        ))