from django.core.management.base import BaseCommand
from demos.models import Demo
import os

class Command(BaseCommand):
    help = 'Fix existing demos after code update'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing existing demos...\n')
        
        demos = Demo.objects.all()
        fixed = 0
        errors = 0
        
        for demo in demos:
            try:
                self.stdout.write(f'Processing: {demo.title}')
                
                # Create directories
                demo._ensure_extraction_directories()
                
                # Re-extract if needed
                if demo.file_type == 'webgl' and demo.webgl_file and not demo.extracted_path:
                    demo._extract_webgl_zip()
                    fixed += 1
                    
                elif demo.file_type == 'lms' and demo.lms_file and not demo.extracted_path:
                    demo._extract_lms_zip()
                    fixed += 1
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Error: {e}')
                errors += 1
        
        self.stdout.write(f'\n✅ Fixed: {fixed}')
        self.stdout.write(f'❌ Errors: {errors}')