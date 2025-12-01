from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_home, name="patient_home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("medico/", views.medico_home, name="medico_home"),
    path("medico/disponibilidades/", views.medico_disponibilidades, name="medico_disponibilidades"),
    path("medico/receitas/", views.medico_receitas, name="medico_receitas"),
    path("medico/consultas/", views.medico_consultas, name="medico_consultas"),
    path("paciente/agendar/", views.agendar_consulta, name="marcar_consulta"),
    path("paciente/agenda/", views.agenda_medica, name="patient_agenda"),
    path("api/disponibilidades/", views.api_disponibilidades, name="api_disponibilidades"),
    path("paciente/consultas/", views.listar_consultas, name="listar_consultas"),
    path("paciente/faturas/", views.listar_faturas, name="listar_faturas"),
]
