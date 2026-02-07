import os
from django.db import connection
from django.contrib.auth import get_user_model

class DatabaseRoleMiddleware:
    """
    Middleware que altera a conexão da base de dados baseado no role do user autenticado.
    
    Fluxo:
    1. User faz login no Django (autenticação normal)
    2. Middleware detecta o role do user (paciente, medico, enfermeiro, admin)
    3. Fecha a conexão atual do base de dados
    4. Reconecta usando as credenciais do role apropriado
    5. Todas as queries subsequentes usam as permissões daquele role
    """
    
    ROLE_DB_MAPPING = {
        'paciente': {
            'USER': 'app_paciente_user',
            'PASSWORD': os.getenv('APP_PACIENTE_PASSWORD', 'w6b@AA5V#A4MhD!XtihLu!paER'),
        },
        'medico': {
            'USER': 'app_medico_user',
            'PASSWORD': os.getenv('APP_MEDICO_PASSWORD', 'D&VDBV4rae$L7R*wZ&ut72Jue&'),
        },
        'enfermeiro': {
            'USER': 'app_enfermeiro_user',
            'PASSWORD': os.getenv('APP_ENFERMEIRO_PASSWORD', '5Pb3Qb&MN*J8U&cLckHu5ozsSC'),
        },
        'admin': {
            'USER': 'app_admin_user',
            'PASSWORD': os.getenv('APP_ADMIN_PASSWORD', '7V4&RR^C9cRrg*Sk$ahk7kjGeC'),
        },
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Armazenar credenciais padrão (admin) para restaurar depois
        self.default_user = None
        self.default_password = None
    
    def __call__(self, request):
        """
        Executado para cada request.
        """
        # Armazenar credenciais padrão na primeira execução
        if self.default_user is None:
            self.default_user = connection.settings_dict.get('USER')
            self.default_password = connection.settings_dict.get('PASSWORD')
        
        # Verificar se o user está autenticado
        if request.user.is_authenticated:
            # Obter o role do user
            user_role = getattr(request.user, 'role', None)
            
            if user_role and user_role in self.ROLE_DB_MAPPING:
                # Obter as credenciais do role correspondente
                db_credentials = self.ROLE_DB_MAPPING[user_role]
                
                # Verificar se precisa trocar a conexão
                current_user = connection.settings_dict.get('USER')
                target_user = db_credentials['USER']
                
                if current_user != target_user:
                    # Fechar conexão atual
                    connection.close()
                    
                    # Atualizar credenciais da conexão
                    connection.settings_dict['USER'] = db_credentials['USER']
                    connection.settings_dict['PASSWORD'] = db_credentials['PASSWORD']
                    
                    # Log para debug (opcional)
                    if hasattr(request, 'session'):
                        request.session['_db_role'] = user_role
        
        # Processar o request
        response = self.get_response(request)
        
        # Restaurar conexão admin após processar a resposta
        # Isso garante que operações como salvar sessão usem credenciais corretas
        if connection.settings_dict.get('USER') != self.default_user:
            connection.close()
            connection.settings_dict['USER'] = self.default_user
            connection.settings_dict['PASSWORD'] = self.default_password
        
        return response
    
    def process_exception(self, request, exception):
        """
        Captura erros de permissão do PostgreSQL para melhor debugging.
        """
        if 'permission denied' in str(exception).lower():
            # Log do erro de permissão
            user = request.user if request.user.is_authenticated else 'Anonymous'
            role = getattr(request.user, 'role', 'N/A') if request.user.is_authenticated else 'N/A'
            
            print(f"⚠️  ERRO DE PERMISSÃO NO BANCO DE DADOS")
            print(f"   user: {user}")
            print(f"   Role: {role}")
            print(f"   Erro: {exception}")
        
        # Deixar Django lidar com a exceção normalmente
        return None


class SetPostgreSQLUserContextMiddleware:
    """
    Middleware alternativo/complementar que usa SET ROLE para alternar users.
    
    Este approach mantém uma única conexão mas alterna o role usando o comando PostgreSQL SET ROLE.
    Mais leve que fechar/abrir conexões, mas requer que o user padrão tenha permissão
    para assumir os outros roles.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            user_role = getattr(request.user, 'role', None)
            
            if user_role:
                role_mapping = {
                    'paciente': 'app_paciente_user',
                    'medico': 'app_medico_user',
                    'enfermeiro': 'app_enfermeiro_user',
                    'admin': 'app_admin_user',
                }
                
                pg_role = role_mapping.get(user_role)
                
                if pg_role:
                    try:
                        with connection.cursor() as cursor:
                            # Alternar para o role apropriado
                            cursor.execute(f"SET ROLE {pg_role}")
                    except Exception as e:
                        print(f"Erro ao definir role PostgreSQL: {e}")
        
        response = self.get_response(request)
        
        # Reset role para padrão após o request (opcional)
        if request.user.is_authenticated and hasattr(request.user, 'role'):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("RESET ROLE")
            except:
                pass
        
        return response
