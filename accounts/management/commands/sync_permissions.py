from django.core.management.base import BaseCommand
from django.apps import apps
from accounts.models import Permission

class Command(BaseCommand):
    help = 'Auto-generate CRUD permissions for all models'

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0
        
        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            verbose_name = model._meta.verbose_name.title()
            
            # Skip Django internal models
            if app_label in ['admin', 'auth', 'contenttypes', 'sessions']:
                continue
            
            permission_templates = [
                ('view', f'View {verbose_name}', f'Can view {verbose_name} records'),
                ('add', f'Add {verbose_name}', f'Can create new {verbose_name} records'),
                ('edit', f'Edit {verbose_name}', f'Can modify {verbose_name} records'),
                ('delete', f'Delete {verbose_name}', f'Can delete {verbose_name} records'),
            ]
            
            module = app_label.replace('_', ' ').title()
            
            for action, name, description in permission_templates:
                perm_codename = f'{action}_{model_name}'
                
                # ✅ FIXED: Use codename
                if Permission.objects.filter(codename=perm_codename).exists():
                    skipped_count += 1
                    continue
                
                # ✅ FIXED: Use codename
                Permission.objects.create(
                    name=name,
                    codename=perm_codename,  # ✅ Database field
                    description=description,
                    module=module,
                    is_active=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created: {name} ({perm_codename})')
                )
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Summary: {created_count} created, {skipped_count} skipped'
            )
        )