# accounts/management/commands/fix_user_roles.py

from django.core.management.base import BaseCommand
from accounts.models import CustomUser, Role

class Command(BaseCommand):
    help = 'Fix user roles - Remove admin roles from customers'

    def handle(self, *args, **kwargs):
        # Get customers with admin roles
        customers_with_admin_roles = CustomUser.objects.filter(
            user_type='customer',
            role__isnull=False
        ).exclude(
            role__name__icontains='customer'
        )
        
        count = customers_with_admin_roles.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No issues found!'))
            return
        
        self.stdout.write(f'⚠️ Found {count} customers with admin roles:')
        
        for user in customers_with_admin_roles:
            self.stdout.write(f'  - {user.full_name} ({user.email}) has role: {user.role.name}')
        
        # Ask for confirmation
        confirm = input('\n❓ Remove admin roles from customers? (yes/no): ')
        
        if confirm.lower() == 'yes':
            updated = 0
            for user in customers_with_admin_roles:
                user.role = None
                user.is_staff = False
                user.is_superuser = False
                user.save()
                updated += 1
            
            self.stdout.write(self.style.SUCCESS(f'✅ Updated {updated} users!'))
        else:
            self.stdout.write('❌ Cancelled')