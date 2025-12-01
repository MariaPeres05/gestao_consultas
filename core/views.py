# core/views.py
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
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
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_time


@csrf_exempt
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
                # aplicar "Lembrar-me": prolongar sessão se pedido
                try:
                    remember = form.cleaned_data.get("remember_me")
                except Exception:
                    remember = False
                if remember:
                    # 30 dias
                    request.session.set_expiry(30 * 24 * 3600)
                else:
                    # expira ao fechar o browser
                    request.session.set_expiry(0)
                # Redireciona pacientes para a área do paciente, outros para o dashboard
                try:
                    role = getattr(user, "role", None)
                except Exception:
                    role = None

                if role == Utilizador.ROLE_PACIENTE:
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
                role=Utilizador.ROLE_PACIENTE,
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
        # Bloquear a disponibilidade para evitar race conditions
        from datetime import datetime, timedelta

        try:
            with transaction.atomic():
                disponibilidade = Disponibilidade.objects.select_for_update().get(pk=disp_id)

                # Consideramos uma slot livre quando status_slot não indica 'booked' ou 'ocupado'
                if disponibilidade.status_slot and disponibilidade.status_slot.lower() in ("booked", "ocupado", "reserved"):
                    messages.error(request, "A disponibilidade já não está disponível.")
                    return redirect("marcar_consulta")

                hora_consulta = disponibilidade.hora_inicio

                # impedir dupla marcação no mesmo disponibilidade+hora
                if Consulta.objects.filter(id_disponibilidade=disponibilidade, hora_consulta=hora_consulta).exists():
                    messages.error(request, "O horário já foi marcado por outro paciente.")
                    return redirect("marcar_consulta")

                consulta = Consulta.objects.create(
                    id_paciente=paciente,
                    id_medico=disponibilidade.id_medico,
                    id_disponibilidade=disponibilidade,
                    data_consulta=disponibilidade.data,
                    hora_consulta=hora_consulta,
                    estado="marcada",
                )

                # calcular número total de slots possíveis para esta disponibilidade
                duracao = getattr(disponibilidade, "duracao_slot", None) or 0
                start_dt = datetime.combine(disponibilidade.data, disponibilidade.hora_inicio)
                end_dt = datetime.combine(disponibilidade.data, disponibilidade.hora_fim) if getattr(disponibilidade, "hora_fim", None) else start_dt

                total_slots = 0
                if duracao and duracao > 0 and end_dt > start_dt:
                    step = timedelta(minutes=duracao)
                    cur = start_dt
                    while cur + step <= end_dt + timedelta(seconds=1):
                        total_slots += 1
                        cur += step
                else:
                    total_slots = 1

                consultas_count = Consulta.objects.filter(id_disponibilidade=disponibilidade).count()
                if total_slots and consultas_count >= total_slots:
                    disponibilidade.status_slot = "booked"
                    disponibilidade.save()

        except Disponibilidade.DoesNotExist:
            messages.error(request, "Disponibilidade não encontrada.")
            return redirect("marcar_consulta")

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


def agenda_medica(request):
    """Renderiza um calendário com as disponibilidades (FullCalendar)."""
    if not request.user.is_authenticated:
        return redirect("login")

    return render(request, "core/agenda_medica.html", {})


def api_disponibilidades(request):
    """API simples que retorna disponibilidades como eventos JSON.

    Query params:
    - medico: optional medico id to filtrar
    - unidade: optional unidade id
    - start/end: ignored here (could be used to limit range)
    """
    qs = Disponibilidade.objects.all()
    medico_id = request.GET.get("medico")
    unidade_id = request.GET.get("unidade")
    if medico_id:
        qs = qs.filter(id_medico__id_medico=medico_id)
    if unidade_id:
        qs = qs.filter(id_unidade__id_unidade=unidade_id)

    # só disponibilidades não marcadas
    qs = qs.filter(~Q(status_slot__iexact="booked"))

    events = []
    for d in qs:
        start = None
        end = None
        try:
            start = f"{d.data.isoformat()}T{d.hora_inicio.strftime('%H:%M:%S')}"
        except Exception:
            start = None
        try:
            if getattr(d, 'hora_fim', None):
                end = f"{d.data.isoformat()}T{d.hora_fim.strftime('%H:%M:%S')}"
        except Exception:
            end = None

        title = f"{d.id_medico.id_utilizador.nome}"
        events.append({
            "id": d.id_disponibilidade,
            "title": title,
            "start": start,
            "end": end,
            "extendedProps": {
                "medico_id": d.id_medico.id_medico,
                "unidade": getattr(d.id_unidade, 'nome_unidade', None),
            },
        })

    return JsonResponse(events, safe=False)


