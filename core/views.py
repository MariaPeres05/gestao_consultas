from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import Receitas, Consultas, Faturas, Horarios, Medicos, Especialidades
from .forms import ReceitaForm, FaturaForm
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .forms import LoginForm, RegistroForm
import json

def home(request):
    return render(request, 'core/home.html')

# =========================
# CONSULTAS - NOVO SISTEMA DE AGENDAMENTO
# =========================


def marcar_consulta(request):
    """Nova view para marcar consultas com interface moderna"""
    try:
        # Obter especialidades para o dropdown
        with connection.cursor() as cursor:
            cursor.execute('SELECT "ID_ESPECIALIDADES", "NOME_ESPECIALIDADE" FROM "ESPECIALIDADES" ORDER BY "NOME_ESPECIALIDADE"')
            especialidades = cursor.fetchall()
            
            # Obter médicos com informações básicas
            cursor.execute("""
                SELECT m."ID_MEDICO", m."ID_UTILIZADOR", u."NOMEREGIAO" as nome, 
                       STRING_AGG(es."NOME_ESPECIALIDADE", ', ') as especialidades
                FROM "MEDICOS" m
                JOIN "UTILIZADOR" u ON m."ID_UTILIZADOR" = u."ID_UTILIZADOR"
                LEFT JOIN "ESPECIALIZAM_SE" esm ON m."ID_UTILIZADOR" = esm."ID_UTILIZADOR" AND m."ID_MEDICO" = esm."ID_MEDICO"
                LEFT JOIN "ESPECIALIDADES" es ON esm."ID_ESPECIALIDADES" = es."ID_ESPECIALIDADES"
                GROUP BY m."ID_MEDICO", m."ID_UTILIZADOR", u."NOMEREGIAO"
            """)
            medicos_raw = cursor.fetchall()
            
            # Converter médicos para formato adequado
            medicos = []
            for medico in medicos_raw:
                medicos.append({
                    'id_medico': medico[0],
                    'id_utilizador': medico[1],
                    'nome': medico[2],
                    'especialidades': medico[3] or 'Sem especialidade'
                })
            
            # Obter alguns horários disponíveis para exemplo
            cursor.execute("""
                SELECT h."ID_HORARIO", h."HORA_INICIO", h."HORA_FIM", h."DIAS_SEMANA"
                FROM "HORARIOS" h
                WHERE h."DATA_FIM" >= CURRENT_DATE
                LIMIT 10
            """)
            horarios_disponiveis = cursor.fetchall()

    except Exception as e:
        especialidades = []
        medicos = []
        horarios_disponiveis = []
        messages.error(request, f'Erro ao carregar dados: {str(e)}')

    if request.method == 'POST':
        try:
            # Extrair dados do formulário moderno
            id_horario = request.POST.get('id_horario')
            id_medico = request.POST.get('id_medico')
            data_consulta = request.POST.get('data_consulta')
            hora_inicio = request.POST.get('hora_inicio')
            motivo = request.POST.get('motivo', 'Consulta de rotina')
            
            # Validar dados
            if not all([id_horario, id_medico, data_consulta, hora_inicio]):
                messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')
                return render(request, 'core/marcar_consulta.html', {
                    'especialidades': especialidades,
                    'medicos': medicos,
                    'horarios_disponiveis': horarios_disponiveis
                })
            
            # Combinar data e hora
            inicio_datetime = f"{data_consulta} {hora_inicio}"
            
            # Calcular fim (1 hora de duração padrão)
            inicio_obj = datetime.strptime(inicio_datetime, '%Y-%m-%d %H:%M')
            fim_obj = inicio_obj + timedelta(hours=1)
            fim_datetime = fim_obj.strftime('%Y-%m-%d %H:%M')
            
            # Tentar usar o stored procedure primeiro
            try:
                with connection.cursor() as cursor:
                    cursor.callproc('SP_AGENDAR_CONSULTA', [
                        None,  # p_id_consulta
                        int(id_horario),
                        inicio_datetime,
                        fim_datetime,
                        'agendada'
                    ])
                    
                messages.success(request, 'Consulta agendada com sucesso usando procedimento armazenado!')
                return redirect('listar_consultas')
                
            except Exception as sp_error:
                # Fallback para inserção direta
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO "CONSULTAS" (
                            "ID_HORARIO", "INICIO", "FIM", "ESTADO", "MOTIVO"
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, [
                        int(id_horario),
                        inicio_datetime,
                        fim_datetime,
                        'agendada',
                        motivo
                    ])
                
                messages.success(request, 'Consulta agendada com sucesso!')
                return redirect('listar_consultas')
                
        except Exception as e:
            messages.error(request, f'Erro ao agendar consulta: {str(e)}')
            return render(request, 'core/marcar_consulta.html', {
                'especialidades': especialidades,
                'medicos': medicos,
                'horarios_disponiveis': horarios_disponiveis,
                'error': f'Erro ao agendar consulta: {str(e)}'
            })
    
    # GET request - mostrar formulário
    return render(request, 'core/marcar_consulta.html', {
        'especialidades': especialidades,
        'medicos': medicos,
        'horarios_disponiveis': horarios_disponiveis,
        'titulo': 'Agendar Nova Consulta'
    })

