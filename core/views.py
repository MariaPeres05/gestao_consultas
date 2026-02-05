# core/views.py
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import datetime, timedelta
from django.db import connection, transaction

from .forms import LoginForm, RegisterForm, PacienteDetailsForm
from django.contrib.auth.decorators import login_required
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
            conta_inativa = False
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT ativo FROM \"core_utilizador\" WHERE email = %s LIMIT 1",
                    [email]
                )
                row = cursor.fetchone()
                if row and row[0] is False:
                    conta_inativa = True
            if conta_inativa:
                messages.error(request, "Conta desativada.")
            else:
                messages.error(request, "Email ou password incorretos.")
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
@role_required('paciente')
def update_paciente_details(request):
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_paciente_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        result = cursor.fetchone()
    
    if not result:
        messages.error(request, "Não foi possível encontrar o registo de paciente.")
        return redirect("patient_home")
    
    paciente_dict = {
        'id_paciente': result[0],
        'data_nasc': result[1],
        'genero': result[2],
        'morada': result[3] or '',
        'alergias': result[4] or '',
        'observacoes': result[5] or ''
    }
    
    if request.method == "POST":
        form = PacienteDetailsForm(request.POST)
        if form.is_valid():
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL atualizar_paciente(%s, %s, %s, %s, %s, %s)",
                        [
                            paciente_dict['id_paciente'],
                            form.cleaned_data["data_nasc"],
                            form.cleaned_data["genero"],
                            form.cleaned_data["morada"],
                            form.cleaned_data["alergias"],
                            form.cleaned_data["observacoes"]
                        ]
                    )
                messages.success(request, "✅ Dados atualizados com sucesso!")
                return redirect("patient_home")
            except Exception as e:
                messages.error(request, f"Erro ao atualizar dados: {str(e)}")
    else:
        initial_data = {
            "data_nasc": paciente_dict['data_nasc'],
            "genero": paciente_dict['genero'],
            "morada": paciente_dict['morada'],
            "alergias": paciente_dict['alergias'],
            "observacoes": paciente_dict['observacoes'],
        }
        form = PacienteDetailsForm(initial=initial_data)
    
    return render(request, "core/update_paciente_details.html", {
        "form": form,
        "paciente": paciente_dict,
    })

def register_view(request):
    from .email_utils import enviar_email_verificacao
    from datetime import date
    from django.db import connection
    
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL criar_utilizador_paciente(%s, %s, %s, %s, %s, %s, %s, %s)",
                        [
                            form.cleaned_data["nome"],
                            form.cleaned_data["email"],
                            form.cleaned_data["telefone"],
                            form.cleaned_data["password"],
                            date(2000, 1, 1),  # data_nasc default
                            "Não especificado",  # genero default
                            "",  # morada
                            ""   # alergias
                        ]
                    )
                
                # Buscar o utilizador criado para enviar email
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM obter_utilizador_por_email(%s)",
                        [form.cleaned_data["email"]]
                    )
                    user_result = cursor.fetchone()
                
                if user_result:
                    class UserLike:
                        def __init__(self, data):
                            self.id_utilizador = data[0]
                            self.nome = data[1]
                            self.email = data[2]
                            self.email_verified = data[8]
                    
                    user = UserLike(user_result)
                    
                    # Enviar email de verificação
                    if enviar_email_verificacao(user, request):
                        messages.success(request, "✅ Conta criada com sucesso! Verifique o seu email para ativar a conta.")
                    else:
                        messages.success(request, "Conta criada com sucesso! Pode fazer login.")
                else:
                    messages.success(request, "Conta criada com sucesso! Pode fazer login.")
                
                return redirect("login")
            except Exception as e:
                messages.error(request, f"Erro ao criar conta: {str(e)}")

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
    from django.db import connection
    
    try:
        # Verificar primeiro se já está verificado
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT email_verified FROM obter_utilizador_por_token(%s)",
                [token]
            )
            result = cursor.fetchone()
            
            if result and result[0]:  # Já verificado
                messages.info(request, "Este email já foi verificado anteriormente.")
                return redirect('login')
        
        # Chamar procedure para verificar email
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL verificar_email_utilizador(%s)",
                [token]
            )
        
        messages.success(request, "✅ Email verificado com sucesso! Pode agora fazer login.")
        return redirect('login')
        
    except Exception as e:
        error_msg = str(e)
        if 'Token inválido' in error_msg:
            messages.error(request, "Link de verificação inválido ou expirado.")
        else:
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
    system_name = "MediPulse"
    user = request.user
    user_name = getattr(user, "nome", user.email if user.is_authenticated else "")

    consultas_count = 0
    faturas_count = 0
    proxima_consulta = None
    
    if user.is_authenticated and user.role == 'paciente':
        # Usar função para obter estatísticas
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM obter_estatisticas_paciente(%s)",
                [user.id_utilizador]
            )
            result = cursor.fetchone()
            
            if result:
                consultas_count = result[0] or 0
                faturas_count = result[1] or 0
                if result[2] and result[3]:
                    proxima_consulta = f"{result[2]} às {result[3]}"

    context = {
        "system_name": system_name,
        "user_name": user_name,
        "user_email": getattr(user, "email", "") if user.is_authenticated else "",
        "consultas_count": consultas_count,
        "faturas_count": faturas_count,
        "proxima_consulta": proxima_consulta,
    }

    return render(request, "core/patient_home.html", context)


