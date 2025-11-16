from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Autenticação - URLs corretas para o Django
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/registro/', views.registro_view, name='registro'),
    
    # URLs do dashboard - versões curtas
    path('marcar-consulta/', views.marcar_consulta, name='marcar_consulta'),
    path('minhas-consultas/', views.listar_consultas, name='listar_consultas'),
    path('minhas-receitas/', views.listar_receitas, name='listar_receitas'),
    path('minhas-faturas/', views.listar_faturas, name='listar_faturas'),
    path('agenda/', views.agenda_medica, name='agenda_medica'),
    path('api/atualizar-consulta/<int:id_consulta>/', views.atualizar_estado_consulta, name='atualizar_estado_consulta'),
    path('api/horarios-disponiveis/', views.horarios_disponiveis_medico, name='horarios_disponiveis_medico'),
        
    # APIs
    path('api/medicos/especialidade/<int:especialidade_id>/', views.api_medicos_por_especialidade, name='api_medicos_especialidade'),
    path('api/horarios/medico/<int:medico_id>/', views.api_horarios_por_medico, name='api_horarios_medico'),
    
    # URLs antigas (mantidas para compatibilidade)
    path('consultas/marcar/', views.marcar_consulta, name='marcar_consulta_old'),
    path('consultas/', views.listar_consultas, name='listar_consultas_old'),
    path('consultas/inserir/', views.inserir_consulta, name='inserir_consulta'),
    path('simple-login/', views.simple_login_view, name='simple_login'),
    
    # Pacientes
    path('pacientes/', views.listar_pacientes, name='listar_pacientes'),
    path('pacientes/inserir/', views.inserir_paciente, name='inserir_paciente'),
    
    # Procedimentos
    path('procedimentos/agendar/', views.usar_procedimento_agendar, name='usar_procedimento_agendar'),
    
    # Vistas
    path('vistas/faturas/', views.usar_vista_faturas, name='usar_vista_faturas'),
    
    # Receitas
    path('receitas/', views.listar_receitas, name='listar_receitas'),
    path('receitas/inserir/', views.inserir_receita, name='inserir_receita'),
    path('receitas/<int:id_receita>/', views.detalhes_receita, name='detalhes_receita'),
    path('receitas/<int:id_receita>/editar/', views.editar_receita, name='editar_receita'),
    path('receitas/<int:id_receita>/eliminar/', views.eliminar_receita, name='eliminar_receita'),
    
    # Faturas
    path('faturas/', views.listar_faturas, name='listar_faturas'),
    path('faturas/inserir/', views.inserir_fatura, name='inserir_fatura'),
    path('faturas/<int:id_fatura>/', views.detalhes_fatura, name='detalhes_fatura'),
    path('faturas/<int:id_fatura>/editar/', views.editar_fatura, name='editar_fatura'),
    path('faturas/<int:id_fatura>/eliminar/', views.eliminar_fatura, name='eliminar_fatura'),
    path('faturas/<int:id_fatura>/pago/', views.marcar_fatura_pago, name='marcar_fatura_pago'),
]