# APIs para AJAX
@login_required
def api_medicos_por_especialidade(request, especialidade_id):
    """API para carregar médicos por especialidade"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT m."ID_MEDICO", m."ID_UTILIZADOR", u."NOMEREGIAO" as nome,
                       STRING_AGG(es."NOME_ESPECIALIDADE", ', ') as especialidades,
                       STRING_AGG(DISTINCT us."NOME_UNIDADE", ', ') as unidades
                FROM "MEDICOS" m
                JOIN "UTILIZADOR" u ON m."ID_UTILIZADOR" = u."ID_UTILIZADOR"
                JOIN "ESPECIALIZAM_SE" esm ON m."ID_UTILIZADOR" = esm."ID_UTILIZADOR" AND m."ID_MEDICO" = esm."ID_MEDICO"
                JOIN "ESPECIALIDADES" es ON esm."ID_ESPECIALIDADES" = es."ID_ESPECIALIDADES"
                LEFT JOIN "TEEM_COMO_HORARIO" tch ON m."ID_UTILIZADOR" = tch."ID_UTILIZADOR" AND m."ID_MEDICO" = tch."ID_MEDICO"
                LEFT JOIN "TEM_COMO_DISPONIBILIDADE" tcd ON tch."ID_HORARIO" = tcd."ID_HORARIO"
                LEFT JOIN "UNIDADE_DE_SAUDE" us ON tcd."ID_UNIDADE" = us."ID_UNIDADE"
                WHERE es."ID_ESPECIALIDADES" = %s
                GROUP BY m."ID_MEDICO", m."ID_UTILIZADOR", u."NOMEREGIAO"
            """, [especialidade_id])
            
            medicos_raw = cursor.fetchall()
            
            medicos_data = []
            for medico in medicos_raw:
                medicos_data.append({
                    'id_medico': medico[0],
                    'id_utilizador': medico[1],
                    'nome': medico[2],
                    'especialidades': medico[3] or 'Sem especialidade',
                    'unidades': medico[4] or 'Unidade Central'
                })
            
            return JsonResponse({'medicos': medicos_data})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_horarios_por_medico(request, medico_id):
    """API para carregar horários disponíveis por médico"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT h."ID_HORARIO", h."HORA_INICIO", h."HORA_FIM", 
                       h."DIAS_SEMANA", h."DATA_INICIO", h."DATA_FIM"
                FROM "HORARIOS" h
                JOIN "TEEM_COMO_HORARIO" tch ON h."ID_HORARIO" = tch."ID_HORARIO"
                WHERE tch."ID_MEDICO" = %s 
                AND h."DATA_FIM" >= CURRENT_DATE
                AND h."ID_HORARIO" NOT IN (
                    SELECT c."ID_HORARIO" 
                    FROM "CONSULTAS" c 
                    WHERE c."ESTADO" IN ('agendada', 'confirmada')
                    AND c."INICIO" >= CURRENT_DATE
                )
                ORDER BY h."DATA_INICIO", h."HORA_INICIO"
            """, [medico_id])
            
            horarios = []
            for row in cursor.fetchall():
                horarios.append({
                    'id_horario': row[0],
                    'hora_inicio': row[1],
                    'hora_fim': row[2],
                    'dias_semana': row[3],
                    'data_inicio': row[4].strftime('%d/%m/%Y') if row[4] else '',
                    'data_fim': row[5].strftime('%d/%m/%Y') if row[5] else ''
                })
            
            return JsonResponse({'horarios': horarios})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # Processamento manual do login (sem usar forms do Django)
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # Usar nosso backend personalizado
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo de volta, {user.nomeregiao}!')
                
                # Redirecionar para a próxima página ou home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Email/Nome ou password inválidos.')
        else:
            messages.error(request, 'Por favor, preencha todos os campos.')
    
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Sessão terminada com sucesso.')
    return redirect('home')

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Criar perfil específico baseado no role
            if user.role == 1:  # Paciente
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO "PACIENTES" (
                            "ID_UTILIZADOR", "NOMEREGIAO", "EMAIL", "TELEFONE", "N_UTENTE", "SENHA",
                            "ROLE", "DATA_REGISTO", "ATIVO", "DATA_NASC", "GENERO", "MORADA"
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 1, %s, %s, %s)
                    """, [
                        user.id_utilizador,
                        user.nomeregiao,
                        user.email,
                        user.telefone,
                        user.n_utente,
                        user.password,  # Já está hasheada
                        user.role,
                        '2000-01-01',  # Data padrão
                        'Não especificado',  # Género padrão
                        ''  # Morada vazia
                    ])
            
            messages.success(request, 'Conta criada com sucesso! Faça login.')
            return redirect('login')
    else:
        form = RegistroForm()
    
    return render(request, 'core/registro.html', {'form': form})

# Modifique a home view para verificar autenticação
def home(request):
    context = {}
    if request.user.is_authenticated:
        context['user'] = request.user
        # Adicionar informações específicas do perfil
        if hasattr(request.user, 'pacientes'):
            context['perfil'] = request.user.pacientes
        elif hasattr(request.user, 'medicos'):
            context['perfil'] = request.user.medicos
    return render(request, 'core/home.html', context)

# =========================
# CONSULTAS - MANTENDO COMPATIBILIDADE
# =========================

def listar_consultas(request):
    """Listar consultas (mantido para compatibilidade)"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.*, h."HORA_INICIO", h."HORA_FIM", h."DURACAO",
                       u."NOMEREGIAO" as nome_medico
                FROM "CONSULTAS" c 
                LEFT JOIN "HORARIOS" h ON c."ID_HORARIO" = h."ID_HORARIO"
                LEFT JOIN "TEEM_COMO_HORARIO" tch ON h."ID_HORARIO" = tch."ID_HORARIO"
                LEFT JOIN "MEDICOS" m ON tch."ID_UTILIZADOR" = m."ID_UTILIZADOR" AND tch."ID_MEDICO" = m."ID_MEDICO"
                LEFT JOIN "UTILIZADOR" u ON m."ID_UTILIZADOR" = u."ID_UTILIZADOR"
                ORDER BY c."INICIO" DESC
                LIMIT 50
            """)
            consultas = cursor.fetchall()
        
        if consultas:
            colunas = [col[0] for col in cursor.description]
            consultas_dict = [dict(zip(colunas, row)) for row in consultas]
        else:
            consultas_dict = []
        
        return render(request, 'core/lista_consultas.html', {
            'consultas': consultas_dict,
            'total': len(consultas_dict),
            'titulo': 'Lista de Consultas'
        })
    except Exception as e:
        return render(request, 'core/lista_consultas.html', {
            'error': f'Erro ao carregar consultas: {str(e)}',
            'consultas': [],
            'total': 0,
            'titulo': 'Lista de Consultas'
        })

def inserir_consulta(request):
    """View antiga - redireciona para a nova"""
    messages.info(request, 'Utilize o novo sistema de agendamento de consultas.')
    return redirect('marcar_consulta')

# =========================
# PACIENTES - CRUD COMPLETO (MANTIDO)
# =========================

def listar_pacientes(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.*, u."NOMEREGIAO", u."EMAIL", u."TELEFONE", u."N_UTENTE"
                FROM "PACIENTES" p 
                JOIN "UTILIZADOR" u ON p."ID_UTILIZADOR" = u."ID_UTILIZADOR"
                LIMIT 50
            """)
            pacientes = cursor.fetchall()
        
        if pacientes:
            colunas = [col[0] for col in cursor.description]
            pacientes_dict = [dict(zip(colunas, row)) for row in pacientes]
        else:
            pacientes_dict = []
        
        return render(request, 'core/lista_pacientes.html', {
            'pacientes': pacientes_dict,
            'total': len(pacientes_dict)
        })
    except Exception as e:
        return render(request, 'core/lista_pacientes.html', {
            'error': f'Erro ao carregar pacientes: {str(e)}',
            'pacientes': [],
            'total': 0
        })

