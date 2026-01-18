from django.urls import path
from . import views, views_medico, views_admin, views_enfermeiro

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_home, name="patient_home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("paciente/agendar/", views.agendar_consulta, name="marcar_consulta"),
    path("paciente/agenda/", views.agenda_medica, name="patient_agenda"),
    path("api/disponibilidades/", views.api_disponibilidades, name="api_disponibilidades"),
    path("paciente/consultas/", views.listar_consultas, name="listar_consultas"),
    path("paciente/consultas/<int:consulta_id>/confirmar/", views.paciente_confirmar_consulta, name="paciente_confirmar_consulta"),
    path("paciente/consultas/<int:consulta_id>/recusar/", views.paciente_recusar_consulta, name="paciente_recusar_consulta"),
    path("paciente/consultas/<int:consulta_id>/cancelar/", views.paciente_cancelar_consulta, name="paciente_cancelar_consulta"),
    path("paciente/consultas/<int:consulta_id>/reagendar/", views.reagendar_consulta, name="reagendar_consulta"),
    path("paciente/faturas/", views.listar_faturas, name="listar_faturas"),
    path("paciente/perfil/", views.patient_perfil_editar, name="patient_perfil_editar"),

    # URLs do Médico
    path('medico/dashboard/', views_medico.medico_dashboard, name='medico_dashboard'),
    path('medico/agenda/', views_medico.medico_agenda, name='medico_agenda'),
    path('medico/agendar/', views_medico.medico_agendar_consulta, name='medico_agendar_consulta'),
    path('medico/verificar-disponibilidade/', views_medico.medico_verificar_disponibilidade, name='medico_verificar_disponibilidade'),
    path('medico/disponibilidade/', views_medico.medico_disponibilidade, name='medico_disponibilidade'),
    path('medico/indisponibilidade/', views_medico.medico_indisponibilidade, name='medico_indisponibilidade'),
    path('medico/consulta/<int:consulta_id>/', views_medico.medico_detalhes_consulta, name='medico_detalhes_consulta'),
    path('medico/consulta/<int:consulta_id>/confirmar/', views_medico.medico_confirmar_consulta, name='medico_confirmar_consulta'),
    path('medico/consulta/<int:consulta_id>/recusar/', views_medico.medico_recusar_consulta, name='medico_recusar_consulta'),
    path('medico/consulta/<int:consulta_id>/cancelar/', views_medico.medico_cancelar_consulta, name='medico_cancelar_consulta'),
    path('medico/consulta/<int:consulta_id>/registar/', views_medico.medico_registar_consulta, name='medico_registar_consulta'),
    
    # URLs do Enfermeiro
    path('enfermeiro/dashboard/', views_enfermeiro.enfermeiro_dashboard, name='enfermeiro_dashboard'),
    path('enfermeiro/consultas/', views_enfermeiro.enfermeiro_consultas, name='enfermeiro_consultas'),
    path('enfermeiro/consultas/criar/', views_enfermeiro.enfermeiro_consulta_criar, name='enfermeiro_consulta_criar'),
    path('enfermeiro/pacientes/', views_enfermeiro.enfermeiro_pacientes, name='enfermeiro_pacientes'),
    path('enfermeiro/pacientes/<int:paciente_id>/', views_enfermeiro.enfermeiro_paciente_detalhes, name='enfermeiro_paciente_detalhes'),
    path('enfermeiro/relatorios/', views_enfermeiro.enfermeiro_relatorios, name='enfermeiro_relatorios'),
    
    # URLs do Admin
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # Gestão de Regiões
    path('admin-panel/regioes/', views_admin.admin_regioes, name='admin_regioes'),
    path('admin-panel/regioes/criar/', views_admin.admin_regiao_criar, name='admin_regiao_criar'),
    path('admin-panel/regioes/<int:regiao_id>/editar/', views_admin.admin_regiao_editar, name='admin_regiao_editar'),
    path('admin-panel/regioes/<int:regiao_id>/eliminar/', views_admin.admin_regiao_eliminar, name='admin_regiao_eliminar'),
    
    # Gestão de Especialidades
    path('admin-panel/especialidades/', views_admin.admin_especialidades, name='admin_especialidades'),
    path('admin-panel/especialidades/criar/', views_admin.admin_especialidade_criar, name='admin_especialidade_criar'),
    path('admin-panel/especialidades/<int:especialidade_id>/editar/', views_admin.admin_especialidade_editar, name='admin_especialidade_editar'),
    path('admin-panel/especialidades/<int:especialidade_id>/eliminar/', views_admin.admin_especialidade_eliminar, name='admin_especialidade_eliminar'),
    
    # Gestão de Unidades
    path('admin-panel/unidades/', views_admin.admin_unidades, name='admin_unidades'),
    path('admin-panel/unidades/criar/', views_admin.admin_unidade_criar, name='admin_unidade_criar'),
    path('admin-panel/unidades/<int:unidade_id>/editar/', views_admin.admin_unidade_editar, name='admin_unidade_editar'),
    path('admin-panel/unidades/<int:unidade_id>/eliminar/', views_admin.admin_unidade_eliminar, name='admin_unidade_eliminar'),
    
    # Gestão de Utilizadores
    path('admin-panel/utilizadores/', views_admin.admin_utilizadores, name='admin_utilizadores'),
    path('admin-panel/utilizadores/criar/', views_admin.admin_utilizador_criar, name='admin_utilizador_criar'),
    path('admin-panel/utilizadores/<int:utilizador_id>/editar/', views_admin.admin_utilizador_editar, name='admin_utilizador_editar'),
    path('admin-panel/utilizadores/<int:utilizador_id>/desativar/', views_admin.admin_utilizador_desativar, name='admin_utilizador_desativar'),
    
    # Gestão de Consultas
    path('admin-panel/consultas/', views_admin.admin_consultas, name='admin_consultas'),
    path('admin-panel/consultas/criar/', views_admin.admin_consulta_criar, name='admin_consulta_criar'),
    path('admin-panel/consultas/<int:consulta_id>/cancelar/', views_admin.admin_consulta_cancelar, name='admin_consulta_cancelar'),
    path('admin-panel/disponibilidades/list/', views_admin.admin_disponibilidades_list, name='admin_disponibilidades_list'),
    
    # Gestão de Faturas
    path('admin-panel/faturas/', views_admin.admin_faturas, name='admin_faturas'),
    path('admin-panel/faturas/criar/<int:consulta_id>/', views_admin.admin_fatura_criar, name='admin_fatura_criar'),
    path('admin-panel/faturas/<int:fatura_id>/editar/', views_admin.admin_fatura_editar, name='admin_fatura_editar'),
    
    # Relatórios
    path('admin-panel/relatorios/', views_admin.admin_relatorios, name='admin_relatorios'),
]
