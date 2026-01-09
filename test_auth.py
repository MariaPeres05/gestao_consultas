import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_consultas.settings')
django.setup()

from core.models import Utilizador
from django.contrib.auth import authenticate

# Check if user exists
user = Utilizador.objects.filter(email='admin@medipulse.pt').first()

if user:
    print(f"✅ User found: {user.email}")
    print(f"   Name: {user.nome}")
    print(f"   Role: {user.role}")
    print(f"   Has password: {bool(user.password)}")
    print(f"   Password field: {user.password[:60]}...")
    print(f"   Is staff: {user.is_staff}")
    print(f"   Is active: {user.is_active}")
    print()
    
    # Test password check directly
    test_password = "admin123"  # Change this to the password you used
    print(f"Testing password: '{test_password}'")
    result = user.check_password(test_password)
    print(f"   check_password result: {result}")
    print()
    
    # Test authentication
    print("Testing authentication...")
    auth_user = authenticate(None, email='admin@medipulse.pt', password=test_password)
    if auth_user:
        print(f"   ✅ Authentication successful: {auth_user.email}")
    else:
        print(f"   ❌ Authentication failed")
else:
    print("❌ User not found")