def inserir_paciente(request):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO "UTILIZADOR" (
                        "NOMEREGIAO", "EMAIL", "TELEFONE", "N_UTENTE", "SENHA", 
                        "ROLE", "DATA_REGISTO", "ATIVO"
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), 1)
                    RETURNING "ID_UTILIZADOR"
                """, [
                    request.POST['nome'],
                    request.POST['email'],
                    request.POST['telefone'],
                    request.POST['n_utente'],
                    request.POST['senha'],
                    1
                ])
                
                id_utilizador = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO "PACIENTES" (
                        "ID_UTILIZADOR", "NOMEREGIAO", "EMAIL", "TELEFONE", "N_UTENTE", "SENHA",
                        "ROLE", "DATA_REGISTO", "ATIVO", "DATA_NASC", "GENERO", "MORADA", "ALERGIAS", "OBSERVACOES"
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 1, %s, %s, %s, %s, %s)
                """, [
                    id_utilizador,
                    request.POST['nome'],
                    request.POST['email'],
                    request.POST['telefone'],
                    request.POST['n_utente'],
                    request.POST['senha'],
                    1,
                    request.POST['data_nasc'],
                    request.POST['genero'],
                    request.POST.get('morada', ''),
                    request.POST.get('alergias', ''),
                    request.POST.get('observacoes', '')
                ])
            
            return redirect('/pacientes/')
                
        except Exception as e:
            return render(request, 'core/inserir_paciente.html', {
                'error': f'Erro ao registar paciente: {str(e)}'
            })
    
    return render(request, 'core/inserir_paciente.html')

