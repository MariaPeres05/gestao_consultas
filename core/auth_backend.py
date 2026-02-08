from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.db import connection


class UtilizadorFromDB:
    """User object created from SQL query results"""
    def __init__(self, row):
        self.pk = row[0]
        self.id_utilizador = row[0]
        self.nome = row[1]
        self.email = row[2]
        self.password = row[3]
        self.telefone = row[4]
        self.n_utente = row[5]
        self.role = row[6]
        self.data_registo = row[7]
        self.ativo = row[8]
        self.email_verified = row[9]
        self.last_login = row[10]
        self.is_superuser = row[11] if len(row) > 11 else False
        self.backend = 'core.auth_backend.UtilizadorBackend'
        
        # Django compatibility attributes
        self.is_active = self.ativo
        self.is_staff = self.role in ['admin', 'medico', 'enfermeiro']
        self.is_authenticated = True
        self.is_anonymous = False
    
    def __str__(self):
        return self.email
    
    def get_username(self):
        return self.email
    
    def __getstate__(self):
        """For session serialization"""
        return {
            'pk': self.pk,
            'email': self.email,
            'backend': self.backend
        }
    
    def __setstate__(self, state):
        """For session deserialization"""
        self.pk = state['pk']
        self.email = state['email']
        self.backend = state.get('backend', 'core.auth_backend.UtilizadorBackend')


class UtilizadorBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        if not email or not password:
            return None
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM obter_utilizador_completo_por_email(%s)",
                [email]
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            user = UtilizadorFromDB(row)
            
            if not user.ativo:
                return None
            
            # Use Django's password checking (pbkdf2_sha256)
            if check_password(password, user.password):
                return user
        
        return None

    def get_user(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM obter_utilizador_completo_por_pk(%s)",
                [user_id]
            )
            row = cursor.fetchone()
            
            if row:
                return UtilizadorFromDB(row)
        
        return None
