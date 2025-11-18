from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("paciente/", views.patient_home, name="patient_home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("paciente/agendar/", views.agendar_consulta, name="marcar_consulta"),
    path("paciente/consultas/", views.listar_consultas, name="listar_consultas"),
    path("paciente/faturas/", views.listar_faturas, name="listar_faturas"),
]
