# core/views.py
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

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
    Receita,
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_time


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user:
            # Verificar se o email foi verificado
            if not user.email_verified:
                messages.error(request, "Por favor, verifique o seu email antes de fazer login. Não recebeu o email? <a href='/reenviar-verificacao/'>Clique aqui para reenviar</a>.")
                return render(request, 'core/login.html')
            
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


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                # Criar utilizador (n_utente é gerado automaticamente)
                user = Utilizador.objects.create_user(
                    nome=form.cleaned_data["nome"],
                    email=form.cleaned_data["email"],
                    telefone=form.cleaned_data["telefone"],
                    senha=form.cleaned_data["password"],
                    role=Utilizador.ROLE_PACIENTE,
                    ativo=True,
                )
                
                # Gerar token de verificação
                import secrets
                verification_token = secrets.token_urlsafe(32)
                user.verification_token = verification_token
                user.email_verified = False
                user.save()
                
                # Enviar email de verificação
                verification_url = request.build_absolute_uri(
                    reverse('verify_email', kwargs={'token': verification_token})
                )
                
                email_subject = "Verificação de Email - MediPulse"
                email_message = f"""
Olá {user.nome},

Obrigado por se registar no MediPulse!

Por favor, clique no link abaixo para verificar o seu email:
{verification_url}

Este link é válido por 24 horas.

Se não criou esta conta, por favor ignore este email.

Cumprimentos,
Equipa MediPulse
                """
                
                try:
                    send_mail(
                        email_subject,
                        email_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    messages.success(request, "Conta criada! Verifique o seu email para ativar a conta.")
                except Exception as e:
                    messages.warning(request, f"Conta criada, mas não foi possível enviar o email de verificação. Entre em contacto com o suporte.")
                
                return redirect("login")
            
            except Exception as e:
                # Handle any database errors (e.g., duplicate email)
                from django.db import IntegrityError
                if isinstance(e, IntegrityError) and 'email' in str(e).lower():
                    messages.error(request, "Este email já está registado. Por favor, use outro email ou faça login.")
                else:
                    messages.error(request, "Ocorreu um erro ao criar a conta. Por favor, tente novamente.")
                return render(request, 'core/register.html', {'form': form})

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
        
        if nome:
            user.nome = nome
        if telefone:
            user.telefone = telefone
        
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


# ==================== PASSWORD RECOVERY ====================

def password_reset_request(request):
    """Página para solicitar reset de password."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Por favor, insira o seu email.")
            return render(request, 'core/password_reset_request.html')
        
        # Verificar se o utilizador existe
        try:
            user = Utilizador.objects.get(email=email)
            
            # Gerar token de reset
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Construir URL de reset
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Enviar email
            subject = 'Recuperação de Password - MediPulse'
            message = f"""
Olá {user.nome},

Recebemos um pedido para recuperar a sua password.

Clique no link abaixo para definir uma nova password:
{reset_url}

Este link é válido por 24 horas.

Se não solicitou esta recuperação, ignore este email.

Cumprimentos,
Equipa MediPulse
"""
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, "Email enviado! Verifique a sua caixa de entrada.")
                return redirect('password_reset_done')
            except Exception as e:
                messages.error(request, f"Erro ao enviar email: {str(e)}")
                return render(request, 'core/password_reset_request.html')
                
        except Utilizador.DoesNotExist:
            # Por segurança, não revelar se o email existe ou não
            messages.success(request, "Se o email existir no sistema, receberá instruções para recuperar a password.")
            return redirect('password_reset_done')
    
    return render(request, 'core/password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    """Página para confirmar e definir nova password."""
    try:
        # Decodificar user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Utilizador.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Utilizador.DoesNotExist):
        user = None
    
    # Verificar se o token é válido
    token_generator = PasswordResetTokenGenerator()
    
    if user is not None and token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()
            
            # Validações
            if not password:
                messages.error(request, "A password não pode estar vazia.")
                return render(request, 'core/password_reset_confirm.html')
            
            if len(password) < 6:
                messages.error(request, "A password deve ter pelo menos 6 caracteres.")
                return render(request, 'core/password_reset_confirm.html')
            
            if password != password_confirm:
                messages.error(request, "As passwords não coincidem.")
                return render(request, 'core/password_reset_confirm.html')
            
            # Atualizar password
            user.set_password(password)
            user.save()
            
            messages.success(request, "Password redefinida com sucesso! Pode agora fazer login.")
            return redirect('login')
        
        return render(request, 'core/password_reset_confirm.html')
    else:
        messages.error(request, "Link de recuperação inválido ou expirado.")
        return redirect('password_reset_request')


def password_reset_done(request):
    """Página de confirmação após solicitar reset."""
    return render(request, 'core/password_reset_done.html')


@login_required
def profile_view(request):
    """View genérica de perfil para todos os utilizadores."""
    user = request.user
    
    # Redirecionar para template específico baseado no role
    template_map = {
        'paciente': 'core/patient_perfil.html',
        'medico': 'core/medico_perfil.html',
        'enfermeiro': 'core/enfermeiro_perfil.html',
        'admin': 'core/admin_perfil.html',
    }
    
    template = template_map.get(user.role, 'core/profile.html')
    context = {'user': user}
    return render(request, template, context)


@login_required
def profile_edit(request):
    """Permite ao utilizador editar o seu perfil (genérico para todos os roles)."""
    user = request.user
    
    if request.method == 'POST':
        # Atualizar dados do utilizador
        nome = request.POST.get('nome', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        foto_perfil = request.POST.get('foto_perfil', '').strip()
        
        if nome:
            user.nome = nome
        if telefone:
            user.telefone = telefone
        if foto_perfil:
            user.foto_perfil = foto_perfil
        
        user.save()
        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect('profile_view')
    
    # Redirecionar para template específico baseado no role
    template_map = {
        'paciente': 'core/patient_perfil.html',
        'medico': 'core/medico_perfil.html',
        'enfermeiro': 'core/enfermeiro_perfil.html',
        'admin': 'core/admin_perfil.html',
    }
    
    template = template_map.get(user.role, 'core/profile_edit.html')
    context = {'user': user}
    return render(request, template, context)


@login_required
def change_password(request):
    """Permite ao utilizador alterar a sua password."""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Validar password atual
        if not request.user.check_password(current_password):
            messages.error(request, "A password atual está incorreta.")
            return render(request, 'core/change_password.html')
        
        # Validar nova password
        if not new_password:
            messages.error(request, "A nova password não pode estar vazia.")
            return render(request, 'core/change_password.html')
        
        if len(new_password) < 6:
            messages.error(request, "A password deve ter pelo menos 6 caracteres.")
            return render(request, 'core/change_password.html')
        
        if new_password != confirm_password:
            messages.error(request, "As passwords não coincidem.")
            return render(request, 'core/change_password.html')
        
        # Atualizar password
        request.user.set_password(new_password)
        request.user.save()
        
        # Fazer logout e pedir login novamente com nova password
        messages.success(request, "Password alterada com sucesso! Por favor, faça login novamente.")
        logout(request)
        return redirect('login')
    
    return render(request, 'core/change_password.html')


def verify_email(request, token):
    """Verifica o email do utilizador através do token."""
    try:
        user = Utilizador.objects.get(verification_token=token)
        
        if user.email_verified:
            messages.info(request, "O seu email já foi verificado anteriormente.")
            return redirect('login')
        
        # Verificar email
        user.email_verified = True
        user.verification_token = None  # Limpar o token após uso
        user.save()
        
        messages.success(request, "Email verificado com sucesso! Pode agora fazer login.")
        return redirect('login')
        
    except Utilizador.DoesNotExist:
        messages.error(request, "Token de verificação inválido ou expirado.")
        return redirect('login')


def resend_verification(request):
    """Permite reenviar o email de verificação."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Por favor, forneça um email.")
            return render(request, 'core/resend_verification.html')
        
        try:
            user = Utilizador.objects.get(email=email)
            
            if user.email_verified:
                messages.info(request, "O seu email já está verificado. Pode fazer login.")
                return redirect('login')
            
            # Gerar novo token
            import secrets
            verification_token = secrets.token_urlsafe(32)
            user.verification_token = verification_token
            user.save()
            
            # Enviar email
            verification_url = request.build_absolute_uri(
                reverse('verify_email', kwargs={'token': verification_token})
            )
            
            email_subject = "Reenvio de Verificação de Email - MediPulse"
            email_message = f"""
Olá {user.nome},

Recebemos um pedido para reenviar o link de verificação de email.

Por favor, clique no link abaixo para verificar o seu email:
{verification_url}

Este link é válido por 24 horas.

Se não solicitou este email, por favor ignore.

Cumprimentos,
Equipa MediPulse
            """
            
            try:
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, "Email de verificação reenviado! Verifique a sua caixa de entrada.")
            except Exception as e:
                messages.error(request, "Erro ao enviar o email. Tente novamente mais tarde.")
            
            return redirect('resend_verification_done')
            
        except Utilizador.DoesNotExist:
            # Por segurança, não revelar se o email existe ou não
            messages.success(request, "Se o email existir no sistema, receberá um link de verificação.")
            return redirect('resend_verification_done')
    
    return render(request, 'core/resend_verification.html')