# =========================
# PROCEDIMENTOS ARMAZENADOS (MANTIDO)
# =========================

def usar_procedimento_agendar(request):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.callproc('"SP_AGENDAR_CONSULTA"', [
                    request.POST.get('id_consulta', 0) or 0,
                    request.POST['id_horario'],
                    request.POST['inicio'],
                    request.POST['fim'],
                    request.POST['estado']
                ])
            
            return redirect('/consultas/')
                
        except Exception as e:
            return render(request, 'core/usar_procedimento.html', {
                'error': f'Erro ao usar procedimento: {str(e)}'
            })
    
    return render(request, 'core/usar_procedimento.html')

# =========================
# VISTAS (VIEWS) (MANTIDO)
# =========================

def usar_vista_faturas(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM "V_FATURAS_PUBLICO" LIMIT 20')
            faturas = cursor.fetchall()
        
        if faturas:
            colunas = [col[0] for col in cursor.description]
            faturas_dict = [dict(zip(colunas, row)) for row in faturas]
        else:
            faturas_dict = []
        
        return render(request, 'core/vista_faturas.html', {
            'faturas': faturas_dict,
            'total': len(faturas_dict)
        })
    except Exception as e:
        return render(request, 'core/vista_faturas.html', {
            'error': f'Erro ao carregar vista: {str(e)}',
            'faturas': [],
            'total': 0
        })

# =========================
# RECEITAS - CRUD COMPLETO
# =========================

def listar_receitas(request):
    """Listar todas as receitas."""
    try:
        # Tentar usar ORM primeiro
        receitas = Receitas.objects.select_related('id_consultas', 'id_fatura').all().order_by('-data_prescricao')
        
        return render(request, 'core/listar_receitas.html', {
            'receitas': receitas,
            'titulo': 'Lista de Receitas',
            'total': receitas.count()
        })
        
    except Exception as e:
        # Fallback para SQL raw
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.*, c."ID_CONSULTAS" as consulta_id
                    FROM "RECEITAS" r 
                    JOIN "CONSULTAS" c ON r."ID_CONSULTAS" = c."ID_CONSULTAS"
                    ORDER BY r."DATA_PRESCRICAO" DESC
                """)
                receitas_raw = cursor.fetchall()
                
                if receitas_raw:
                    colunas = [col[0] for col in cursor.description]
                    receitas_dict = [dict(zip(colunas, row)) for row in receitas_raw]
                else:
                    receitas_dict = []
                    
                return render(request, 'core/listar_receitas.html', {
                    'receitas': receitas_dict,
                    'titulo': 'Lista de Receitas',
                    'total': len(receitas_dict)
                })
                
        except Exception as e2:
            return render(request, 'core/listar_receitas.html', {
                'error': f'Erro ao carregar receitas: {str(e2)}',
                'receitas': [],
                'total': 0,
                'titulo': 'Lista de Receitas'
            })

def inserir_receita(request):
    """Inserir nova receita."""
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO "RECEITAS" (
                        "ID_CONSULTAS", "ID_FATURA", "MEDICAMENTO", "DOSAGEM", 
                        "INSTRUCOES", "DATA_PRESCRICAO"
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    request.POST['id_consultas'],
                    request.POST['id_fatura'],
                    request.POST['medicamento'],
                    request.POST['dosagem'],
                    request.POST.get('instrucoes', ''),
                    request.POST['data_prescricao']
                ])
            
            messages.success(request, 'Receita criada com sucesso!')
            return redirect('listar_receitas')
                
        except Exception as e:
            # Carregar consultas e faturas para o dropdown
            with connection.cursor() as cursor:
                cursor.execute('SELECT "ID_CONSULTAS" FROM "CONSULTAS" ORDER BY "ID_CONSULTAS"')
                consultas = cursor.fetchall()
                
                cursor.execute('SELECT "ID_FATURA" FROM "FATURAS" ORDER BY "ID_FATURA"')
                faturas = cursor.fetchall()
            
            return render(request, 'core/inserir_receita.html', {
                'error': f'Erro ao criar receita: {str(e)}',
                'consultas': consultas,
                'faturas': faturas,
                'titulo': 'Nova Receita'
            })
    
    # GET request - carregar consultas e faturas disponíveis
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT "ID_CONSULTAS" FROM "CONSULTAS" ORDER BY "ID_CONSULTAS"')
            consultas = cursor.fetchall()
            
            cursor.execute('SELECT "ID_FATURA" FROM "FATURAS" ORDER BY "ID_FATURA"')
            faturas = cursor.fetchall()
    except Exception as e:
        consultas = []
        faturas = []
    
    return render(request, 'core/inserir_receita.html', {
        'consultas': consultas,
        'faturas': faturas,
        'titulo': 'Nova Receita'
    })

def detalhes_receita(request, id_receita):
    """Mostrar detalhes de uma receita específica."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, c."ID_CONSULTAS", f."ID_FATURA"
                FROM "RECEITAS" r 
                LEFT JOIN "CONSULTAS" c ON r."ID_CONSULTAS" = c."ID_CONSULTAS"
                LEFT JOIN "FATURAS" f ON r."ID_FATURA" = f."ID_FATURA"
                WHERE r."ID_RECEITA" = %s
            """, [id_receita])
            
            receita_data = cursor.fetchone()
            
            if receita_data:
                colunas = [col[0] for col in cursor.description]
                receita = dict(zip(colunas, receita_data))
            else:
                receita = None
        
        if not receita:
            messages.error(request, 'Receita não encontrada.')
            return redirect('listar_receitas')
        
        return render(request, 'core/detalhes_receita.html', {
            'receita': receita,
            'titulo': f'Detalhes da Receita #{id_receita}'
        })
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar receita: {str(e)}')
        return redirect('listar_receitas')

def editar_receita(request, id_receita):
    """Editar uma receita existente."""
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE "RECEITAS" SET
                        "ID_CONSULTAS" = %s,
                        "ID_FATURA" = %s,
                        "MEDICAMENTO" = %s,
                        "DOSAGEM" = %s,
                        "INSTRUCOES" = %s,
                        "DATA_PRESCRICAO" = %s
                    WHERE "ID_RECEITA" = %s
                """, [
                    request.POST['id_consultas'],
                    request.POST['id_fatura'],
                    request.POST['medicamento'],
                    request.POST['dosagem'],
                    request.POST.get('instrucoes', ''),
                    request.POST['data_prescricao'],
                    id_receita
                ])
            
            messages.success(request, 'Receita atualizada com sucesso!')
            return redirect('listar_receitas')
                
        except Exception as e:
            messages.error(request, f'Erro ao atualizar receita: {str(e)}')
            return redirect('editar_receita', id_receita=id_receita)
    
    # GET request - carregar dados atuais da receita
    try:
        with connection.cursor() as cursor:
            # Carregar receita
            cursor.execute('SELECT * FROM "RECEITAS" WHERE "ID_RECEITA" = %s', [id_receita])
            receita_data = cursor.fetchone()
            
            if receita_data:
                colunas = [col[0] for col in cursor.description]
                receita = dict(zip(colunas, receita_data))
            else:
                receita = None
            
            # Carregar consultas e faturas para dropdown
            cursor.execute('SELECT "ID_CONSULTAS" FROM "CONSULTAS" ORDER BY "ID_CONSULTAS"')
            consultas = cursor.fetchall()
            
            cursor.execute('SELECT "ID_FATURA" FROM "FATURAS" ORDER BY "ID_FATURA"')
            faturas = cursor.fetchall()
            
    except Exception as e:
        messages.error(request, f'Erro ao carregar receita: {str(e)}')
        return redirect('listar_receitas')
    
    if not receita:
        messages.error(request, 'Receita não encontrada.')
        return redirect('listar_receitas')
    
    return render(request, 'core/editar_receita.html', {
        'receita': receita,
        'consultas': consultas,
        'faturas': faturas,
        'titulo': f'Editar Receita #{id_receita}'
    })

