#!/usr/bin/env python
"""Diagnostic script to check project setup."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PFE.settings')
django.setup()

print("=" * 60)
print("PFEFLIX PROJECT DIAGNOSTIC")
print("=" * 60)

# 1. Check imports
print("\n1. Checking imports...")
try:
    from django.conf import settings
    print("   ✓ Django settings loaded")
except Exception as e:
    print(f"   ✗ Django settings error: {e}")
    sys.exit(1)

try:
    from core.models import Content, UserPreference, Rating
    print("   ✓ Core models imported")
except Exception as e:
    print(f"   ✗ Core models error: {e}")
    sys.exit(1)

# 2. Check database connection
print("\n2. Checking database connection...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("   ✓ Database connection successful")
except Exception as e:
    print(f"   ✗ Database connection failed: {e}")
    print(f"   Using: {settings.DATABASES['default']}")

# 3. Check Content table
print("\n3. Checking Content table...")
try:
    count = Content.objects.count()
    print(f"   ✓ Content table exists ({count} items)")
except Exception as e:
    print(f"   ✗ Content table error: {e}")

# 4. Test search_people logic
print("\n4. Testing search_people logic...")
try:
    # Simulate a search
    query = "test"
    actor_qs = Content.objects.filter(cast__icontains=query)
    director_qs = Content.objects.filter(director__icontains=query)
    
    actor_ids = set(actor_qs.values_list('id', flat=True))
    director_ids = set(director_qs.values_list('id', flat=True))
    
    combined_ids = list(director_ids) + [i for i in actor_ids if i not in director_ids]
    
    if combined_ids:
        content_dict = {item.id: item for item in Content.objects.filter(id__in=combined_ids)}
        results = [content_dict[pk] for pk in combined_ids if pk in content_dict][:60]
        print(f"   ✓ Search logic works ({len(results)} results for 'test')")
    else:
        print("   ℹ Search logic works (no results for 'test')")
except Exception as e:
    print(f"   ✗ Search logic error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