@login_required
@role_required('paciente')
def agendar_consulta(request):
    from django.db import connection
    
    if not request.user.is_authenticated:
        return redirect("login")

    # Obter ID do paciente
    with connection.cursor() as cursor:
        cursor.execute("SELECT obter_paciente_por_utilizador_id(%s)", [request.user.id_utilizador])
        result = cursor.fetchone()
    
    if not result or not result[0]:
        messages.error(request, "Não foi possível encontrar o registo de paciente.")
        return redirect("patient_home")
    
    paciente_id = result[0]

    if request.method == "POST":
        disp_id = request.POST.get("disponibilidade_id")
        hora_consulta_str = request.POST.get("hora_consulta")
        
        if not disp_id or not hora_consulta_str:
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect("marcar_consulta")
        
        try:
            hora_consulta = datetime.strptime(hora_consulta_str, "%H:%M").time()
            
            # Obter dados da disponibilidade
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT d.data, d.id_medico, d.id_unidade
                    FROM "DISPONIBILIDADE" d
                    WHERE d.id_disponibilidade = %s
                    AND d.status_slot IN ('disponivel', 'available')
                """, [disp_id])
                disp_data = cursor.fetchone()
                
                if not disp_data:
                    messages.error(request, "Disponibilidade não encontrada.")
                    return redirect("marcar_consulta")
                
                data_consulta = disp_data[0]
                id_medico = disp_data[1]
                id_unidade = disp_data[2]
                
                # Marcar consulta usando procedure
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "CALL marcar_consulta(%s, %s, %s, %s, %s)",
                            [paciente_id, id_medico, data_consulta, hora_consulta, "Consulta marcada via sistema"]
                        )
                    messages.success(request, "Consulta marcada com sucesso!")
                    return redirect("listar_consultas")
                    
                except Exception as e:
                    messages.error(request, f"Erro ao marcar consulta: {str(e)}")
                    return redirect("marcar_consulta")
            
        except Exception as e:
            messages.error(request, f"Erro ao processar dados: {str(e)}")
            return redirect("marcar_consulta")

    # GET: obter dados para formulário
    especialidade_id = request.GET.get("especialidade")
    unidade_id = request.GET.get("unidade")
    data_q = request.GET.get("data")
    
    # Obter listas usando funções
    with connection.cursor() as cursor:
        # Especialidades
        cursor.execute("SELECT * FROM listar_especialidades()")
        especialidades = [
            {'id_especialidade': row[0], 'nome_especialidade': row[1], 'descricao': row[2]}
            for row in cursor.fetchall()
        ]
        
        # Unidades
        cursor.execute("SELECT * FROM listar_unidades()")
        unidades = [
            {'id_unidade': row[0], 'nome_unidade': row[1], 'morada_unidade': row[2], 'tipo_unidade': row[3]}
            for row in cursor.fetchall()
        ]
        
        # Médicos com disponibilidade (via view vw_disponibilidades)
        medicos_query = """
            SELECT DISTINCT d.id_medico, d.medico_nome, COALESCE(d.nome_especialidade, 'Sem especialidade')
            FROM vw_disponibilidades d
            WHERE d.status_slot IN ('disponivel', 'available')
            AND d.data >= CURRENT_DATE
        """
        medicos_params = []
        if especialidade_id:
            medicos_query += " AND d.id_especialidade = %s"
            medicos_params.append(especialidade_id)
        if unidade_id:
            medicos_query += " AND d.id_unidade = %s"
            medicos_params.append(unidade_id)
        medicos_query += " ORDER BY d.medico_nome"

        cursor.execute(medicos_query, medicos_params)
        medicos = []
        for row in cursor.fetchall():
            medicos.append({
                'id_medico': row[0],
                'nome': row[1],
                'especialidade': row[2],
                'tem_disponibilidade': True
            })
        
        # Obter disponibilidades se médico e unidade/data foram selecionados
        disponibilidades = []
        medico_id = request.GET.get("medico")
        
        if medico_id and (unidade_id or data_q):
            query = """
                SELECT d.id_disponibilidade, d.data, d.hora_inicio, d.hora_fim,
                       d.duracao_slot, d.status_slot,
                       d.nome_unidade, d.medico_nome, COALESCE(d.nome_especialidade, 'Sem especialidade')
                FROM vw_disponibilidades d
                WHERE d.id_medico = %s
                AND d.status_slot IN ('disponivel', 'available')
                AND d.data >= CURRENT_DATE
            """
            params = [medico_id]
            
            if unidade_id:
                query += " AND d.id_unidade = %s"
                params.append(unidade_id)
            
            if data_q:
                query += " AND d.data = %s"
                params.append(data_q)
            
            query += " ORDER BY d.data, d.hora_inicio"
            
            cursor.execute(query, params)
            disp_rows = cursor.fetchall()

            # Pré-carregar consultas ocupadas por disponibilidade
            disp_ids = [r[0] for r in disp_rows]
            ocupados = {}
            if disp_ids:
                cursor.execute("""
                    SELECT id_disponibilidade, hora_consulta
                    FROM "CONSULTAS"
                    WHERE id_disponibilidade = ANY(%s)
                    AND estado NOT IN ('cancelada')
                """, [disp_ids])
                for d_id, hora in cursor.fetchall():
                    ocupados.setdefault(d_id, set()).add(hora)

            for row in disp_rows:
                disp_id = row[0]
                hora_inicio = row[2]
                hora_fim = row[3]
                duracao = row[4]

                # Gerar slots
                slots = []
                current_time = datetime.combine(row[1], hora_inicio)
                end_time = datetime.combine(row[1], hora_fim)
                ocupados_disp = ocupados.get(disp_id, set())
                while current_time < end_time:
                    slot_time = current_time.time()
                    slots.append({
                        'time': slot_time.strftime('%H:%M'),
                        'available': slot_time not in ocupados_disp
                    })
                    current_time += timedelta(minutes=duracao)

                disponibilidades.append({
                    'id_disponibilidade': row[0],
                    'data': row[1],
                    'hora_inicio': row[2],
                    'hora_fim': row[3],
                    'duracao_slot': row[4],
                    'status_slot': row[5],
                    'unidade_nome': row[6],
                    'medico_nome': row[7],
                    'especialidade_nome': row[8],
                    'slots': slots
                })

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
    from django.db import connection
    
    id_medico = request.GET.get("medico")
    unidade_id = request.GET.get("unidade")
    
    query = """
        SELECT d.id_disponibilidade, d.data, d.hora_inicio, d.hora_fim, 
               u.nome as medico_nome, un.nome_unidade
        FROM "DISPONIBILIDADE" d
        JOIN "MEDICOS" m ON d.id_medico = m.id_medico
        JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
        LEFT JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
        WHERE d.status_slot NOT ILIKE 'booked'
    """
    params = []
    
    if id_medico:
        query += " AND d.id_medico = %s"
        params.append(id_medico)
    if unidade_id:
        query += " AND d.id_unidade = %s"
        params.append(unidade_id)
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    
    events = []
    for row in rows:
        start = None
        end = None
        try:
            start = f"{row[1].isoformat()}T{row[2].strftime('%H:%M:%S')}"
        except Exception:
            start = None
        try:
            if row[3]:
                end = f"{row[1].isoformat()}T{row[3].strftime('%H:%M:%S')}"
        except Exception:
            end = None

        title = f"{row[4]}"
        events.append({
            "id": row[0],
            "title": title,
            "start": start,
            "end": end,
            "extendedProps": {
                "id_medico": id_medico,
                "unidade": row[5],
            },
        })

    return JsonResponse(events, safe=False)


def listar_consultas(request):
    from django.db import connection
    
    if not request.user.is_authenticated:
        return redirect("login")

    # Obter paciente usando função
    paciente_id = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT obter_paciente_por_utilizador_id(%s)", [request.user.id_utilizador])
        result = cursor.fetchone()
        if result:
            paciente_id = result[0]
    
    if not paciente_id:
        messages.error(request, "Não foi possível encontrar o registo de paciente.")
        return redirect("patient_home")

    # POST: cancelar consulta
    if request.method == "POST":
        action = request.POST.get("action")
        consulta_id = request.POST.get("consulta_id")
        if action == "cancel" and consulta_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL cancelar_consulta(%s, %s, %s, %s)",
                        [consulta_id, "Cancelada pelo paciente", request.user.id_utilizador, 'paciente']
                    )
                messages.success(request, "Consulta cancelada com sucesso.")
            except Exception as e:
                messages.error(request, f"Erro ao cancelar consulta: {str(e)}")
            return redirect("listar_consultas")

    # GET: listar consultas usando view vw_consultas_completas
    consultas_list = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id_consulta,
                data_consulta,
                hora_consulta,
                estado,
                motivo,
                medico_nome,
                nome_unidade,
                especialidade_descricao,
                paciente_presente,
                hora_checkin
            FROM vw_consultas_completas
            WHERE id_paciente = %s
            ORDER BY data_consulta DESC, hora_consulta DESC
        """, [paciente_id])
        
        from django.utils import timezone
        
        for row in cursor.fetchall():
            try:
                consulta_datetime = datetime.combine(row[1], row[2])
                consulta_datetime = timezone.make_aware(consulta_datetime)
                tempo_restante = consulta_datetime - timezone.now()
            except:
                tempo_restante = timedelta(days=1)
            
            consultas_list.append({
                'id_consulta': row[0],
                'data_consulta': row[1],
                'hora_consulta': row[2],
                'estado': row[3],
                'motivo': row[4],
                'medico_nome': row[5] if row[5] else "Não atribuído",
                'unidade_nome': row[6] if row[6] else "Não especificada",
                'especialidade': row[7] if row[7] else "Sem especialidade",
                'paciente_presente': row[8],
                'hora_checkin': row[9],
                'can_cancel_24h': tempo_restante >= timedelta(hours=24) and row[3] in ('agendada', 'confirmada', 'marcada')
            })

    context = {"consultas": consultas_list, "paciente_id": paciente_id}
    return render(request, "core/patient_consultas.html", context)

