# accounts/models.py (COMPLETE VERSION WITH RBAC)
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import re

def validate_business_email(email):
    """Validate that email is not from blocked personal domains"""
    blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [
        'yahoo.com', 'hotmail.com', 'outlook.com', 
        'ymail.com', 'aol.com', 'icloud.com', 'live.com',
        'gmail.com',
    ])
    
    domain = email.split('@')[1].lower()
    if domain in blocked_domains:
        raise ValidationError(
            f'Business email required. Personal email domains ({domain}) are not allowed.'
        )


def validate_employee_id_format(value):
    """
    Validate Employee ID format: EMP followed by exactly 5 digits
    Example: EMP00001, EMP12345
    """
    if value:  # Only validate if value exists
        pattern = r'^EMP\d{5}$'
        if not re.match(pattern, value):
            raise ValidationError(
                'Employee ID must be in format EMP00000 (EMP followed by 5 digits). Example: EMP00001'
            )

# =============================================
# NEW: RBAC MODELS
# =============================================

class Permission(models.Model):
    """Individual permissions for RBAC system"""
    
    MODULE_CHOICES = [
        ('customers', 'Customer Management'),
        ('demos', 'Demo Management'),
        ('demo_requests', 'Demo Requests'),
        ('enquiries', 'Enquiries'),
        ('notifications', 'Notifications'),
        ('business_categories', 'Business Categories'),
        ('settings', 'Settings'),
        ('analytics', 'Analytics & Reports'),
        ('system', 'System Administration'),
    ]
    
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Permission Name"
    )
    codename = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Code Name",
        help_text="e.g., view_customers, edit_demos"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    module = models.CharField(
        max_length=50, 
        choices=MODULE_CHOICES,
        verbose_name="Module"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rbac_permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['module', 'name']
    
    def __str__(self):
        return f"{self.get_module_display()} - {self.name}"


class Role(models.Model):
    """User roles with assigned permissions"""
    
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Role Name"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name='roles',
        blank=True,
        verbose_name="Permissions"
    )
    is_system_role = models.BooleanField(
        default=False,
        verbose_name="System Role",
        help_text="System roles cannot be deleted (Super Admin, Admin, etc.)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    priority = models.IntegerField(
        default=0,
        verbose_name="Priority",
        help_text="Higher priority = more access (used for hierarchy)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rbac_roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return self.name
    
    def get_permission_codenames(self):
        """Get list of permission codenames for this role"""
        return list(
            self.permissions.filter(is_active=True).values_list('codename', flat=True)
        )
    
    def get_users_count(self):
        """Get count of users with this role"""
        return self.users.count()


# =============================================
# EXISTING MODELS (WITH RBAC INTEGRATION)
# =============================================

class BusinessCategory(models.Model):
    """Business categories for customer classification"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    description = models.TextField(blank=True, verbose_name="Description")
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="CSS icon class or emoji",
        verbose_name="Icon"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Sort Order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'business_categories'
        verbose_name = 'Business Category'
        verbose_name_plural = 'Business Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class BusinessSubCategory(models.Model):
    """Business subcategories under main categories"""
    
    category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Parent Category"
    )
    name = models.CharField(max_length=100, verbose_name="Subcategory Name")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Sort Order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'business_subcategories'
        verbose_name = 'Business Subcategory'
        verbose_name_plural = 'Business Subcategories'
        ordering = ['sort_order', 'name']
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.verified and timezone.now() < self.expires_at
    
    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))
    
    class Meta:
        ordering = ['-created_at']


class CustomUser(AbstractUser):
    """Enhanced User Model with Employee Management & RBAC"""
    
    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(max_length=50, verbose_name="Last Name")
    email = models.EmailField(unique=True, validators=[validate_business_email], verbose_name="Office Email")
    
    # Contact Information
    phone_validator = RegexValidator(regex=r'^\d{10}$', message="Phone number must be exactly 10 digits.")
    mobile = models.CharField(validators=[phone_validator], max_length=10, verbose_name="Contact Number")
    
    COUNTRY_CHOICES = [
        ('+93', '🇦🇫 Afghanistan (+93)'),
        ('+355', '🇦🇱 Albania (+355)'),
        ('+213', '🇩🇿 Algeria (+213)'),
        ('+1', '🇺🇸 American Samoa (+1)'),
        ('+376', '🇦🇩 Andorra (+376)'),
        ('+244', '🇦🇴 Angola (+244)'),
        ('+1', '🇦🇮 Anguilla (+1)'),
        ('+1', '🇦🇬 Antigua and Barbuda (+1)'),
        ('+54', '🇦🇷 Argentina (+54)'),
        ('+374', '🇦🇲 Armenia (+374)'),
        ('+297', '🇦🇼 Aruba (+297)'),
        ('+61', '🇦🇺 Australia (+61)'),
        ('+43', '🇦🇹 Austria (+43)'),
        ('+994', '🇦🇿 Azerbaijan (+994)'),
        ('+1', '🇧🇸 Bahamas (+1)'),
        ('+973', '🇧🇭 Bahrain (+973)'),
        ('+880', '🇧🇩 Bangladesh (+880)'),
        ('+1', '🇧🇧 Barbados (+1)'),
        ('+375', '🇧🇾 Belarus (+375)'),
        ('+32', '🇧🇪 Belgium (+32)'),
        ('+501', '🇧🇿 Belize (+501)'),
        ('+229', '🇧🇯 Benin (+229)'),
        ('+1', '🇧🇲 Bermuda (+1)'),
        ('+975', '🇧🇹 Bhutan (+975)'),
        ('+591', '🇧🇴 Bolivia (+591)'),
        ('+387', '🇧🇦 Bosnia and Herzegovina (+387)'),
        ('+267', '🇧🇼 Botswana (+267)'),
        ('+55', '🇧🇷 Brazil (+55)'),
        ('+1', '🇻🇬 British Virgin Islands (+1)'),
        ('+673', '🇧🇳 Brunei (+673)'),
        ('+359', '🇧🇬 Bulgaria (+359)'),
        ('+226', '🇧🇫 Burkina Faso (+226)'),
        ('+257', '🇧🇮 Burundi (+257)'),
        ('+855', '🇰🇭 Cambodia (+855)'),
        ('+237', '🇨🇲 Cameroon (+237)'),
        ('+1', '🇨🇦 Canada (+1)'),
        ('+238', '🇨🇻 Cape Verde (+238)'),
        ('+1', '🇰🇾 Cayman Islands (+1)'),
        ('+236', '🇨🇫 Central African Republic (+236)'),
        ('+235', '🇹🇩 Chad (+235)'),
        ('+56', '🇨🇱 Chile (+56)'),
        ('+86', '🇨🇳 China (+86)'),
        ('+57', '🇨🇴 Colombia (+57)'),
        ('+269', '🇰🇲 Comoros (+269)'),
        ('+242', '🇨🇬 Congo (+242)'),
        ('+682', '🇨🇰 Cook Islands (+682)'),
        ('+506', '🇨🇷 Costa Rica (+506)'),
        ('+225', '🇨🇮 Côte d\'Ivoire (+225)'),
        ('+385', '🇭🇷 Croatia (+385)'),
        ('+53', '🇨🇺 Cuba (+53)'),
        ('+357', '🇨🇾 Cyprus (+357)'),
        ('+420', '🇨🇿 Czech Republic (+420)'),
        ('+243', '🇨🇩 Democratic Republic of Congo (+243)'),
        ('+45', '🇩🇰 Denmark (+45)'),
        ('+253', '🇩🇯 Djibouti (+253)'),
        ('+1', '🇩🇲 Dominica (+1)'),
        ('+1', '🇩🇴 Dominican Republic (+1)'),
        ('+593', '🇪🇨 Ecuador (+593)'),
        ('+20', '🇪🇬 Egypt (+20)'),
        ('+503', '🇸🇻 El Salvador (+503)'),
        ('+240', '🇬🇶 Equatorial Guinea (+240)'),
        ('+291', '🇪🇷 Eritrea (+291)'),
        ('+372', '🇪🇪 Estonia (+372)'),
        ('+251', '🇪🇹 Ethiopia (+251)'),
        ('+500', '🇫🇰 Falkland Islands (+500)'),
        ('+298', '🇫🇴 Faroe Islands (+298)'),
        ('+679', '🇫🇯 Fiji (+679)'),
        ('+358', '🇫🇮 Finland (+358)'),
        ('+33', '🇫🇷 France (+33)'),
        ('+594', '🇬🇫 French Guiana (+594)'),
        ('+689', '🇵🇫 French Polynesia (+689)'),
        ('+241', '🇬🇦 Gabon (+241)'),
        ('+220', '🇬🇲 Gambia (+220)'),
        ('+995', '🇬🇪 Georgia (+995)'),
        ('+49', '🇩🇪 Germany (+49)'),
        ('+233', '🇬🇭 Ghana (+233)'),
        ('+350', '🇬🇮 Gibraltar (+350)'),
        ('+30', '🇬🇷 Greece (+30)'),
        ('+299', '🇬🇱 Greenland (+299)'),
        ('+1', '🇬🇩 Grenada (+1)'),
        ('+590', '🇬🇵 Guadeloupe (+590)'),
        ('+1', '🇬🇺 Guam (+1)'),
        ('+502', '🇬🇹 Guatemala (+502)'),
        ('+224', '🇬🇳 Guinea (+224)'),
        ('+245', '🇬🇼 Guinea-Bissau (+245)'),
        ('+592', '🇬🇾 Guyana (+592)'),
        ('+509', '🇭🇹 Haiti (+509)'),
        ('+504', '🇭🇳 Honduras (+504)'),
        ('+852', '🇭🇰 Hong Kong (+852)'),
        ('+36', '🇭🇺 Hungary (+36)'),
        ('+354', '🇮🇸 Iceland (+354)'),
        ('+91', '🇮🇳 India (+91)'),
        ('+62', '🇮🇩 Indonesia (+62)'),
        ('+98', '🇮🇷 Iran (+98)'),
        ('+964', '🇮🇶 Iraq (+964)'),
        ('+353', '🇮🇪 Ireland (+353)'),
        ('+972', '🇮🇱 Israel (+972)'),
        ('+39', '🇮🇹 Italy (+39)'),
        ('+1', '🇯🇲 Jamaica (+1)'),
        ('+81', '🇯🇵 Japan (+81)'),
        ('+962', '🇯🇴 Jordan (+962)'),
        ('+7', '🇰🇿 Kazakhstan (+7)'),
        ('+254', '🇰🇪 Kenya (+254)'),
        ('+686', '🇰🇮 Kiribati (+686)'),
        ('+965', '🇰🇼 Kuwait (+965)'),
        ('+996', '🇰🇬 Kyrgyzstan (+996)'),
        ('+856', '🇱🇦 Laos (+856)'),
        ('+371', '🇱🇻 Latvia (+371)'),
        ('+961', '🇱🇧 Lebanon (+961)'),
        ('+266', '🇱🇸 Lesotho (+266)'),
        ('+231', '🇱🇷 Liberia (+231)'),
        ('+218', '🇱🇾 Libya (+218)'),
        ('+423', '🇱🇮 Liechtenstein (+423)'),
        ('+370', '🇱🇹 Lithuania (+370)'),
        ('+352', '🇱🇺 Luxembourg (+352)'),
        ('+853', '🇲🇴 Macao (+853)'),
        ('+389', '🇲🇰 Macedonia (+389)'),
        ('+261', '🇲🇬 Madagascar (+261)'),
        ('+265', '🇲🇼 Malawi (+265)'),
        ('+60', '🇲🇾 Malaysia (+60)'),
        ('+960', '🇲🇻 Maldives (+960)'),
        ('+223', '🇲🇱 Mali (+223)'),
        ('+356', '🇲🇹 Malta (+356)'),
        ('+692', '🇲🇭 Marshall Islands (+692)'),
        ('+596', '🇲🇶 Martinique (+596)'),
        ('+222', '🇲🇷 Mauritania (+222)'),
        ('+230', '🇲🇺 Mauritius (+230)'),
        ('+52', '🇲🇽 Mexico (+52)'),
        ('+691', '🇫🇲 Micronesia (+691)'),
        ('+373', '🇲🇩 Moldova (+373)'),
        ('+377', '🇲🇨 Monaco (+377)'),
        ('+976', '🇲🇳 Mongolia (+976)'),
        ('+382', '🇲🇪 Montenegro (+382)'),
        ('+1', '🇲🇸 Montserrat (+1)'),
        ('+212', '🇲🇦 Morocco (+212)'),
        ('+258', '🇲🇿 Mozambique (+258)'),
        ('+95', '🇲🇲 Myanmar (+95)'),
        ('+264', '🇳🇦 Namibia (+264)'),
        ('+674', '🇳🇷 Nauru (+674)'),
        ('+977', '🇳🇵 Nepal (+977)'),
        ('+31', '🇳🇱 Netherlands (+31)'),
        ('+687', '🇳🇨 New Caledonia (+687)'),
        ('+64', '🇳🇿 New Zealand (+64)'),
        ('+505', '🇳🇮 Nicaragua (+505)'),
        ('+227', '🇳🇪 Niger (+227)'),
        ('+234', '🇳🇬 Nigeria (+234)'),
        ('+683', '🇳🇺 Niue (+683)'),
        ('+672', '🇳🇫 Norfolk Island (+672)'),
        ('+850', '🇰🇵 North Korea (+850)'),
        ('+1', '🇲🇵 Northern Mariana Islands (+1)'),
        ('+47', '🇳🇴 Norway (+47)'),
        ('+968', '🇴🇲 Oman (+968)'),
        ('+92', '🇵🇰 Pakistan (+92)'),
        ('+680', '🇵🇼 Palau (+680)'),
        ('+970', '🇵🇸 Palestine (+970)'),
        ('+507', '🇵🇦 Panama (+507)'),
        ('+675', '🇵🇬 Papua New Guinea (+675)'),
        ('+595', '🇵🇾 Paraguay (+595)'),
        ('+51', '🇵🇪 Peru (+51)'),
        ('+63', '🇵🇭 Philippines (+63)'),
        ('+48', '🇵🇱 Poland (+48)'),
        ('+351', '🇵🇹 Portugal (+351)'),
        ('+1', '🇵🇷 Puerto Rico (+1)'),
        ('+974', '🇶🇦 Qatar (+974)'),
        ('+262', '🇷🇪 Réunion (+262)'),
        ('+40', '🇷🇴 Romania (+40)'),
        ('+7', '🇷🇺 Russia (+7)'),
        ('+250', '🇷🇼 Rwanda (+250)'),
        ('+290', '🇸🇭 Saint Helena (+290)'),
        ('+1', '🇰🇳 Saint Kitts and Nevis (+1)'),
        ('+1', '🇱🇨 Saint Lucia (+1)'),
        ('+508', '🇵🇲 Saint Pierre and Miquelon (+508)'),
        ('+1', '🇻🇨 Saint Vincent and the Grenadines (+1)'),
        ('+685', '🇼🇸 Samoa (+685)'),
        ('+378', '🇸🇲 San Marino (+378)'),
        ('+239', '🇸🇹 São Tomé and Príncipe (+239)'),
        ('+966', '🇸🇦 Saudi Arabia (+966)'),
        ('+221', '🇸🇳 Senegal (+221)'),
        ('+381', '🇷🇸 Serbia (+381)'),
        ('+248', '🇸🇨 Seychelles (+248)'),
        ('+232', '🇸🇱 Sierra Leone (+232)'),
        ('+65', '🇸🇬 Singapore (+65)'),
        ('+421', '🇸🇰 Slovakia (+421)'),
        ('+386', '🇸🇮 Slovenia (+386)'),
        ('+677', '🇸🇧 Solomon Islands (+677)'),
        ('+252', '🇸🇴 Somalia (+252)'),
        ('+27', '🇿🇦 South Africa (+27)'),
        ('+82', '🇰🇷 South Korea (+82)'),
        ('+211', '🇸🇸 South Sudan (+211)'),
        ('+34', '🇪🇸 Spain (+34)'),
        ('+94', '🇱🇰 Sri Lanka (+94)'),
        ('+249', '🇸🇩 Sudan (+249)'),
        ('+597', '🇸🇷 Suriname (+597)'),
        ('+268', '🇸🇿 Swaziland (+268)'),
        ('+46', '🇸🇪 Sweden (+46)'),
        ('+41', '🇨🇭 Switzerland (+41)'),
        ('+963', '🇸🇾 Syria (+963)'),
        ('+886', '🇹🇼 Taiwan (+886)'),
        ('+992', '🇹🇯 Tajikistan (+992)'),
        ('+255', '🇹🇿 Tanzania (+255)'),
        ('+66', '🇹🇭 Thailand (+66)'),
        ('+670', '🇹🇱 Timor-Leste (+670)'),
        ('+228', '🇹🇬 Togo (+228)'),
        ('+690', '🇹🇰 Tokelau (+690)'),
        ('+676', '🇹🇴 Tonga (+676)'),
        ('+1', '🇹🇹 Trinidad and Tobago (+1)'),
        ('+216', '🇹🇳 Tunisia (+216)'),
        ('+90', '🇹🇷 Turkey (+90)'),
        ('+993', '🇹🇲 Turkmenistan (+993)'),
        ('+1', '🇹🇨 Turks and Caicos Islands (+1)'),
        ('+688', '🇹🇻 Tuvalu (+688)'),
        ('+256', '🇺🇬 Uganda (+256)'),
        ('+380', '🇺🇦 Ukraine (+380)'),
        ('+971', '🇦🇪 United Arab Emirates (+971)'),
        ('+44', '🇬🇧 United Kingdom (+44)'),
        ('+1', '🇺🇸 United States (+1)'),
        ('+598', '🇺🇾 Uruguay (+598)'),
        ('+998', '🇺🇿 Uzbekistan (+998)'),
        ('+678', '🇻🇺 Vanuatu (+678)'),
        ('+379', '🇻🇦 Vatican City (+379)'),
        ('+58', '🇻🇪 Venezuela (+58)'),
        ('+84', '🇻🇳 Vietnam (+84)'),
        ('+1', '🇻🇮 Virgin Islands (US) (+1)'),
        ('+681', '🇼🇫 Wallis and Futuna (+681)'),
        ('+212', '🇪🇭 Western Sahara (+212)'),
        ('+967', '🇾🇪 Yemen (+967)'),
        ('+260', '🇿🇲 Zambia (+260)'),
        ('+263', '🇿🇼 Zimbabwe (+263)'),
    ]
    country_code = models.CharField(
        max_length=50, 
        choices=COUNTRY_CHOICES,
        default='+91',
        verbose_name="Country Code"
    )
    # ==========================================
    # EMPLOYEE IDENTIFICATION
    # ==========================================
    employee_id = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        unique=True,
        validators=[validate_employee_id_format],
        verbose_name="Employee ID",
        help_text="Unique employee identifier (e.g., EMP001)"
    )
    
    # ==========================================
    # SYSTEM INFORMATION (Auto-captured from backend)
    # ==========================================
    system_mac_address = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        verbose_name="System MAC Address",
        help_text="Auto-captured from user's system (Format: XX:XX:XX:XX:XX:XX)"
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="Auto-captured on login"
    )
    
    # ==========================================
    # USER TYPE & ROLE
    # ==========================================
    USER_TYPE_CHOICES = [
        ('employee', 'Employee'),
        ('customer', 'Customer'),
    ]
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='customer',
        verbose_name="User Type"
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Role",
        help_text="Admin, Sales, Manager, etc."
    )
    
    additional_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='users_with_permission',
        verbose_name="Additional Permissions"
    )
    
    # ==========================================
    # BUSINESS INFORMATION
    # ==========================================
    job_title = models.CharField(max_length=100, blank=True, verbose_name="Job Title")
    organization = models.CharField(max_length=200, blank=True, verbose_name="Organization")
    business_category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name="Category"
    )
    business_subcategory = models.ForeignKey(
        BusinessSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name="Subcategory"
    )
    
    # ==========================================
    # STATUS & VERIFICATION
    # ==========================================
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status",
        help_text="Inactive users cannot login to the system"
    )
    
    is_email_verified = models.BooleanField(default=False, verbose_name="Email Verified")
    is_approved = models.BooleanField(default=False, verbose_name="Account Approved")
    
    # ==========================================
    # SIGNUP & REFERRAL (For Customers)
    # ==========================================
    REFERRAL_CHOICES = [
        ('referral', 'Referral from colleague'),
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('google', 'Google Search'),
        ('other', 'Other'),
    ]
    referral_source = models.CharField(max_length=20, choices=REFERRAL_CHOICES, blank=True, verbose_name="Referral Source")
    referral_message = models.TextField(blank=True, verbose_name="Additional Message")
    
    # ==========================================
    # SECURITY TOKENS
    # ==========================================
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_expires = models.DateTimeField(blank=True, null=True)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    # ==========================================
    # TIMESTAMPS
    # ==========================================
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    # ==========================================
    # META & AUTH CONFIG
    # ==========================================
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'mobile']
    
    class Meta:
        db_table = 'custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee_id']),  # ✅ Index for faster queries
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.employee_id:
            return f"{self.full_name} ({self.employee_id})"
        return f"{self.full_name} ({self.email})"
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_mobile(self):
        return f"{self.country_code}{self.mobile}"
    
    @property
    def is_employee(self):
        """Check if user is an employee"""
        return self.user_type == 'employee' and self.is_staff
    
    @property
    def is_profile_complete(self):
        required = [self.first_name, self.last_name, self.email, self.mobile]
        if self.user_type == 'employee':
            required.extend([self.employee_id, self.role])
        else:
            required.extend([self.job_title, self.organization, self.business_category])
        return all(required)
    
    @property
    def is_indian_customer(self):
        return self.country_code == '+91'
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """
        Model-level validation
        Called before save() when using forms or admin
        """
        super().clean()
        
        #Validate Employee ID format if provided
        if self.employee_id:
            # Convert to uppercase
            self.employee_id = self.employee_id.upper()
            
            # Validate format
            pattern = r'^EMP\d{5}$'
            if not re.match(pattern, self.employee_id):
                raise ValidationError({
                    'employee_id': 'Employee ID must be in format EMP00000 (EMP followed by 5 digits)'
                })
        # Customers cannot have high-priority roles
        if self.user_type == 'customer' and self.role:
            if self.role.priority >= 60:  # Manager level and above
                raise ValidationError({
                    'role': 'Customers cannot be assigned admin/manager roles. Please select a customer-appropriate role or change user type to Employee.'
                })
        
        # Employees should have roles
        if self.user_type == 'employee' and not self.role:
            raise ValidationError({
                'role': 'Employees must be assigned a role.'
            })
    # ==========================================
    # RBAC METHODS
    # ==========================================
    def get_all_permissions(self):
        """Get all permissions from role"""
        if not self.role:
            return set()
        
        # ✅ FIXED: Use codename
        return set(
            self.role.permissions.filter(is_active=True)
            .values_list('codename', flat=True)  # ✅ Database field
        )
    
    def has_permission(self, permission_code):
        """Check if user has specific permission"""
        if self.is_superuser:
            return True
        
        if not self.role:
            return False
        
        # ✅ FIXED: Use codename
        return self.role.permissions.filter(
            codename=permission_code,  # ✅ Database field
            is_active=True
        ).exists()

    def get_permissions_by_module(self):
        """Get permissions grouped by module"""
        permissions = self.get_all_permissions()
        grouped = {}
        for perm in permissions:
            if perm.module not in grouped:
                grouped[perm.module] = []
            grouped[perm.module].append(perm.codename)
        return grouped

    def save(self, *args, **kwargs):
        """
        Override save method to ensure data consistency
        """
        # ✅ Convert employee_id to uppercase before saving
        if self.employee_id:
            self.employee_id = self.employee_id.upper()
        
        # ✅ Ensure employees have is_staff=True
        if self.user_type == 'employee':
            self.is_staff = True
        
        super().save(*args, **kwargs)