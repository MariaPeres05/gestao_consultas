"""
Database Router para utilizar diferentes database users baseado no role do utilizador
Coloca este ficheiro em: core/db_router.py
"""

from django.conf import settings


class RoleBasedDatabaseRouter:
    """
    Router que seleciona a conexão de base de dados baseada no role do utilizador atual.
    
    Cada role usa uma database user diferente com permissões específicas:
    - paciente → app_paciente_user
    - medico → app_medico_user
    - enfermeiro → app_enfermeiro_user
    - admin → app_admin_user
    """
    
    def __init__(self):
        # Cache do utilizador atual por thread
        self._current_user = {}
    
    def _get_db_for_role(self, role):
        """Retorna o alias da base de dados para o role especificado"""
        role_db_mapping = {
            'paciente': 'paciente_db',
            'medico': 'medico_db',
            'enfermeiro': 'enfermeiro_db',
            'admin': 'admin_db',
        }
        return role_db_mapping.get(role, 'default')
    
    def _get_current_user_role(self):
        """Obtém o role do utilizador atual da thread local"""
        from threading import current_thread
        thread_id = current_thread().ident
        return self._current_user.get(thread_id)
    
    def set_current_user(self, user):
        """Define o utilizador atual para a thread (chamado pelo middleware)"""
        from threading import current_thread
        thread_id = current_thread().ident
        if user and user.is_authenticated:
            self._current_user[thread_id] = user.role
        else:
            self._current_user.pop(thread_id, None)
    
    def db_for_read(self, model, **hints):
        """
        Seleciona a base de dados para operações de leitura baseado no role do user
        """
        role = self._get_current_user_role()
        if role:
            return self._get_db_for_role(role)
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Seleciona a base de dados para operações de escrita baseado no role do user
        """
        role = self._get_current_user_role()
        if role:
            return self._get_db_for_role(role)
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relações entre objetos se estiverem na mesma base de dados
        """
        # Todas as databases apontam para o mesmo PostgreSQL, apenas users diferentes
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Apenas permite migrations na database 'default' com user admin
        """
        return db == 'default'


# Instância global do router (necessário para o middleware)
db_router = RoleBasedDatabaseRouter()
