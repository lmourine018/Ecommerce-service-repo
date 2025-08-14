# ecommerce_app/tests/conftest.py

import os
import sys
import django

# Get the absolute path to the project root (where manage.py is)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add project root to PYTHONPATH
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Ecommerce.settings")

# Setup Django
django.setup()
