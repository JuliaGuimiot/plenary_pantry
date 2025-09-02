"""
Test settings for plenary_pantry project.
This file extends the main settings but overrides the database to use SQLite for testing.
"""

from .settings import *

# Add core app to INSTALLED_APPS for testing
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'django_extensions',
    
    # Custom apps
    'core',
    'recipe_ingestion',
]

# Use in-memory SQLite database for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use console email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}

# Use a simple secret key for testing
SECRET_KEY = 'test-secret-key-for-testing-only'

# Disable debug mode for tests
DEBUG = False

# Use a simple cache backend for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
