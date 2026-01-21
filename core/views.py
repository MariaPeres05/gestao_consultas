# core/views.py
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from .forms import LoginForm, RegisterForm, PacienteDetailsForm
from .models import (
    Utilizador,
    Paciente,
    Consulta,
    Fatura,
    Especialidade,
    UnidadeSaude,
    Medico,
    Disponibilidade,
    Receita, 
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_time
from .decorators import role_required


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            # Redirect based on user role
            if user.role == 'medico':
                return redirect('medico_dashboard')
            elif user.role == 'paciente':
                return redirect('patient_home')
            elif user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'enfermeiro':
                return redirect('enfermeiro_dashboard')
            return redirect('home')
        else:
            messages.error(request, "Email ou password incorretos.")
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
@role_required('paciente')
def update_paciente_details(request):
    """Allow patient to update their personal details"""
    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    
    if not paciente:
        messages.error(request, "Não foi possível encontrar o registo de paciente.")
        return redirect("patient_home")
    
    if request.method == "POST":
        form = PacienteDetailsForm(request.POST)
        if form.is_valid():
            paciente.data_nasc = form.cleaned_data["data_nasc"]
            paciente.genero = form.cleaned_data["genero"]
            paciente.morada = form.cleaned_data["morada"]
            paciente.alergias = form.cleaned_data["alergias"]
            paciente.observacoes = form.cleaned_data["observacoes"]
            paciente.save()
            
            messages.success(request, "✅ Dados atualizados com sucesso!")
            return redirect("patient_home")
    else:
        # Pre-populate form with existing data
        initial_data = {
            "data_nasc": paciente.data_nasc,
            "genero": paciente.genero,
            "morada": paciente.morada or "",
            "alergias": paciente.alergias or "",
            "observacoes": paciente.observacoes or "",
        }
        form = PacienteDetailsForm(initial=initial_data)
    
    return render(request, "core/update_paciente_details.html", {
        "form": form,
        "paciente": paciente,
    })


def register_view(request):
    from .email_utils import enviar_email_verificacao
    from datetime import date
    
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Create user account
            user = Utilizador.objects.create_user(
                nome=form.cleaned_data["nome"],
                email=form.cleaned_data["email"],
                telefone=form.cleaned_data["telefone"],
                senha=form.cleaned_data["password"],
                role=Utilizador.ROLE_PACIENTE,
                ativo=True,
            )
            
            # Create corresponding Paciente record
            Paciente.objects.create(
                id_utilizador=user,
                data_nasc=date(2000, 1, 1),  # Default date - user can update in profile
                genero="Não especificado",  # Default - user can update in profile
                morada="",
                alergias="",
                observacoes=""
            )
            
            # Enviar email de verificação
            if enviar_email_verificacao(user, request):
                messages.success(request, "✅ Conta criada com sucesso! Verifique o seu email para ativar a conta.")
            else:
                messages.success(request, "Conta criada com sucesso! Pode fazer login.")
            
            return redirect("login")

    else:
        form = RegisterForm()

    return render(request, "core/register.html", {"form": form})


def dashboard(request):
    """
    Generic dashboard view that redirects users to their role-specific dashboard.
    This ensures users always land on the appropriate page for their role.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Redirect based on user role
    if request.user.role == 'medico':
        return redirect('medico_dashboard')
    elif request.user.role == 'paciente':
        return redirect('patient_home')
    elif request.user.role == 'admin':
        return redirect('admin_dashboard')
    elif request.user.role == 'enfermeiro':
        return redirect('enfermeiro_dashboard')
    
    # Fallback to home page if role is not recognized
    return redirect('home')


def verify_email(request, token):
    """
    View para verificar o email do utilizador através do token enviado por email.
    
    Args:
        token: Token de verificação único enviado no email
    """
    try:
        # Buscar utilizador pelo token de verificação
        user = Utilizador.objects.get(verification_token=token)
        
        # Verificar se já foi verificado
        if user.email_verified:
            messages.info(request, "Este email já foi verificado anteriormente.")
            return redirect('login')
        
        # Marcar email como verificado e limpar token
        user.email_verified = True
        user.verification_token = None
        user.save(update_fields=['email_verified', 'verification_token'])
        
        messages.success(request, "✅ Email verificado com sucesso! Pode agora fazer login.")
        return redirect('login')
        
    except Utilizador.DoesNotExist:
        messages.error(request, "Link de verificação inválido ou expirado.")
        return redirect('login')
    except Exception as e:
        messages.error(request, "Ocorreu um erro ao verificar o email. Por favor, tente novamente.")
        return redirect('login')


def resend_verification(request):
    """
    View para reenviar email de verificação para utilizadores não verificados.
    Requer que o utilizador esteja autenticado.
    """
    from .email_utils import reenviar_email_verificacao
    
    if not request.user.is_authenticated:
        messages.error(request, "Precisa fazer login primeiro.")
        return redirect('login')
    
    user = request.user
    
    # Verificar se já está verificado
    if user.email_verified:
        messages.info(request, "O seu email já está verificado.")
        return redirect('dashboard')
    
    # Reenviar email de verificação
    if reenviar_email_verificacao(user, request):
        messages.success(request, "📧 Email de verificação reenviado! Verifique a sua caixa de entrada.")
    else:
        messages.error(request, "Erro ao reenviar email de verificação. Tente novamente mais tarde.")
    
    return redirect('dashboard')


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
                # Count only confirmed consultas (accepted by both parties) that are not canceled
                consultas_count = Consulta.objects.filter(
                    id_paciente=paciente_obj,
                    estado='confirmada'
                ).count()
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
        hora_consulta_str = request.POST.get("hora_consulta")
        
        if not disp_id:
            messages.error(request, "Escolha uma disponibilidade para marcar.")
            return redirect("marcar_consulta")
        
        if not hora_consulta_str:
            messages.error(request, "Selecione um horário para a consulta.")
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

                # Parse the selected time
                try:
                    hora_consulta = datetime.strptime(hora_consulta_str, "%H:%M").time()
                except ValueError:
                    messages.error(request, "Horário inválido.")
                    return redirect("marcar_consulta")
                
                # Validate the time is within disponibilidade range
                if hora_consulta < disponibilidade.hora_inicio or (disponibilidade.hora_fim and hora_consulta >= disponibilidade.hora_fim):
                    messages.error(request, "Horário fora do intervalo de disponibilidade.")
                    return redirect("marcar_consulta")

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
                    estado="agendada",  # Aguarda confirmação do médico
                    medico_aceitou=False,  # Médico precisa aceitar
                    paciente_aceitou=True  # Paciente já aceita ao marcar
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
    
    # Calculate available time slots for each disponibilidade
    from datetime import datetime, timedelta
    for disp in disponibilidades:
        time_slots = []
        if disp.hora_fim:
            # Generate slots every 30 minutes (or use duracao_slot if available)
            duracao = getattr(disp, 'duracao_slot', 30) or 30
            start_dt = datetime.combine(disp.data, disp.hora_inicio)
            end_dt = datetime.combine(disp.data, disp.hora_fim)
            
            current_time = start_dt
            while current_time < end_dt:
                slot_time = current_time.time()
                # Check if this slot is already booked
                is_booked = Consulta.objects.filter(
                    id_disponibilidade=disp,
                    hora_consulta=slot_time
                ).exists()
                
                time_slots.append({
                    'time': slot_time.strftime('%H:%M'),
                    'available': not is_booked
                })
                current_time += timedelta(minutes=duracao)
        else:
            # If no end time, just show the start time
            time_slots.append({
                'time': disp.hora_inicio.strftime('%H:%M'),
                'available': not Consulta.objects.filter(
                    id_disponibilidade=disp,
                    hora_consulta=disp.hora_inicio
                ).exists()
            })
        
        disp.time_slots = time_slots

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
        .prefetch_related('receitas') 
        .order_by("-data_consulta", "hora_consulta")
    )
    
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    for consulta in consultas:
        consulta_datetime = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
        if timezone.is_aware(consulta_datetime):
            consulta_datetime = timezone.make_naive(consulta_datetime)
        consulta_datetime = timezone.make_aware(consulta_datetime)
        tempo_restante = consulta_datetime - timezone.now()
        consulta.can_cancel_24h = tempo_restante >= timedelta(hours=24)
        
        # Verificar se a consulta já passou (para fins de exibição)
        # Consultas no passado só devem mostrar "realizada" se foram realmente marcadas como tal
        # Se ainda não foram marcadas como realizadas mas já passaram, deixar no estado anterior
        if consulta_datetime < timezone.now() and consulta.estado != 'realizada':
            # Se já passou mas ainda não foi registada como realizada
            # não muda o estado, apenas mostra como estava
            pass
        
        consulta.tem_receita = consulta.receitas.exists()

    context = {"consultas": consultas, "paciente": paciente}
    return render(request, "core/patient_consultas.html", context)

@login_required
@role_required('paciente')
def paciente_receitas(request, consulta_id):
    """Mostra as receitas associadas a uma consulta específica do paciente"""
    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    if not paciente:
        return redirect('patient_home')
    
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_paciente=paciente)
    receitas = Receita.objects.filter(id_consulta=consulta).order_by('data_prescricao')
    
    context = {
        'consulta': consulta,
        'receitas': receitas,
    }
    
    return render(request, 'core/patient_receitas.html', context)

@login_required
@role_required('paciente')
def paciente_confirmar_consulta(request, consulta_id):
    """Paciente confirma uma consulta agendada"""
    paciente = Paciente.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_paciente=paciente)
    
    if consulta.estado == 'agendada':
        consulta.paciente_aceitou = True
        
        # Se o médico já aceitou, confirma a consulta
        if consulta.medico_aceitou:
            consulta.estado = 'confirmada'
            messages.success(request, "Consulta confirmada com sucesso!")
        else:
            # Senão, mantém como agendada esperando aceitação do médico
            messages.success(request, "Aceitaste a consulta. A aguardar aceitação do médico.")
        
        consulta.save()
    else:
        messages.warning(request, "Esta consulta não pode ser confirmada.")
    
    return redirect('listar_consultas')


@login_required
@role_required('paciente')
def paciente_recusar_consulta(request, consulta_id):
    """Paciente recusa uma consulta agendada"""
    paciente = Paciente.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_paciente=paciente)
    
    if consulta.estado == 'agendada':
        consulta.estado = 'cancelada'
        if not consulta.motivo:
            consulta.motivo = "Recusada pelo paciente"
        else:
            consulta.motivo += " (Recusada pelo paciente)"
        consulta.save()
        messages.success(request, "Consulta recusada.")
    else:
        messages.warning(request, "Esta consulta não pode ser recusada.")
    
    return redirect('listar_consultas')


@login_required
@role_required('paciente')
def paciente_cancelar_consulta(request, consulta_id):
    """Paciente cancela uma consulta confirmada (até 24h antes)"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    paciente = Paciente.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_paciente=paciente)
    
    # Combinar data e hora da consulta
    consulta_datetime = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
    if timezone.is_aware(consulta_datetime):
        consulta_datetime = timezone.make_naive(consulta_datetime)
    consulta_datetime = timezone.make_aware(consulta_datetime)
    
    # Verificar se faltam mais de 24 horas
    tempo_restante = consulta_datetime - timezone.now()
    
    if tempo_restante < timedelta(hours=24):
        messages.error(request, "Não é possível cancelar consultas com menos de 24 horas de antecedência.")
        return redirect('listar_consultas')
    
    if consulta.estado in ['agendada', 'confirmada']:
        consulta.estado = 'cancelada'
        if not consulta.motivo:
            consulta.motivo = "Cancelada pelo paciente"
        else:
            consulta.motivo += " (Cancelada pelo paciente)"
        consulta.save()
        messages.success(request, "Consulta cancelada com sucesso.")
    else:
        messages.warning(request, "Esta consulta não pode ser cancelada.")
    
    return redirect('listar_consultas')


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


@login_required
def patient_perfil_editar(request):
    """Permite ao paciente editar o seu perfil."""
    if request.user.role != 'paciente':
        messages.error(request, "Acesso negado.")
        return redirect('home')
    
    user = request.user
    
    if request.method == 'POST':
        # Atualizar dados do utilizador
        nome = request.POST.get('nome', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()
        
        if nome:
            user.nome = nome
        if telefone:
            user.telefone = telefone
        
        # Se forneceu nova password, valida e atualiza
        if password:
            if password == password_confirm:
                if len(password) >= 6:
                    user.set_password(password)
                    messages.success(request, "Perfil atualizado com sucesso! Por favor, faça login novamente com a nova password.")
                    user.save()
                    logout(request)
                    return redirect('login')
                else:
                    messages.error(request, "A password deve ter pelo menos 6 caracteres.")
                    return render(request, 'core/patient_perfil.html', {'user': user})
            else:
                messages.error(request, "As passwords não coincidem.")
                return render(request, 'core/patient_perfil.html', {'user': user})
        
        user.save()
        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect('patient_perfil_editar')
    
    context = {'user': user}
    return render(request, 'core/patient_perfil.html', context)


@login_required
def reagendar_consulta(request, consulta_id):
    """Permite reagendar uma consulta existente para uma nova disponibilidade."""
    if request.user.role != 'paciente':
        messages.error(request, "Acesso negado.")
        return redirect('home')
    
    paciente = Paciente.objects.filter(id_utilizador=request.user).first()
    if not paciente:
        messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
        return redirect("patient_home")
    
    # Buscar consulta original
    try:
        consulta = Consulta.objects.select_related(
            'id_medico__id_utilizador',
            'id_medico__id_especialidade',
            'id_disponibilidade__id_unidade'
        ).get(id_consulta=consulta_id, id_paciente=paciente)
    except Consulta.DoesNotExist:
        messages.error(request, "Consulta não encontrada.")
        return redirect('listar_consultas')
    
    # Só permitir reagendar se estiver em estado marcada ou agendada
    if consulta.estado.lower() not in ('marcada', 'agendada'):
        messages.error(request, "Esta consulta não pode ser reagendada.")
        return redirect('listar_consultas')
    
    if request.method == 'POST':
        nova_disp_id = request.POST.get('nova_disponibilidade')
        if nova_disp_id:
            try:
                with transaction.atomic():
                    # Buscar nova disponibilidade
                    nova_disp = Disponibilidade.objects.select_for_update().get(
                        id_disponibilidade=nova_disp_id,
                        status_slot__in=['available', 'disponivel']
                    )
                    
                    # Libertar disponibilidade antiga (se existir)
                    if consulta.id_disponibilidade:
                        disp_antiga = consulta.id_disponibilidade
                        disp_antiga.status_slot = 'available'
                        disp_antiga.save()
                    
                    # Atualizar consulta
                    consulta.id_disponibilidade = nova_disp
                    consulta.data_consulta = nova_disp.data
                    consulta.hora_consulta = nova_disp.hora_inicio
                    consulta.id_medico = nova_disp.id_medico
                    consulta.estado = 'agendada'
                    consulta.save()
                    
                    # Marcar nova disponibilidade como ocupada
                    nova_disp.status_slot = 'booked'
                    nova_disp.save()
                    
                    messages.success(request, "Consulta reagendada com sucesso!")
                    return redirect('listar_consultas')
                    
            except Disponibilidade.DoesNotExist:
                messages.error(request, "Disponibilidade não encontrada ou já ocupada.")
            except Exception as e:
                messages.error(request, f"Erro ao reagendar: {str(e)}")
        else:
            messages.error(request, "Por favor, selecione uma nova data/hora.")
    
    # Buscar disponibilidades do mesmo médico (ou da mesma especialidade)
    disponibilidades = Disponibilidade.objects.filter(
        id_medico=consulta.id_medico,
        status_slot__in=['available', 'disponivel']
    ).filter(
        Q(data__gt=consulta.data_consulta) | 
        Q(data=consulta.data_consulta, hora_inicio__gt=consulta.hora_consulta)
    ).select_related('id_unidade').order_by('data', 'hora_inicio')[:50]
    
    context = {
        'consulta': consulta,
        'disponibilidades': disponibilidades,
        'paciente': paciente
    }
    return render(request, 'core/patient_reagendar.html', context)


def home(request):
    """Página inicial pública do sistema de gestão de consultas.

    Passa o nome do sistema para o template.
    """
    system_name = "MediPulse"
    return render(request, "core/home.html", {"system_name": system_name})