def eliminar_receita(request, id_receita):
    """Eliminar uma receita."""
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM "RECEITAS" WHERE "ID_RECEITA" = %s', [id_receita])
            
            messages.success(request, 'Receita eliminada com sucesso!')
            return redirect('listar_receitas')
                
        except Exception as e:
            messages.error(request, f'Erro ao eliminar receita: {str(e)}')
            return redirect('detalhes_receita', id_receita=id_receita)
    
    # GET request - mostrar página de confirmação
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM "RECEITAS" WHERE "ID_RECEITA" = %s', [id_receita])
            receita_data = cursor.fetchone()
            
            if receita_data:
                colunas = [col[0] for col in cursor.description]
                receita = dict(zip(colunas, receita_data))
            else:
                receita = None
                
    except Exception as e:
        messages.error(request, f'Erro ao carregar receita: {str(e)}')
        return redirect('listar_receitas')
    
    if not receita:
        messages.error(request, 'Receita não encontrada.')
        return redirect('listar_receitas')
    
    return render(request, 'core/eliminar_receita.html', {
        'receita': receita,
        'titulo': f'Eliminar Receita #{id_receita}'
    })

# =========================
# FATURAS - CRUD COMPLETO
# =========================

def listar_faturas(request):
    """Listar faturas (usa ORM)."""
    try:
        faturas = Faturas.objects.select_related('id_consultas').all().order_by('-id_fatura')
        # Paginador (opcional)
        paginator = Paginator(faturas, 20)
        page = request.GET.get('page')
        faturas_page = paginator.get_page(page)

        return render(request, 'core/lista_faturas.html', {
            'faturas': faturas_page,
            'total': faturas.count()
        })
    except Exception as e:
        # fallback: usar vista V_FATURAS_PUBLICO (raw SQL)
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM "V_FATURAS_PUBLICO" ORDER BY "ID_FATURA" DESC LIMIT 200')
                faturas_raw = cursor.fetchall()
                if faturas_raw:
                    colunas = [col[0] for col in cursor.description]
                    faturas_dict = [dict(zip(colunas, row)) for row in faturas_raw]
                else:
                    faturas_dict = []
            return render(request, 'core/lista_faturas.html', {
                'faturas': faturas_dict,
                'total': len(faturas_dict),
                'error': f'Erro ORM: {str(e)} — fallback para vista usada.'
            })
        except Exception as e2:
            return render(request, 'core/lista_faturas.html', {
                'faturas': [],
                'total': 0,
                'error': f'Erro ao carregar faturas: {str(e2)}'
            })