@login_required
@role_required('paciente')
def paciente_receitas(request, consulta_id):
    """Mostra as receitas associadas a uma consulta específica do paciente"""
    from django.db import connection
    
    # Verificar se a consulta pertence ao paciente
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id_consulta, c.data_consulta, c.hora_consulta, c.estado, c.motivo,
                   u.nome as medico_nome
            FROM "CONSULTAS" c
            JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
            JOIN "MEDICOS" m ON c.id_medico = m.id_medico
            JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
            WHERE c.id_consulta = %s AND p.id_utilizador = %s
        """, [consulta_id, request.user.id_utilizador])
        consulta_row = cursor.fetchone()
        
        if not consulta_row:
            return redirect('patient_home')
        
        # Obter receitas
        cursor.execute("""
            SELECT id_receita, medicamento, dosagem, instrucoes, data_prescricao
            FROM "RECEITAS"
            WHERE id_consulta = %s
            ORDER BY data_prescricao
        """, [consulta_id])
        receitas_rows = cursor.fetchall()
    
    consulta = {
        'id_consulta': consulta_row[0],
        'data_consulta': consulta_row[1],
        'hora_consulta': consulta_row[2],
        'estado': consulta_row[3],
        'motivo': consulta_row[4],
        'medico_nome': consulta_row[5],
    }
    
    receitas = [
        {
            'id_receita': row[0],
            'medicamento': row[1],
            'dosagem': row[2],
            'instrucoes': row[3],
            'data_prescricao': row[4],
        }
        for row in receitas_rows
    ]
    
    context = {
        'consulta': consulta,
        'receitas': receitas,
    }
    
    return render(request, 'core/patient_receitas.html', context)

@login_required
@role_required('paciente')
def paciente_confirmar_consulta(request, consulta_id):
    """Paciente confirma uma consulta agendada"""
    from django.db import connection
    
    # Verificar se a consulta pertence ao paciente
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM "CONSULTAS" c
            JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
            WHERE c.id_consulta = %s AND p.id_utilizador = %s
        """, [consulta_id, request.user.id_utilizador])
        if not cursor.fetchone():
            messages.error(request, "Consulta não encontrada.")
            return redirect('listar_consultas')
    
    # Chamar procedure para confirmar consulta
    try:
        with connection.cursor() as cursor:
            cursor.execute("CALL confirmar_consulta(%s, %s)", [
                consulta_id,
                'paciente'
            ])
        messages.success(request, "Consulta confirmada com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao confirmar consulta: {str(e)}")
    
    return redirect('listar_consultas')


