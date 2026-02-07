"""
Middleware para configurar o database user correto baseado no role do utilizador
Coloca este ficheiro em: core/middleware.py (ou adiciona a um ficheiro middleware existente)
"""

from django.db import connection
from .db_router import db_router


class RoleBasedDatabaseMiddleware:
    """
    Middleware que:
    1. Define qual database user usar baseado no role do utilizador autenticado
    2. Configura o current_user_id no PostgreSQL para Row Level Security (RLS)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Configurar o router com o utilizador atual
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Define o role no router
            db_router.set_current_user(request.user)
            
            # Define o current_user_id para Row Level Security
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_current_user(%s)", 
                        [request.user.id_utilizador]
                    )
            except Exception as e:
                # Log do erro mas não quebra o request
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Erro ao configurar current_user para RLS: {e}")
        else:
            # User não autenticado - limpar
            db_router.set_current_user(None)
        
        response = self.get_response(request)
        
        return response


class DatabaseUserLoggingMiddleware:
    """
    Middleware opcional para debug - mostra qual database user está sendo usado
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Log qual user está sendo usado
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user")
                db_user = cursor.fetchone()[0]
                logger.info(
                    f"User: {request.user.email} (role: {request.user.role}) "
                    f"→ DB User: {db_user}"
                )
        
        response = self.get_response(request)
        return response