def resend_verification_done(request):
    """Página de confirmação após reenvio do email de verificação."""
    return render(request, 'core/resend_verification_done.html')


# ---------- Receitas (Prescriptions) ----------
@login_required
@role_required('paciente')
def patient_receitas(request):
    """View patient prescriptions"""
    try:
        paciente = Paciente.objects.get(id_utilizador=request.user)
    except Paciente.DoesNotExist:
        messages.error(request, "Perfil de paciente não encontrado.")
        return redirect('index')
    
    # Get all prescriptions from patient's consultations
    receitas = Receita.objects.filter(
        id_consulta__id_paciente=paciente
    ).select_related(
        'id_consulta',
        'id_consulta__id_medico__id_utilizador',
        'id_consulta__id_medico__id_especialidade'
    ).order_by('-data_prescricao')
    
    context = {
        'receitas': receitas,
        'paciente': paciente,
    }
    
    return render(request, 'core/patient_receitas.html', context)


@login_required
@role_required('paciente')
def patient_receita_detalhes(request, receita_id):
    """View prescription details"""
    try:
        paciente = Paciente.objects.get(id_utilizador=request.user)
    except Paciente.DoesNotExist:
        messages.error(request, "Perfil de paciente não encontrado.")
        return redirect('index')
    
    # Get prescription and verify it belongs to this patient
    receita = get_object_or_404(
        Receita.objects.select_related(
            'id_consulta',
            'id_consulta__id_medico__id_utilizador',
            'id_consulta__id_medico__id_especialidade'
        ),
        id_receita=receita_id,
        id_consulta__id_paciente=paciente
    )
    
    context = {
        'receita': receita,
        'paciente': paciente,
    }
    
    return render(request, 'core/patient_receita_detalhes.html', context)


# ==================== API ENDPOINTS ====================

@login_required
@role_required('paciente')
def patient_search_medicos(request):
    """API endpoint to search doctors by name or specialty"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    medicos = Medico.objects.select_related('id_utilizador', 'id_especialidade').filter(
        Q(id_utilizador__nome__icontains=query) | 
        Q(id_especialidade__nome_especialidade__icontains=query),
        id_utilizador__ativo=True
    ).order_by('id_utilizador__nome')[:10]
    
    results = [
        {
            'id': m.id_medico,
            'nome': m.id_utilizador.nome,
            'especialidade': m.id_especialidade.nome_especialidade if m.id_especialidade else 'N/A',
            'numero_ordem': m.numero_ordem if hasattr(m, 'numero_ordem') and m.numero_ordem else '',
            'text': f"Dr(a). {m.id_utilizador.nome} - {m.id_especialidade.nome_especialidade if m.id_especialidade else 'N/A'}"
        }
        for m in medicos
    ]
    
    return JsonResponse({'results': results})
