from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

def role_required(role):
    """
    Decorator para verificar se o utilizador tem o papel correto.
    Uso: @role_required('medico'), @role_required('paciente'), etc.
    """
    def check_role(user):
        if not user.is_authenticated:
            return False
        return user.role == role
    
    def decorator(view_func):
        decorated_view = user_passes_test(
            check_role,
            login_url='/login/'
        )(view_func)
        return decorated_view
    
    return decorator