def listar_consultas(request):
    """Lista e gere as consultas do paciente autenticado.

    - GET: mostra as consultas ordenadas por data/hora
    - POST: permite cancelar uma consulta (muda `estado` para 'cancelada')
    """
    if not request.user.is_authenticated:
        return redirect("login")

    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    if not paciente:
        messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
        return redirect("patient_home")

    # POST: ação (ex.: cancelar)
    if request.method == "POST":
        action = request.POST.get("action")
        consulta_id = request.POST.get("consulta_id")
        if action == "cancel" and consulta_id:
            try:
                with transaction.atomic():
                    consulta = Consulta.objects.select_for_update().get(id_consulta=consulta_id, id_paciente=paciente)
                    # permitir cancelamento apenas se estiver em estado marcada
                    if consulta.estado.lower() in ("marcada", "agendada"):
                        consulta.estado = "cancelada"
                        consulta.save()
                        messages.success(request, "Consulta cancelada com sucesso.")
                    else:
                        messages.error(request, "Esta consulta não pode ser cancelada.")
            except Consulta.DoesNotExist:
                messages.error(request, "Consulta não encontrada.")

        return redirect("listar_consultas")

    consultas = (
        Consulta.objects.filter(id_paciente=paciente)
        .select_related("id_medico__id_utilizador", "id_disponibilidade__id_unidade")
        .order_by("-data_consulta", "hora_consulta")
    )

    context = {"consultas": consultas, "paciente": paciente}
    return render(request, "core/patient_consultas.html", context)


def listar_faturas(request):
    """Lista e gere as faturas do paciente autenticado.

    - GET: mostra as faturas associadas às consultas do paciente
    - POST: permite marcar uma fatura como paga (define `estado='paga'` e `data_pagamento`)
    """
    if not request.user.is_authenticated:
        return redirect("login")

    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    if not paciente:
        messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
        return redirect("patient_home")

    if request.method == "POST":
        action = request.POST.get("action")
        fatura_id = request.POST.get("fatura_id")
        if action == "pay" and fatura_id:
            try:
                with transaction.atomic():
                    f = Fatura.objects.select_for_update().get(id_fatura=fatura_id, id_consulta__id_paciente=paciente)
                    if f.estado.lower() != "paga":
                        from django.utils import timezone

                        f.estado = "paga"
                        f.data_pagamento = timezone.now()
                        # opcional: método de pagamento
                        metodo = request.POST.get("metodo_pagamento")
                        if metodo:
                            f.metodo_pagamento = metodo
                        f.save()
                        messages.success(request, "Fatura marcada como paga.")
                    else:
                        messages.info(request, "A fatura já está paga.")
            except Fatura.DoesNotExist:
                messages.error(request, "Fatura não encontrada.")

        return redirect("listar_faturas")

    faturas = (
        Fatura.objects.filter(id_consulta__id_paciente=paciente)
        .select_related("id_consulta__id_medico__id_utilizador")
        .order_by("-data_pagamento", "-id_fatura")
    )

    context = {"faturas": faturas, "paciente": paciente}
    return render(request, "core/patient_faturas.html", context)


def home(request):
    """Página inicial pública do sistema de gestão de consultas.

    Passa o nome do sistema para o template.
    """
    system_name = "MediPulse"
    return render(request, "core/home.html", {"system_name": system_name})