@login_required
@role_required('paciente')
def paciente_recusar_consulta(request, consulta_id):
    """Paciente recusa uma consulta agendada"""
    from django.db import connection
    
    # Verificar se a consulta pertence ao paciente
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM "CONSULTAS" c
            JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
            WHERE c.id_consulta = %s AND p.id_utilizador = %s
        """, [consulta_id, request.user.id_utilizador])
        if not cursor.fetchone():
            messages.error(request, "Consulta não encontrada.")
            return redirect('listar_consultas')
    
    # Chamar procedure para cancelar consulta
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL cancelar_consulta(%s, %s, %s, %s)",
                [consulta_id, "Recusada pelo paciente", request.user.id_utilizador, 'paciente']
            )
        messages.success(request, "Consulta recusada.")
    except Exception as e:
        messages.error(request, f"Erro ao recusar consulta: {str(e)}")
    
    return redirect('listar_consultas')


@login_required
@role_required('paciente')
def paciente_cancelar_consulta(request, consulta_id):
    """Paciente cancela uma consulta confirmada usando procedure"""
    from django.db import connection
    
    # Chamar procedure para cancelar consulta
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL cancelar_consulta(%s, %s, %s, %s)",
                [
                    consulta_id,
                    request.POST.get("motivo", "Cancelada pelo paciente"),
                    request.user.id_utilizador,
                    'paciente'
                ]
            )
        messages.success(request, "Consulta cancelada com sucesso.")
    except Exception as e:
        # Extrair mensagem de erro amigável
        error_msg = str(e)
        if "24 horas" in error_msg:
            messages.error(request, "Não é possível cancelar consultas com menos de 24 horas de antecedência.")
        elif "já está cancelada" in error_msg:
            messages.info(request, "Esta consulta já está cancelada.")
        elif "não pode ser cancelada" in error_msg:
            messages.error(request, "Esta consulta não pode ser cancelada.")
        else:
            messages.error(request, f"Erro ao cancelar consulta: {error_msg}")
    
    return redirect('listar_consultas')


def listar_faturas(request):
    """Lista e gere as faturas do paciente autenticado.

    - GET: mostra as faturas associadas às consultas do paciente
    - POST: permite marcar uma fatura como paga (define `estado='paga'` e `data_pagamento`)
    """
    if not request.user.is_authenticated:
        return redirect("login")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_paciente FROM "PACIENTES"
            WHERE id_utilizador = %s
        """, [request.user.id_utilizador])
        paciente_row = cursor.fetchone()
        if not paciente_row:
            messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
            return redirect("patient_home")
        paciente_id = paciente_row[0]

    if request.method == "POST":
        action = request.POST.get("action")
        fatura_id = request.POST.get("fatura_id")
        if action == "pay" and fatura_id:
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Verificar se a fatura pertence ao paciente e não está paga
                        cursor.execute("""
                            SELECT estado FROM "FATURAS"
                            WHERE id_fatura = %s AND id_consulta IN (
                                SELECT id_consulta FROM "CONSULTAS" WHERE id_paciente = %s
                            )
                        """, [fatura_id, paciente_id])
                        fatura_row = cursor.fetchone()
                        if not fatura_row:
                            messages.error(request, "Fatura não encontrada.")
                            return redirect("listar_faturas")
                        if fatura_row[0].lower() == "paga":
                            messages.info(request, "A fatura já está paga.")
                            return redirect("listar_faturas")
                        
                        # Marcar como paga
                        from django.utils import timezone
                        data_pagamento = timezone.now()
                        metodo = request.POST.get("metodo_pagamento")
                        cursor.execute("""
                            UPDATE "FATURAS"
                            SET estado = 'paga', data_pagamento = %s, metodo_pagamento = %s
                            WHERE id_fatura = %s
                        """, [data_pagamento, metodo or None, fatura_id])
                        messages.success(request, "Fatura marcada como paga.")
            except Exception as e:
                messages.error(request, f"Erro ao processar pagamento: {str(e)}")

        return redirect("listar_faturas")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT f.id_fatura, f.valor, f.estado, f.data_pagamento, f.metodo_pagamento,
                   c.data_consulta, c.hora_consulta,
                   u.nome as medico_nome
            FROM "FATURAS" f
            JOIN "CONSULTAS" c ON f.id_consulta = c.id_consulta
            JOIN "MEDICOS" med ON c.id_medico = med.id_medico
            JOIN "core_utilizador" u ON med.id_utilizador = u.id_utilizador
            WHERE c.id_paciente = %s
            ORDER BY f.data_pagamento DESC NULLS FIRST, f.id_fatura DESC
        """, [paciente_id])
        faturas_rows = cursor.fetchall()
        faturas = []
        for row in faturas_rows:
            faturas.append({
                'id_fatura': row[0],
                'valor': row[1],
                'estado': row[2],
                'data_pagamento': row[3],
                'metodo_pagamento': row[4],
                'consulta': {
                    'data_consulta': row[5],
                    'hora_consulta': row[6],
                    'medico': {'id_utilizador': {'nome': row[7]}}
                }
            })

    context = {"faturas": faturas, "paciente": {'id_paciente': paciente_id}}
    return render(request, "core/patient_faturas.html", context)


@login_required
def patient_perfil_editar(request):
    if request.user.role != 'paciente':
        messages.error(request, "Acesso negado.")
        return redirect('home')
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()
        
        # Validações
        if password and password != password_confirm:
            messages.error(request, "As passwords não coincidem.")
            return render(request, 'core/patient_perfil.html', {'user': request.user})
        
        if password and len(password) < 6:
            messages.error(request, "A password deve ter pelo menos 6 caracteres.")
            return render(request, 'core/patient_perfil.html', {'user': request.user})
        
        # Chamar procedure
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                if password:
                    cursor.execute(
                        "CALL atualizar_perfil_utilizador(%s, %s, %s, %s)",
                        [request.user.id_utilizador, nome, telefone, password]
                    )
                    messages.success(request, "Perfil atualizado com sucesso! Faça login novamente.")
                    logout(request)
                    return redirect('login')
                else:
                    cursor.execute(
                        "CALL atualizar_perfil_utilizador(%s, %s, %s, NULL)",
                        [request.user.id_utilizador, nome, telefone]
                    )
                    messages.success(request, "Perfil atualizado com sucesso!")
                    return redirect('patient_perfil_editar')
                    
        except Exception as e:
            messages.error(request, f"Erro ao atualizar perfil: {str(e)}")
    
    context = {'user': request.user}
    return render(request, 'core/patient_perfil.html', context)


@login_required
def reagendar_consulta(request, consulta_id):
    """Permite reagendar uma consulta existente para uma nova disponibilidade."""
    if request.user.role != 'paciente':
        messages.error(request, "Acesso negado.")
        return redirect('home')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_paciente FROM "PACIENTES"
            WHERE id_utilizador = %s
        """, [request.user.id_utilizador])
        paciente_row = cursor.fetchone()
        if not paciente_row:
            messages.error(request, "Não foi possível encontrar o registo de paciente associado ao utilizador.")
            return redirect("patient_home")
        paciente_id = paciente_row[0]
    
    # Buscar consulta original
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id_consulta, c.estado, c.data_consulta, c.hora_consulta,
                   m.id_medico, u.nome as medico_nome, e.nome as especialidade_nome,
                   d.id_unidade, un.nome as unidade_nome
            FROM "CONSULTAS" c
            JOIN "MEDICOS" m ON c.id_medico = m.id_medico
            JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
            JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
            LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
            LEFT JOIN "UNIDADES" un ON d.id_unidade = un.id_unidade
            WHERE c.id_consulta = %s AND c.id_paciente = %s
        """, [consulta_id, paciente_id])
        consulta_row = cursor.fetchone()
        if not consulta_row:
            messages.error(request, "Consulta não encontrada.")
            return redirect('listar_consultas')
        
        consulta = {
            'id_consulta': consulta_row[0],
            'estado': consulta_row[1],
            'data_consulta': consulta_row[2],
            'hora_consulta': consulta_row[3],
            'id_medico': {'id_medico': consulta_row[4], 'id_utilizador': {'nome': consulta_row[5]}, 'id_especialidade': {'nome': consulta_row[6]}},
            'id_disponibilidade': {'id_unidade': {'nome': consulta_row[7]}}
        }
    
    # Só permitir reagendar se estiver em estado marcada ou agendada
    if consulta['estado'].lower() not in ('marcada', 'agendada'):
        messages.error(request, "Esta consulta não pode ser reagendada.")
        return redirect('listar_consultas')
    
    if request.method == 'POST':
        nova_disp_id = request.POST.get('nova_disponibilidade')
        if nova_disp_id:
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("CALL reagendar_consulta(%s, %s, %s)", [consulta_id, nova_disp_id, request.user.id_utilizador])
                        messages.success(request, "Consulta reagendada com sucesso!")
                        return redirect('listar_consultas')
            except Exception as e:
                messages.error(request, f"Erro ao reagendar: {str(e)}")
        else:
            messages.error(request, "Por favor, selecione uma nova data/hora.")
    
    # Buscar disponibilidades do mesmo médico (ou da mesma especialidade)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT d.id_disponibilidade, d.data, d.hora_inicio, d.hora_fim,
                   u.nome as unidade_nome
            FROM "DISPONIBILIDADE" d
            JOIN "UNIDADES" u ON d.id_unidade = u.id_unidade
            WHERE d.id_medico = %s AND d.status_slot IN ('available', 'disponivel')
            AND (d.data > %s OR (d.data = %s AND d.hora_inicio > %s))
            ORDER BY d.data, d.hora_inicio
            LIMIT 50
        """, [consulta['id_medico']['id_medico'], consulta['data_consulta'], consulta['data_consulta'], consulta['hora_consulta']])
        disponibilidades_rows = cursor.fetchall()
        disponibilidades = []
        for row in disponibilidades_rows:
            disponibilidades.append({
                'id_disponibilidade': row[0],
                'data': row[1],
                'hora_inicio': row[2],
                'hora_fim': row[3],
                'id_unidade': {'nome': row[4]}
            })
    
    context = {
        'consulta': consulta,
        'disponibilidades': disponibilidades,
        'paciente': {'id_paciente': paciente_id}
    }
    return render(request, 'core/patient_reagendar.html', context)


def home(request):
    """Página inicial pública do sistema de gestão de consultas.

    Passa o nome do sistema para o template.
    """
    system_name = "MediPulse"
    return render(request, "core/home.html", {"system_name": system_name})
