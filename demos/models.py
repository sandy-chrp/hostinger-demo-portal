# demos/models.py - COMPLETE WITH ALL IMPORTS
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse
import uuid
import os
import zipfile
import shutil

User = get_user_model()



class DemoCategory(models.Model):
    """Categories for organizing demos"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    description = models.TextField(blank=True, verbose_name="Description")
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Emoji or CSS icon class",
        verbose_name="Icon"
    )
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Active")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Sort Order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'demo_categories'
        verbose_name = 'Demo Category'
        verbose_name_plural = 'Demo Categories'
        ordering = ['sort_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


def demo_video_path(instance, filename):
    """Generate upload path for video files"""
    return f'demos/videos/{instance.slug}/{filename}'


def demo_webgl_path(instance, filename):
    """Generate upload path for WebGL files"""
    return f'demos/webgl/{instance.slug}/{filename}'


def demo_lms_path(instance, filename):
    """Generate upload path for LMS/SCORM files"""
    return f'demos/lms/{instance.slug}/{filename}'


def demo_thumbnail_path(instance, filename):
    """Generate upload path for thumbnail images"""
    return f'demos/thumbnails/{instance.slug}/{filename}'

class Demo(models.Model):
    """Demo videos/presentations/WebGL/LMS content with complete support"""
    
    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Demo Title")
    description = models.TextField(verbose_name="Description")
    slug = models.SlugField(unique=True, blank=True, max_length=250)
    
    # File Type Selection
    FILE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('webgl', 'WebGL'),
        ('lms', 'LMS/SCORM'),
    ]
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        default='video',
        verbose_name="File Type",
        help_text="Select the type of demo content"
    )
    
    # Business Category Targeting
    target_business_categories = models.ManyToManyField(
        'accounts.BusinessCategory',
        blank=True,
        related_name='available_demos',
        verbose_name="Target Business Categories",
        help_text="Select business categories this demo is relevant for. Leave empty for all categories."
    )
    
    target_business_subcategories = models.ManyToManyField(
        'accounts.BusinessSubCategory',
        blank=True,
        related_name='available_demos',
        verbose_name="Target Business Subcategories",
        help_text="Select specific subcategories this demo is relevant for. Leave empty for all subcategories."
    )
    
    # Demo Type (Optional)
    DEMO_TYPE_CHOICES = [
        ('product', 'Product Demo'),
        ('feature', 'Feature Demo'),
        ('overview', 'Overview Demo'),
        ('tutorial', 'Tutorial'),
        ('case_study', 'Case Study'),
        ('webinar', 'Webinar Recording'),
    ]
    demo_type = models.CharField(
        max_length=20,
        choices=DEMO_TYPE_CHOICES,
        default='product',
        blank=True,
        null=True,
    )
    
    # MEDIA FILES
    video_file = models.FileField(
        upload_to=demo_video_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'wmv'])],
        verbose_name="Video File",
        help_text="Upload video file (required if file type is Video)"
    )
    
    webgl_file = models.FileField(
        upload_to=demo_webgl_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['html', 'zip', 'gltf', 'glb'])],
        verbose_name="WebGL File",
        help_text="Upload WebGL file - HTML, ZIP archive, or 3D model (required if file type is WebGL)"
    )
    
    lms_file = models.FileField(
        upload_to=demo_lms_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['zip', 'scorm'])],
        verbose_name="LMS/SCORM File",
        help_text="Upload LMS/SCORM package (ZIP format)"
    )
    
    extracted_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Extracted Path",
        help_text="Path to extracted WebGL/LMS files (auto-populated)"
    )
    
    thumbnail = models.ImageField(
        upload_to=demo_thumbnail_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name="Thumbnail Image",
        help_text="Upload custom thumbnail (optional - default icon will be shown if not provided)"
    )
    
    duration = models.DurationField(
        null=True, 
        blank=True, 
        help_text="Duration in HH:MM:SS format (applicable for videos only)",
        verbose_name="Duration"
    )
    
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="File Size (bytes)",
        help_text="Auto-calculated file size"
    )
    
    file_version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="File Version",
        help_text="Version number (optional)"
    )
    
    target_customers = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='accessible_demos',
        verbose_name="Target Customers",
        help_text="Select specific customers who can access this demo. Leave empty for all customers."
    )
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="Views Count")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    download_count = models.PositiveIntegerField(default=0, verbose_name="Download Count")
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_featured = models.BooleanField(
        default=False, 
        verbose_name="Featured/Suggested",
        help_text="Mark as suggested demo to highlight for customers"
    )
    sort_order = models.PositiveIntegerField(
        default=0, 
        verbose_name="Sort Order", 
        blank=True, 
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_demos',
        verbose_name="Created By"
    )
    
    class Meta:
        db_table = 'demos'
        verbose_name = 'Demo'
        verbose_name_plural = 'Demos'
        ordering = ['-is_featured', 'sort_order', '-created_at']
    
    def clean(self):
        """Validate that appropriate file is uploaded based on file_type"""
        if self.file_type == 'video' and not self.video_file:
            raise ValidationError({'video_file': 'Video file is required when file type is Video'})
        
        if self.file_type == 'webgl' and not self.webgl_file:
            raise ValidationError({'webgl_file': 'WebGL file is required when file type is WebGL'})
        
        if self.file_type == 'lms' and not self.lms_file:
            raise ValidationError({'lms_file': 'LMS/SCORM file is required when file type is LMS'})

    def save(self, *args, **kwargs):
        """Custom save to handle slug and file processing"""
        
        # Extract skip_extraction from kwargs before passing to super()
        skip_extraction = kwargs.pop('skip_extraction', False)
        
        # Generate slug if not exists
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Demo.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Check if this is a new instance or file has changed
        is_new = self.pk is None
        old_instance = None
        file_changed = False
        
        if not is_new:
            try:
                old_instance = Demo.objects.get(pk=self.pk)
                if self.file_type == 'video':
                    file_changed = old_instance.video_file != self.video_file
                elif self.file_type == 'webgl':
                    file_changed = old_instance.webgl_file != self.webgl_file
                elif self.file_type == 'lms':
                    file_changed = old_instance.lms_file != self.lms_file
            except Demo.DoesNotExist:
                pass
        
        # Save to database
        super().save(*args, **kwargs)
        
        # Handle file extraction after save
        if not skip_extraction and (is_new or file_changed):
            if self.file_type == 'webgl' and self.webgl_file:
                if self.webgl_file.size < 10 * 1024 * 1024:
                    try:
                        self._extract_webgl_zip()
                    except Exception as e:
                        print(f"❌ Error extracting WebGL: {e}")
                else:
                    print(f"⏳ Large WebGL file, skipping extraction")
            
            elif self.file_type == 'lms' and self.lms_file:
                if self.lms_file.size < 10 * 1024 * 1024:
                    try:
                        self._extract_lms_zip()
                    except Exception as e:
                        print(f"❌ Error extracting LMS: {e}")
                else:
                    print(f"⏳ Large LMS file, skipping extraction")

    def _calculate_file_size(self):
        """Auto-calculate file size based on file type"""
        try:
            if self.file_type == 'video' and self.video_file:
                self.file_size = self.video_file.size
            elif self.file_type == 'webgl' and self.webgl_file:
                self.file_size = self.webgl_file.size
            elif self.file_type == 'lms' and self.lms_file:
                self.file_size = self.lms_file.size
        except Exception as e:
            print(f"Error calculating file size: {e}")
            self.file_size = 0
    
    def _cleanup_extracted_files(self, path):
        """Clean up extracted WebGL/LMS files"""
        if path:
            extract_dir = os.path.join(settings.MEDIA_ROOT, path)
            if os.path.exists(extract_dir):
                try:
                    shutil.rmtree(extract_dir)
                    print(f"✅ Cleaned up old extracted files: {extract_dir}")
                except Exception as e:
                    print(f"❌ Error cleaning up extracted files: {e}")

    def _extract_webgl_zip(self):
        """Extract WebGL ZIP to LOCAL server"""
        if not self.webgl_file or not self.webgl_file.name.endswith('.zip'):
            return
        
        extract_dir = os.path.join(
            settings.MEDIA_ROOT,
            'webgl_extracted',
            f'demo_{self.slug}'
        )
        
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            if hasattr(settings, 'USE_S3') and settings.USE_S3:
                import tempfile
                
                print(f"📥 Downloading ZIP from S3: {self.webgl_file.name}")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    self.webgl_file.open('rb')
                    tmp_file.write(self.webgl_file.read())
                    self.webgl_file.close()
                    tmp_zip_path = tmp_file.name
                
                print(f"✅ Downloaded to temp: {tmp_zip_path}")
                
                with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                os.remove(tmp_zip_path)
                print(f"🗑️  Cleaned up temp file")
            
            else:
                print(f"📂 Extracting ZIP from local: {self.webgl_file.path}")
                
                with zipfile.ZipFile(self.webgl_file.path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            self.extracted_path = f'webgl_extracted/demo_{self.slug}'
            
            file_count = sum([len(files) for _, _, files in os.walk(extract_dir)])
            
            print(f"✅ WebGL ZIP extracted successfully!")
            print(f"   📁 Location: {extract_dir}")
            print(f"   📄 Files: {file_count}")
            
        except zipfile.BadZipFile:
            print(f"❌ Error: Invalid or corrupted ZIP file")
            self.extracted_path = ''
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
            self.extracted_path = ''
        except Exception as e:
            print(f"❌ Error extracting WebGL ZIP: {e}")
            import traceback
            traceback.print_exc()
            self.extracted_path = ''
    
    def _extract_lms_zip(self):
        """Extract LMS/SCORM ZIP package"""
        if not self.lms_file or not self.lms_file.name.endswith('.zip'):
            return
        
        extract_dir = os.path.join(
            settings.MEDIA_ROOT,
            'lms_extracted',
            f'demo_{self.slug}'
        )
        
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            if hasattr(settings, 'USE_S3') and settings.USE_S3:
                import tempfile
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    self.lms_file.open('rb')
                    tmp_file.write(self.lms_file.read())
                    self.lms_file.close()
                    tmp_zip_path = tmp_file.name
                
                with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                os.remove(tmp_zip_path)
            else:
                with zipfile.ZipFile(self.lms_file.path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            self.extracted_path = f'lms_extracted/demo_{self.slug}'
            
            file_count = sum([len(files) for _, _, files in os.walk(extract_dir)])
            print(f"✅ LMS ZIP extracted successfully! Files: {file_count}")
            
        except Exception as e:
            print(f"❌ Error extracting LMS ZIP: {e}")
            self.extracted_path = ''

    def get_thumbnail_url(self):
        """Return thumbnail URL or default icon based on file type"""
        if self.thumbnail:
            return self.thumbnail.url
        
        default_icons = {
            'video': '/static/images/icons/video-icon.png',
            'webgl': '/static/images/icons/webgl-icon.png',
            'lms': '/static/images/icons/lms-icon.png',
        }
        
        return default_icons.get(self.file_type, '/static/images/icons/default-icon.png')

    def get_webgl_index_url(self):
        """Get URL to WebGL index.html or file"""
        from django.urls import reverse
        
        if self.file_type != 'webgl' or not self.webgl_file:
            return None
        
        file_ext = os.path.splitext(self.webgl_file.name)[1].lower()
        
        if file_ext == '.zip' and self.extracted_path:
            possible_index_files = [
                'index.html',
                'Index.html',
                'build/index.html',
                'Build/index.html',
                'dist/index.html',
                'Dist/index.html',
            ]
            
            for rel_path in possible_index_files:
                full_path = os.path.join(
                    settings.MEDIA_ROOT, 
                    self.extracted_path, 
                    rel_path
                )
                
                if os.path.exists(full_path):
                    url_path = rel_path.replace('\\', '/')
                    
                    try:
                        return reverse('core:serve_webgl_file', kwargs={
                            'slug': self.slug,
                            'filepath': url_path
                        })
                    except Exception as e:
                        print(f"❌ Error generating URL for {url_path}: {e}")
                        return None
            
            extracted_dir = os.path.join(settings.MEDIA_ROOT, self.extracted_path)
            
            if os.path.exists(extracted_dir):
                for root, dirs, files in os.walk(extracted_dir):
                    for file in files:
                        if file.lower().endswith(('.html', '.htm')):
                            rel_path = os.path.relpath(
                                os.path.join(root, file),
                                extracted_dir
                            )
                            url_path = rel_path.replace('\\', '/')
                            
                            try:
                                return reverse('core:serve_webgl_file', kwargs={
                                    'slug': self.slug,
                                    'filepath': url_path
                                })
                            except Exception as e:
                                print(f"❌ Error generating URL: {e}")
                                return None
        
        elif file_ext == '.html':
            return self.webgl_file.url
        
        elif file_ext in ['.glb', '.gltf']:
            return self.webgl_file.url
        
        return None
    
    def get_lms_index_url(self):
        """Get URL to LMS/SCORM index.html"""
        from django.urls import reverse
        
        if self.file_type != 'lms' or not self.lms_file:
            return None
        
        if self.lms_file.name.endswith('.zip') and self.extracted_path:
            possible_index_files = [
                'index.html',
                'index_lms.html',
                'story.html',
                'scormdriver/indexAPI.html',
            ]
            
            for rel_path in possible_index_files:
                full_path = os.path.join(
                    settings.MEDIA_ROOT, 
                    self.extracted_path, 
                    rel_path
                )
                
                if os.path.exists(full_path):
                    url_path = rel_path.replace('\\', '/')
                    
                    try:
                        return reverse('core:serve_lms_file', kwargs={
                            'slug': self.slug,
                            'filepath': url_path
                        })
                    except Exception:
                        return None
        
        return None

    def get_webgl_viewer_type(self):
        """Determine which viewer to use"""
        if self.file_type != 'webgl' or not self.webgl_file:
            return None
        
        file_ext = os.path.splitext(self.webgl_file.name)[1].lower()
        
        if file_ext in ['.zip', '.html']:
            return 'iframe'
        elif file_ext in ['.glb', '.gltf']:
            return 'model-viewer'
        
        return 'iframe'
    
    def delete(self, *args, **kwargs):
        """Override delete to clean up all files"""
        if self.extracted_path:
            self._cleanup_extracted_files(self.extracted_path)
        
        files_to_delete = [
            self.video_file,
            self.webgl_file,
            self.lms_file,
            self.thumbnail,
        ]
        
        for file_field in files_to_delete:
            if file_field:
                try:
                    if hasattr(file_field, 'path') and os.path.isfile(file_field.path):
                        os.remove(file_field.path)
                except Exception as e:
                    print(f"Error deleting file: {e}")
        
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"
    
    @property
    def file_url(self):
        """Get the appropriate file URL based on file type"""
        if self.file_type == 'video' and self.video_file:
            return self.video_file.url
        elif self.file_type == 'webgl':
            return self.get_webgl_index_url()
        elif self.file_type == 'lms':
            return self.get_lms_index_url()
        return None
    
    @property
    def formatted_duration(self):
        """Get formatted duration for videos"""
        if self.duration:
            total_seconds = int(self.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        return "00:00"
    
    @property
    def formatted_file_size(self):
        """Get human-readable file size"""
        if self.file_size == 0:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    @property
    def is_for_all_business_categories(self):
        """Check if demo is available for all business categories"""
        return self.target_business_categories.count() == 0
    
    @property
    def is_for_all_business_subcategories(self):
        """Check if demo is available for all business subcategories"""
        return self.target_business_subcategories.count() == 0
    
    def is_available_for_business_category(self, category):
        """Check if demo is available for a specific business category"""
        if self.is_for_all_business_categories:
            return True
        if category:
            return self.target_business_categories.filter(id=category.id).exists()
        return False
    
    def is_available_for_business_subcategory(self, subcategory):
        """Check if demo is available for a specific business subcategory"""
        if self.is_for_all_business_subcategories:
            return True
        if subcategory:
            return self.target_business_subcategories.filter(id=subcategory.id).exists()
        return False
    
    def is_available_for_business(self, category=None, subcategory=None):
        """Check if demo is available for given business category/subcategory combination"""
        if self.is_for_all_business_categories and self.is_for_all_business_subcategories:
            return True
        
        category_match = self.is_available_for_business_category(category)
        subcategory_match = self.is_available_for_business_subcategory(subcategory)
        
        return category_match or subcategory_match
    
    @property
    def is_for_all_customers(self):
        return self.target_customers.count() == 0
    
    def can_customer_access(self, customer):
        if self.is_for_all_customers:
            return True
        return self.target_customers.filter(id=customer.id).exists()
    
    @property
    def primary_business_category(self):
        """Get the first business category for display purposes"""
        return self.target_business_categories.first()
    
    @property
    def business_categories_display(self):
        """Get comma-separated list of business categories"""
        categories = self.target_business_categories.all()
        if categories:
            return ", ".join([cat.name for cat in categories])
        return "All Categories"

class DemoView(models.Model):
    """Track demo views by users"""
    
    demo = models.ForeignKey(Demo, on_delete=models.CASCADE, related_name='demo_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demo_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    watch_duration = models.DurationField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'demo_views'
        verbose_name = 'Demo View'
        verbose_name_plural = 'Demo Views'
        unique_together = ['demo', 'user']
        ordering = ['-viewed_at']


class DemoLike(models.Model):
    """Track demo likes by users"""
    
    demo = models.ForeignKey(Demo, on_delete=models.CASCADE, related_name='demo_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demo_likes')
    liked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'demo_likes'
        verbose_name = 'Demo Like'
        verbose_name_plural = 'Demo Likes'
        unique_together = ['demo', 'user']
        ordering = ['-liked_at']


class DemoFeedback(models.Model):
    """User feedback on demos"""
    
    demo = models.ForeignKey(Demo, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demo_feedbacks')
    
    # Rating & Feedback
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, 
        blank=True,
        verbose_name="Rating (1-5)"
    )
    feedback_text = models.TextField(verbose_name="Feedback")
    
    # Status
    is_approved = models.BooleanField(default=False, verbose_name="Approved")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'demo_feedbacks'
        verbose_name = 'Demo Feedback'
        verbose_name_plural = 'Demo Feedbacks'
        unique_together = ['demo', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback by {self.user.full_name} on {self.demo.title}"


class TimeSlot(models.Model):
    """Available time slots for demo bookings"""
    
    SLOT_TYPES = [
        ('morning', 'Morning (9:30 AM - 1:00 PM)'),
        ('afternoon', 'Afternoon/Evening (2:00 PM - 7:00 PM)'),
    ]
    
    slot_type = models.CharField(max_length=10, choices=SLOT_TYPES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'time_slots'
        verbose_name = 'Time Slot'
        verbose_name_plural = 'Time Slots'
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.get_slot_type_display()}: {self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

class DemoRequest(models.Model):
    """User requests for live demo sessions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rescheduled', 'Rescheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('scheduling_conflict', 'Scheduling Conflict'),
        ('requirements_change', 'Change in Requirements'),
        ('found_alternative', 'Found Alternative Solution'),
        ('no_longer_interested', 'No Longer Interested'),
        ('other', 'Other Reasons'),
    ]
    
    # Request Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demo_requests')
    demo = models.ForeignKey(Demo, on_delete=models.CASCADE, related_name='demo_requests')
    
    # Business Category Fields
    business_category = models.ForeignKey(
        'accounts.BusinessCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demo_requests',
        verbose_name="Business Category"
    )
    business_subcategory = models.ForeignKey(
        'accounts.BusinessSubCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demo_requests',
        verbose_name="Business Subcategory"
    )
    country_region = models.CharField(
        max_length=50, 
        blank=True,
        null=True,
        default='IN',
        verbose_name="Country/Region"
    )
    
    # Scheduling
    requested_date = models.DateField(verbose_name="Requested Date")
    requested_time_slot = models.ForeignKey(
        TimeSlot, 
        on_delete=models.CASCADE,
        verbose_name="Requested Time Slot"
    )
    
    # Confirmed scheduling
    confirmed_date = models.DateField(null=True, blank=True, verbose_name="Confirmed Date")
    confirmed_time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='confirmed_requests',
        verbose_name="Confirmed Time Slot"
    )

    assigned_to = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_demo_requests',
        limit_choices_to={'is_staff': True, 'is_active': True},
        help_text='Employee assigned to handle this demo'
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the demo was assigned'
    )
    assigned_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_demos_by',
        help_text='Admin who assigned this demo'
    )
    
    # Additional Information
    notes = models.TextField(blank=True, verbose_name="Notes/Additional Details")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Postal/ZIP Code")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    timezone = models.CharField(max_length=50, blank=True, verbose_name="Timezone")
    
    # Geographic metadata
    is_international = models.BooleanField(default=False, verbose_name="International Customer")
    
    # Cancellation Information (NEW FIELDS)
    cancellation_reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASON_CHOICES,
        blank=True,
        null=True,
        verbose_name="Cancellation Reason"
    )
    cancellation_details = models.TextField(
        blank=True,
        null=True,
        verbose_name="Cancellation Details"
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Cancelled At"
    )
    
    # Admin Response
    admin_notes = models.TextField(blank=True, verbose_name="Admin Notes")
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_demo_requests',
        verbose_name="Handled By"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'demo_requests'
        verbose_name = 'Demo Request'
        verbose_name_plural = 'Demo Requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.demo.title} on {self.requested_date}"
    
    def clean(self):
        from django.utils import timezone
        
        # Check if requested date is not Sunday
        if self.requested_date and self.requested_date.weekday() == 6:
            raise ValidationError("Demo requests cannot be made for Sundays.")
        
        # Check if requested date is not in the past
        if self.requested_date and self.requested_date < timezone.now().date():
            raise ValidationError("Demo requests cannot be made for past dates.")
        
        # Validate subcategory belongs to category
        if self.business_subcategory and self.business_category:
            if self.business_subcategory.category != self.business_category:
                raise ValidationError(
                    'Selected subcategory does not belong to the selected category.'
                )
    
    @property
    def effective_date(self):
        return self.confirmed_date or self.requested_date
    
    @property 
    def effective_time_slot(self):
        return self.confirmed_time_slot or self.requested_time_slot
    
    @property
    def is_cancelled(self):
        """Check if request is cancelled"""
        return self.status == 'cancelled'
    
    @property
    def cancellation_summary(self):
        """Get formatted cancellation summary"""
        if not self.is_cancelled:
            return None
        
        summary = {
            'reason': self.get_cancellation_reason_display() if self.cancellation_reason else 'Not specified',
            'details': self.cancellation_details or 'No additional details',
            'cancelled_at': self.cancelled_at,
        }
        return summary
    
    def has_conflict_with_employee(self, employee):
        """
        Check if employee has another demo at the same time
        """
        if not self.requested_date or not self.requested_time_slot:
            return False, None
        
        conflicting_demos = DemoRequest.objects.filter(
            assigned_to=employee,
            requested_date=self.requested_date,
            requested_time_slot=self.requested_time_slot,
            status__in=['pending', 'confirmed']
        ).exclude(id=self.id)
        
        if conflicting_demos.exists():
            return True, conflicting_demos.first()
        return False, None
    

    # demos/models.py - UPDATED get_available_employees method

    @classmethod
    def get_available_employees(cls, requested_date, requested_time_slot):
        """
        Get list of employees available for given date and time slot
        
        ✅ FIXED: Now includes ALL staff members who have ANY demo-related permission
        """
        from accounts.models import CustomUser
        
        print(f"\n{'='*60}")
        print(f"🔍 Finding Available Employees")
        print(f"{'='*60}")
        print(f"📅 Date: {requested_date}")
        print(f"⏰ Time Slot: {requested_time_slot}")
        
        # Get all active staff members
        all_staff = CustomUser.objects.filter(
            is_staff=True,
            is_active=True
        ).order_by('first_name', 'last_name')
        
        print(f"👥 Total Active Staff: {all_staff.count()}")
        
        available = []
        
        for employee in all_staff:
            print(f"\n   Checking: {employee.get_full_name()} (ID: {employee.id})")
            print(f"   - Email: {employee.email}")
            print(f"   - Is Staff: {employee.is_staff}")
            print(f"   - Is Superuser: {employee.is_superuser}")
            
            # ✅ UPDATED: Include if employee has ANY of these permissions:
            # 1. Superuser (automatic)
            # 2. Has 'manage_demo_requests' permission
            # 3. Has 'view_demo_requests' permission  
            # 4. Has 'approve_demo_request' permission
            
            has_permission = False
            
            if employee.is_superuser:
                has_permission = True
                print(f"   ✓ Is Superuser - INCLUDED")
            elif employee.has_permission('manage_demo_requests'):
                has_permission = True
                print(f"   ✓ Has 'manage_demo_requests' - INCLUDED")
            elif employee.has_permission('view_demo_requests'):
                has_permission = True
                print(f"   ✓ Has 'view_demo_requests' - INCLUDED")
            elif employee.has_permission('approve_demo_request'):
                has_permission = True
                print(f"   ✓ Has 'approve_demo_request' - INCLUDED")
            else:
                print(f"   ✗ No demo permissions - EXCLUDED")
            
            if has_permission:
                # Check if employee has conflict at this time
                has_conflict = cls.objects.filter(
                    assigned_to=employee,
                    requested_date=requested_date,
                    requested_time_slot=requested_time_slot,
                    status__in=['pending', 'confirmed']
                ).exists()
                
                if has_conflict:
                    print(f"   ⚠️ Has scheduling conflict - EXCLUDED")
                else:
                    print(f"   ✓ Available - ADDED TO LIST")
                    available.append(employee)
        
        print(f"\n{'='*60}")
        print(f"✅ Found {len(available)} Available Employees:")
        for emp in available:
            print(f"   - {emp.get_full_name()} ({emp.email})")
        print(f"{'='*60}\n")
        
        return available
    