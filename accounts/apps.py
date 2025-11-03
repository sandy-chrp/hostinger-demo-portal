from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'User Management & Authentication'
    
    def ready(self):
        """
        Import signals when Django starts
        
        This ensures that signal handlers are registered
        and will be triggered when appropriate events occur
        """
        try:
            import accounts.signals  # noqa
            print("✅ Accounts signals loaded successfully")
        except ImportError as e:
            print(f"⚠️ Failed to load accounts signals: {e}")