def inserir_fatura(request):
    """Criar nova fatura."""
    if request.method == 'POST':
        form = FaturaForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            # Se estado for 'pago' e data_pagamento vazia, preenche com hoje
            if f.estado == 'pago' and not f.data_pagamento:
                import datetime
                f.data_pagamento = datetime.date.today().isoformat()
            f.save()
            messages.success(request, 'Fatura criada com sucesso!')
            return redirect('listar_faturas')
        else:
            # mostrar erros
            messages.error(request, 'Por favor corrija os erros no formulário.')
    else:
        form = FaturaForm()

    # carregar consultas para dropdown caso o fallback seja necessário
    try:
        consultas = Consultas.objects.filter(estado='concluida').order_by('-inicio')
    except Exception:
        consultas = []

    return render(request, 'core/inserir_fatura.html', {
        'form': form,
        'consultas': consultas,
        'titulo': 'Nova Fatura'
    })

def detalhes_fatura(request, id_fatura):
    """Mostrar detalhe da fatura."""
    try:
        fatura = get_object_or_404(Faturas, pk=id_fatura)
        return render(request, 'core/detalhes_fatura.html', {
            'fatura': fatura,
            'titulo': f'Fatura #{id_fatura}'
        })
    except Exception as e:
        messages.error(request, f'Erro ao carregar fatura: {str(e)}')
        return redirect('listar_faturas')

def editar_fatura(request, id_fatura):
    """Editar fatura existente."""
    fatura = get_object_or_404(Faturas, pk=id_fatura)
    if request.method == 'POST':
        form = FaturaForm(request.POST, instance=fatura)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fatura atualizada com sucesso!')
            return redirect('detalhes_fatura', id_fatura=id_fatura)
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = FaturaForm(instance=fatura)

    return render(request, 'core/editar_fatura.html', {
        'form': form,
        'fatura': fatura,
        'titulo': f'Editar Fatura #{id_fatura}'
    })

def eliminar_fatura(request, id_fatura):
    """Eliminar fatura (confirmação)."""
    fatura = get_object_or_404(Faturas, pk=id_fatura)
    if request.method == 'POST':
        try:
            fatura.delete()
            messages.success(request, 'Fatura eliminada com sucesso.')
            return redirect('listar_faturas')
        except Exception as e:
            messages.error(request, f'Erro ao eliminar fatura: {str(e)}')
            return redirect('detalhes_fatura', id_fatura=id_fatura)

    return render(request, 'core/eliminar_fatura.html', {
        'fatura': fatura,
        'titulo': f'Eliminar Fatura #{id_fatura}'
    })

def marcar_fatura_pago(request, id_fatura):
    """Marca fatura como paga (mudar estado e definir data_pagamento)."""
    fatura = get_object_or_404(Faturas, pk=id_fatura)
    try:
        import datetime
        fatura.estado = 'pago'
        fatura.data_pagamento = datetime.date.today().isoformat()
        fatura.save()
        messages.success(request, 'Fatura marcada como paga.')
    except Exception as e:
        messages.error(request, f'Erro ao marcar fatura como paga: {str(e)}')
    return redirect('detalhes_fatura', id_fatura=id_fatura)

# =========================
# AGENDA DO MÉDICO - VERSÃO SEM AUTENTICAÇÃO
# =========================

