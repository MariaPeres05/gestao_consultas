# core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import LoginForm, RegisterForm
from .models import (
    Utilizador,
    Paciente,
    Consulta,
    Fatura,
    Especialidade,
    UnidadeSaude,
    Medico,
    Disponibilidade,
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user:
                login(request, user)
                # Redirecionar segundo o papel do utilizador
                role = getattr(user, "role", None)

                if role == "paciente":
                    return redirect("patient_home")
                if role == "medico":
                    return redirect("medico_home")
                return redirect("dashboard")
            messages.error(request, "Credenciais incorretas.")
    else:
        form = LoginForm()

    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            Utilizador.objects.create_user(
                nome=form.cleaned_data["nome"],
                email=form.cleaned_data["email"],
                telefone=form.cleaned_data["telefone"],
                n_utente=form.cleaned_data["n_utente"],
                senha=form.cleaned_data["password"],
                role="paciente",
                ativo=True,
            )
            messages.success(request, "Conta criada com sucesso!")
            return redirect("login")

    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})


def dashboard(request):
    return render(request, "core/dashboard.html")


def patient_home(request):
    """Página principal do paciente após login."""
    system_name = "MediPulse"
    user = request.user
    user_name = getattr(user, "nome", user.email if user.is_authenticated else "")

    # Tentar obter o Paciente associado ao utilizador
    consultas_count = 0
    faturas_count = 0
    paciente_obj = None
    if user.is_authenticated:
        try:
            paciente_obj = Paciente.objects.filter(id_utilizador=user).first()
            if paciente_obj:
                consultas_count = Consulta.objects.filter(id_paciente=paciente_obj).count()
                # faturas ligam-se a consultas; contamos todas as faturas associadas às consultas do paciente
                faturas_count = Fatura.objects.filter(id_consulta__id_paciente=paciente_obj).count()
        except Exception:
            consultas_count = 0
            faturas_count = 0

    context = {
        "system_name": system_name,
        "user_name": user_name,
        "user_email": getattr(user, "email", "") if user.is_authenticated else "",
        "consultas_count": consultas_count,
        "faturas_count": faturas_count,
    }

    return render(request, "core/patient_home.html", context)


def agendar_consulta(request):
    """Página para procurar e marcar uma consulta.

    - GET: mostra filtros (especialidade, unidade, médico, data) e lista de
      disponibilidades correspondentes (se houver filtros aplicados).
    - POST: marca a consulta para a disponibilidade selecionada.
    """
    if not request.user.is_authenticated:
        return redirect("login")

    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    if not paciente:
        messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
        return redirect("patient_home")

    if request.method == "POST":
        disp_id = request.POST.get("disponibilidade_id")
        if not disp_id:
            messages.error(request, "Escolha uma disponibilidade para marcar.")
            return redirect("marcar_consulta")

        disponibilidade = get_object_or_404(Disponibilidade, pk=disp_id)

        # Consideramos uma slot livre quando status_slot não indica 'booked' ou 'ocupado'
        if disponibilidade.status_slot and disponibilidade.status_slot.lower() in ("booked", "ocupado", "reserved"):
            messages.error(request, "A disponibilidade já não está disponível.")
            return redirect("marcar_consulta")

        with transaction.atomic():
            consulta = Consulta.objects.create(
                id_paciente=paciente,
                id_medico=disponibilidade.id_medico,
                id_disponibilidade=disponibilidade,
                data_consulta=disponibilidade.data,
                hora_consulta=disponibilidade.hora_inicio,
                estado="marcada",
            )
            disponibilidade.status_slot = "booked"
            disponibilidade.save()

        messages.success(request, "Consulta marcada com sucesso.")
        return redirect("patient_home")

    # GET: construir filtros e listar disponibilidades
    especialidade_id = request.GET.get("especialidade")
    unidade_id = request.GET.get("unidade")
    medico_id = request.GET.get("medico")
    data_q = request.GET.get("data")

    especialidades = Especialidade.objects.all()
    unidades = UnidadeSaude.objects.all()
    medicos = Medico.objects.all()

    disponibilidades = Disponibilidade.objects.all()
    # filtrar por especialidade (medicos)
    if especialidade_id:
        medicos = medicos.filter(id_especialidade__id_especialidade=especialidade_id)
        disponibilidades = disponibilidades.filter(id_medico__in=medicos)

    if unidade_id:
        disponibilidades = disponibilidades.filter(id_unidade__id_unidade=unidade_id)

    if medico_id:
        disponibilidades = disponibilidades.filter(id_medico__id_medico=medico_id)

    if data_q:
        try:
            from datetime import datetime

            data_parsed = datetime.strptime(data_q, "%Y-%m-%d").date()
            disponibilidades = disponibilidades.filter(data=data_parsed)
        except Exception:
            pass

    # apenas slots que não estejam marcados
    disponibilidades = disponibilidades.filter(~Q(status_slot__iexact="booked")).order_by("data", "hora_inicio")[:200]

    context = {
        "especialidades": especialidades,
        "unidades": unidades,
        "medicos": medicos,
        "disponibilidades": disponibilidades,
        "selected": {
            "especialidade": especialidade_id,
            "unidade": unidade_id,
            "medico": medico_id,
            "data": data_q,
        },
    }

    return render(request, "core/patient_agendar.html", context)


def listar_consultas(request):
    """Placeholder para listar consultas do paciente."""
    return render(request, "core/patient_consultas.html")


def listar_faturas(request):
    """Placeholder para listar faturas do paciente."""
    return render(request, "core/patient_faturas.html")


@login_required
def medico_home(request):
    """Página inicial para médicos após login.

    Mostra opções rápidas: gerir disponibilidades, emitir receitas, ver consultas.
    """
    # tentar obter o registo Medico associado
    medico = Medico.objects.filter(id_utilizador=request.user).first()
    if not medico:
        messages.error(request, "Não foi encontrado um registo de médico para este utilizador.")
        return redirect("dashboard")

    context = {
        "medico": medico,
    }
    return render(request, "core/medico_home.html", context)


@login_required
def medico_disponibilidades(request):
    medico = Medico.objects.filter(id_utilizador=request.user).first()
    if not medico:
        messages.error(request, "Acesso indisponível: não é um médico.")
        return redirect("dashboard")

    disponibilidades = Disponibilidade.objects.filter(id_medico=medico).order_by("data", "hora_inicio")
    return render(request, "core/medico_disponibilidades.html", {"medico": medico, "disponibilidades": disponibilidades})


@login_required
def medico_receitas(request):
    medico = Medico.objects.filter(id_utilizador=request.user).first()
    if not medico:
        messages.error(request, "Acesso indisponível: não é um médico.")
        return redirect("dashboard")

    # Por enquanto listamos receitas associadas às consultas do médico
    receitas = []
    try:
        receitas = [r for c in Consulta.objects.filter(id_medico=medico) for r in c.receitas.all()]
    except Exception:
        receitas = []

    return render(request, "core/medico_receitas.html", {"medico": medico, "receitas": receitas})


@login_required
def medico_consultas(request):
    medico = Medico.objects.filter(id_utilizador=request.user).first()
    if not medico:
        messages.error(request, "Acesso indisponível: não é um médico.")
        return redirect("dashboard")

    consultas = Consulta.objects.filter(id_medico=medico).order_by("data_consulta", "hora_consulta")
    return render(request, "core/medico_consultas.html", {"medico": medico, "consultas": consultas})


def home(request):
    """Página inicial pública do sistema de gestão de consultas.

    Passa o nome do sistema para o template.
    """
    system_name = "MediPulse"
    return render(request, "core/home.html", {"system_name": system_name})