def agenda_medica(request):
    """View da agenda médica que não requer autenticação - versão demo"""
    try:
        # Dados de demonstração
        medico_demo = {
            'nome': 'Dr. Silva',
            'especialidade': 'Cardiologia'
        }
        
        hoje = datetime.now().date()
        
        # Consultas de exemplo
        consultas_hoje = [
            {
                'id_consultas': 1,
                'inicio': datetime.now().replace(hour=9, minute=0),
                'fim': datetime.now().replace(hour=9, minute=30),
                'estado': 'agendada',
                'nome_paciente': 'Maria Santos',
                'telefone': '912345678',
                'nome_especialidade': 'Cardiologia'
            },
            {
                'id_consultas': 2,
                'inicio': datetime.now().replace(hour=11, minute=0),
                'fim': datetime.now().replace(hour=11, minute=45),
                'estado': 'confirmada',
                'nome_paciente': 'João Pereira',
                'telefone': '923456789',
                'nome_especialidade': 'Cardiologia'
            },
            {
                'id_consultas': 3,
                'inicio': datetime.now().replace(hour=14, minute=30),
                'fim': datetime.now().replace(hour=15, minute=15),
                'estado': 'pendente',
                'nome_paciente': 'Ana Costa',
                'telefone': '934567890',
                'nome_especialidade': 'Cardiologia'
            }
        ]
        
        # Próximas consultas
        proximas_consultas = [
            {
                'id_consultas': 4,
                'inicio': (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0),
                'fim': (datetime.now() + timedelta(days=1)).replace(hour=10, minute=45),
                'estado': 'agendada',
                'nome_paciente': 'Carlos Mendes',
                'telefone': '945678901',
                'nome_especialidade': 'Cardiologia',
                'inicio_formatado': (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y %H:%M')
            },
            {
                'id_consultas': 5,
                'inicio': (datetime.now() + timedelta(days=2)).replace(hour=15, minute=0),
                'fim': (datetime.now() + timedelta(days=2)).replace(hour=15, minute=30),
                'estado': 'confirmada',
                'nome_paciente': 'Sofia Almeida',
                'telefone': '956789012',
                'nome_especialidade': 'Cardiologia',
                'inicio_formatado': (datetime.now() + timedelta(days=2)).strftime('%d/%m/%Y %H:%M')
            }
        ]
        
        # Horários disponíveis
        horarios_disponiveis = [
            (1, '08:00:00', '09:00:00', 'Segunda, Quarta, Sexta'),
            (2, '10:00:00', '11:00:00', 'Terça, Quinta'),
            (3, '14:00:00', '15:00:00', 'Segunda a Sexta')
        ]
        
        context = {
            'consultas_hoje': consultas_hoje,
            'proximas_consultas': proximas_consultas,
            'total_hoje': len(consultas_hoje),
            'total_pendentes': len([c for c in consultas_hoje if c['estado'] in ['agendada', 'confirmada']]),
            'total_pacientes': 5,
            'horarios_disponiveis': horarios_disponiveis,
            'hoje': hoje,
            'medico': medico_demo,
            'titulo': 'Minha Agenda - Demonstração',
            'demo_mode': True
        }
        
        return render(request, 'core/agenda_medica.html', context)
        
    except Exception as e:
        return render(request, 'core/agenda_medica.html', {
            'consultas_hoje': [],
            'proximas_consultas': [],
            'total_hoje': 0,
            'total_pendentes': 0,
            'total_pacientes': 0,
            'horarios_disponiveis': [],
            'titulo': 'Minha Agenda - Demonstração',
            'demo_mode': True,
            'error': f'Erro ao carregar agenda: {str(e)}'
        })

def api_agenda_medico(request):
    """API para carregar dados da agenda do médico (AJAX)"""
    try:
        if not hasattr(request.user, 'medicos'):
            return JsonResponse({'error': 'Acesso restrito a médicos'}, status=403)
        
        medico = request.user.medicos
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        
        if not data_inicio or not data_fim:
            return JsonResponse({'error': 'Datas de início e fim são obrigatórias'}, status=400)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c."ID_CONSULTAS",
                    c."INICIO",
                    c."FIM",
                    c."ESTADO",
                    c."MOTIVO",
                    u."NOMEREGIAO" as nome_paciente,
                    u."TELEFONE",
                    es."NOME_ESPECIALIDADE",
                    TO_CHAR(c."INICIO", 'YYYY-MM-DD') as data,
                    TO_CHAR(c."INICIO", 'HH24:MI') as hora_inicio,
                    TO_CHAR(c."FIM", 'HH24:MI') as hora_fim
                FROM "CONSULTAS" c 
                JOIN "HORARIOS" h ON c."ID_HORARIO" = h."ID_HORARIO"
                JOIN "TEEM_COMO_HORARIO" tch ON h."ID_HORARIO" = tch."ID_HORARIO"
                JOIN "MEDICOS" m ON tch."ID_UTILIZADOR" = m."ID_UTILIZADOR" AND tch."ID_MEDICO" = m."ID_MEDICO"
                LEFT JOIN "PACIENTES" p ON c."ID_PACIENTE" = p."ID_PACIENTE"
                LEFT JOIN "UTILIZADOR" u ON p."ID_UTILIZADOR" = u."ID_UTILIZADOR"
                LEFT JOIN "ESPECIALIZAM_SE" esm ON m."ID_UTILIZADOR" = esm."ID_UTILIZADOR" AND m."ID_MEDICO" = esm."ID_MEDICO"
                LEFT JOIN "ESPECIALIDADES" es ON esm."ID_ESPECIALIDADES" = es."ID_ESPECIALIDADES"
                WHERE m."ID_MEDICO" = %s 
                AND c."INICIO" >= %s
                AND c."INICIO" <= %s
                ORDER BY c."INICIO"
            """, [medico.id_medico, data_inicio, data_fim])
            
            consultas = cursor.fetchall()
            colunas = [col[0] for col in cursor.description] if consultas else []
            consultas_dict = [dict(zip(colunas, row)) for row in consultas] if consultas else []
        
        return JsonResponse({'consultas': consultas_dict})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def atualizar_estado_consulta(request, id_consulta):
    """Atualizar o estado de uma consulta"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            if not hasattr(request.user, 'medicos'):
                return JsonResponse({'success': False, 'error': 'Acesso restrito a médicos'})
            
            novo_estado = request.POST.get('estado')
            observacoes = request.POST.get('observacoes', '')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE "CONSULTAS" 
                    SET "ESTADO" = %s, "OBSERVACOES" = %s
                    WHERE "ID_CONSULTAS" = %s
                    AND EXISTS (
                        SELECT 1 FROM "HORARIOS" h
                        JOIN "TEEM_COMO_HORARIO" tch ON h."ID_HORARIO" = tch."ID_HORARIO"
                        WHERE tch."ID_MEDICO" = %s
                        AND h."ID_HORARIO" = "CONSULTAS"."ID_HORARIO"
                    )
                """, [novo_estado, observacoes, id_consulta, request.user.medicos.id_medico])
            
            if cursor.rowcount > 0:
                return JsonResponse({'success': True, 'message': 'Estado da consulta atualizado'})
            else:
                return JsonResponse({'success': False, 'error': 'Consulta não encontrada ou acesso negado'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def horarios_disponiveis_medico(request):
    """API para obter horários disponíveis do médico"""
    try:
        if not hasattr(request.user, 'medicos'):
            return JsonResponse({'error': 'Acesso restrito a médicos'}, status=403)
        
        medico = request.user.medicos
        data = request.GET.get('data')
        
        if not data:
            return JsonResponse({'error': 'Data é obrigatória'}, status=400)
        
        with connection.cursor() as cursor:
            # Horários do médico
            cursor.execute("""
                SELECT 
                    h."ID_HORARIO",
                    h."HORA_INICIO",
                    h."HORA_FIM",
                    h."DIAS_SEMANA"
                FROM "HORARIOS" h
                JOIN "TEEM_COMO_HORARIO" tch ON h."ID_HORARIO" = tch."ID_HORARIO"
                WHERE tch."ID_MEDICO" = %s 
                AND h."DATA_FIM" >= %s
                AND (%s BETWEEN h."DATA_INICIO" AND h."DATA_FIM" OR h."DATA_INICIO" IS NULL)
            """, [medico.id_medico, data, data])
            
            horarios = cursor.fetchall()
            colunas = [col[0] for col in cursor.description] if horarios else []
            horarios_dict = [dict(zip(colunas, row)) for row in horarios] if horarios else []
            
            # Consultas já agendadas nessa data
            cursor.execute("""
                SELECT 
                    c."ID_HORARIO",
                    c."INICIO",
                    c."FIM"
                FROM "CONSULTAS" c
                JOIN "HORARIOS" h ON c."ID_HORARIO" = h."ID_HORARIO"
                WHERE DATE(c."INICIO") = %s
                AND c."ESTADO" IN ('agendada', 'confirmada')
                AND EXISTS (
                    SELECT 1 FROM "TEEM_COMO_HORARIO" tch 
                    WHERE tch."ID_HORARIO" = h."ID_HORARIO" 
                    AND tch."ID_MEDICO" = %s
                )
            """, [data, medico.id_medico])
            
            consultas_agendadas = cursor.fetchall()
        
        return JsonResponse({
            'horarios': horarios_dict,
            'consultas_agendadas': consultas_agendadas
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def simple_login_view(request):
    """View de login manual sem usar backends do Django"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT "ID_UTILIZADOR", "NOMEREGIAO", "EMAIL", "SENHA", "ROLE", "ATIVO"
                    FROM "UTILIZADOR" 
                    WHERE ("EMAIL" = %s OR "NOMEREGIAO" = %s) AND "ATIVO" = 1
                """, [username, username])
                
                user_data = cursor.fetchone()
                
                if user_data:
                    id_utilizador, nomeregiao, email, senha_hash, role, ativo = user_data
                    
                    # Verificação simples (apenas para teste)
                    if password == senha_hash:
                        from django.contrib.auth import login
                        from django.contrib.auth.models import User
                        
                        # Criar user object
                        user = User()
                        user.id = id_utilizador
                        user.username = email
                        user.email = email
                        user.first_name = nomeregiao
                        user.is_active = bool(ativo)
                        
                        # Fazer login manualmente
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(request, user)
                        
                        messages.success(request, f'Bem-vindo, {nomeregiao}!')
                        next_url = request.GET.get('next', 'home')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'Password incorreta.')
                else:
                    messages.error(request, 'Utilizador não encontrado.')
                    
        except Exception as e:
            messages.error(request, f'Erro no login: {str(e)}')
    
    return render(request, 'core/login.html')