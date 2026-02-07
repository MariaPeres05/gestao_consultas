# core/views_enfermeiro.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime, timedelta
from types import SimpleNamespace
from django.http import JsonResponse

from .decorators import role_required


def _dictfetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def _dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _make_enfermeiro(row):
    return SimpleNamespace(
        id_enfermeiro=row.get('id_enfermeiro'),
        id_utilizador=SimpleNamespace(
            id_utilizador=row.get('id_utilizador'),
            nome=row.get('nome'),
            email=row.get('email'),
            telefone=row.get('telefone'),
        ),
        id_unidade=SimpleNamespace(
            nome_unidade=row.get('unidade_nome')
        ),
    )


def _make_consulta(row):
    return SimpleNamespace(
        id_consulta=row.get('id_consulta'),
        data_consulta=row.get('data_consulta'),
        hora_consulta=row.get('hora_consulta'),
        estado=row.get('estado'),
        id_paciente=SimpleNamespace(
            id_utilizador=SimpleNamespace(
                nome=row.get('paciente_nome')
            )
        ),
        id_medico=SimpleNamespace(
            id_utilizador=SimpleNamespace(
                nome=row.get('medico_nome')
            ),
            id_especialidade=SimpleNamespace(
                nome_especialidade=row.get('especialidade_nome')
            )
        ),
    )


def _make_paciente_list(row):
    return SimpleNamespace(
        id_paciente=row.get('id_paciente'),
        total_consultas=row.get('total_consultas', 0),
        id_utilizador=SimpleNamespace(
            nome=row.get('nome'),
            email=row.get('email'),
            telefone=row.get('telefone'),
            n_utente=row.get('n_utente'),
        ),
    )


def _make_paciente_detalhe(row):
    return SimpleNamespace(
        id_paciente=row.get('id_paciente'),
        data_nasc=row.get('data_nasc'),
        genero=row.get('genero'),
        morada=row.get('morada'),
        alergias=row.get('alergias'),
        observacoes=row.get('observacoes'),
        id_utilizador=SimpleNamespace(
            nome=row.get('nome'),
            email=row.get('email'),
            telefone=row.get('telefone'),
            n_utente=row.get('n_utente'),
        ),
    )


def _make_consulta_paciente(row):
    return SimpleNamespace(
        data_consulta=row.get('data_consulta'),
        hora_consulta=row.get('hora_consulta'),
        estado=row.get('estado'),
        id_medico=SimpleNamespace(
            id_utilizador=SimpleNamespace(
                nome=row.get('medico_nome')
            ),
            id_especialidade=SimpleNamespace(
                nome_especialidade=row.get('especialidade_nome')
            ),
        ),
    )


def _make_fatura(row):
    return SimpleNamespace(
        data_pagamento=row.get('data_pagamento'),
        valor=row.get('valor'),
        metodo_pagamento=row.get('metodo_pagamento'),
        estado=row.get('estado'),
    )


def _make_receita(row):
    return SimpleNamespace(
        data_prescricao=row.get('data_prescricao'),
        medicamento=row.get('medicamento'),
        dosagem=row.get('dosagem'),
        id_consulta=SimpleNamespace(
            id_medico=SimpleNamespace(
                id_utilizador=SimpleNamespace(
                    nome=row.get('medico_nome')
                )
            )
        ),
    )


@login_required
@role_required('enfermeiro')
def enfermeiro_dashboard(request):
    """Dashboard principal do enfermeiro."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_enfermeiro_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        enfermeiro_row = _dictfetchone(cursor)

    if not enfermeiro_row:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')

    enfermeiro = _make_enfermeiro(enfermeiro_row)

    # Estatísticas
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_estatisticas_enfermeiro()")
        stats = _dictfetchone(cursor) or {}

    consultas_hoje = stats.get('consultas_hoje', 0)
    consultas_pendentes = stats.get('consultas_pendentes', 0)
    pacientes_semana = stats.get('pacientes_semana', 0)

    # Próximas consultas
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_proximas_consultas_enfermeiro(%s)",
            [10]
        )
        proximas_rows = _dictfetchall(cursor)

    proximas_consultas = [_make_consulta(row) for row in proximas_rows]
    
    context = {
        'enfermeiro': enfermeiro,
        'consultas_hoje': consultas_hoje,
        'consultas_pendentes': consultas_pendentes,
        'pacientes_semana': pacientes_semana,
        'proximas_consultas': proximas_consultas,
    }
    return render(request, 'enfermeiro/dashboard.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_consultas(request):
    """Lista e gere consultas."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_enfermeiro_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        enfermeiro_row = _dictfetchone(cursor)

    if not enfermeiro_row:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')

    enfermeiro = _make_enfermeiro(enfermeiro_row)

    # Filtros
    estado_filter = request.GET.get('estado', '')
    data_filter = request.GET.get('data', '')
    medico_filter = request.GET.get('medico', '')

    data_parsed = None
    if data_filter:
        try:
            data_parsed = datetime.strptime(data_filter, '%Y-%m-%d').date()
        except ValueError:
            data_parsed = None

    medico_id = int(medico_filter) if medico_filter.isdigit() else None

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_consultas_enfermeiro(%s, %s, %s, %s)",
            [estado_filter or None, data_parsed, medico_id, 100]
        )
        consultas_rows = _dictfetchall(cursor)

    consultas = [_make_consulta(row) for row in consultas_rows]

    # Todos os médicos para o filtro
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_medicos_enfermeiro()")
        medicos_rows = _dictfetchall(cursor)

    medicos = [
        SimpleNamespace(
            id_medico=row.get('id_medico'),
            id_utilizador=SimpleNamespace(
                nome=row.get('nome')
            )
        )
        for row in medicos_rows
    ]
    
    context = {
        'enfermeiro': enfermeiro,
        'consultas': consultas,
        'medicos': medicos,
        'estado_filter': estado_filter,
        'data_filter': data_filter,
        'medico_filter': medico_filter,
    }
    return render(request, 'enfermeiro/consultas.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_consulta_criar(request):
    """Criar consulta em nome do paciente"""
    hoje = timezone.now().date()
    
    if request.method == 'POST':
        try:
            paciente_id = request.POST.get('paciente')
            disponibilidade_id = request.POST.get('disponibilidade')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            motivo_consulta = request.POST.get('motivo_consulta', '')

            if not all([paciente_id, disponibilidade_id, hora_inicio, hora_fim]):
                messages.error(request, "Preencha todos os campos obrigatórios.")
                raise ValueError("Campos obrigatórios não preenchidos")

            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()

            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL public.enfermeiro_marcar_consulta(%s::integer, %s::integer, %s::integer, %s::time, %s::time, %s::varchar)",
                    [
                        request.user.id_utilizador,
                        int(paciente_id),
                        int(disponibilidade_id),
                        hora_inicio_obj,
                        hora_fim_obj,
                        motivo_consulta or None,
                    ]
                )
                result = cursor.fetchone()

            mensagem = None
            sucesso = False
            if result:
                mensagem = result[0]
                sucesso = result[1]

            if sucesso:
                messages.success(request, mensagem or "Consulta agendada com sucesso.")
                return redirect('enfermeiro_consultas')

            messages.error(request, mensagem or "Erro ao marcar consulta.")

        except Exception as e:
            messages.error(request, f"Erro ao marcar consulta: {str(e)}")
    
    # GET request - mostrar formulário
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_pacientes_ativos()")
        pacientes_rows = _dictfetchall(cursor)

    pacientes = [
        SimpleNamespace(
            id_paciente=row.get('id_paciente'),
            id_utilizador=SimpleNamespace(
                nome=row.get('nome'),
                email=row.get('email'),
            )
        )
        for row in pacientes_rows
    ]

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_especialidades()")
        especialidades_rows = _dictfetchall(cursor)

    especialidades = [
        SimpleNamespace(
            id_especialidade=row.get('id_especialidade'),
            nome_especialidade=row.get('nome_especialidade')
        )
        for row in especialidades_rows
    ]

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_unidades_saude()")
        unidades_rows = _dictfetchall(cursor)

    unidades = [
        SimpleNamespace(
            id_unidade=row.get('id_unidade'),
            nome_unidade=row.get('nome_unidade')
        )
        for row in unidades_rows
    ]
    
    context = {
        'pacientes': pacientes,
        'especialidades': especialidades,
        'unidades': unidades,
        'hoje': hoje,
    }
    
    return render(request, 'enfermeiro/consulta_form.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_disponibilidades_list(request):
    """API endpoint para disponibilidades por unidade e data (enfermeiro)"""
    unidade_id = request.GET.get('unidade')
    data = request.GET.get('data')
    especialidade_id = request.GET.get('especialidade')

    if not unidade_id or not data:
        return JsonResponse({'disponibilidades': []})

    try:
        disponibilidades = []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM listar_disponibilidades_admin(%s, %s, %s)",
                [unidade_id, data, especialidade_id or None]
            )
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                disponibilidades.append({
                    'id': row_dict['id_disponibilidade'],
                    'medico_nome': row_dict['medico_nome'],
                    'hora_inicio': row_dict['hora_inicio'].strftime('%H:%M'),
                    'hora_fim': row_dict['hora_fim'].strftime('%H:%M'),
                    'especialidade': row_dict['especialidade_nome']
                })

        return JsonResponse({'disponibilidades': disponibilidades})
    except Exception as e:
        return JsonResponse({'disponibilidades': [], 'error': str(e)})


@login_required
@role_required('enfermeiro')
def enfermeiro_pacientes(request):
    """Lista pacientes."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_enfermeiro_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        enfermeiro_row = _dictfetchone(cursor)

    if not enfermeiro_row:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')

    enfermeiro = _make_enfermeiro(enfermeiro_row)

    search = request.GET.get('search', '')

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_pacientes_enfermeiro(%s)",
            [search or None]
        )
        pacientes_rows = _dictfetchall(cursor)

    pacientes = [_make_paciente_list(row) for row in pacientes_rows]
    
    context = {
        'enfermeiro': enfermeiro,
        'pacientes': pacientes,
        'search': search,
    }
    return render(request, 'enfermeiro/pacientes.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_paciente_detalhes(request, paciente_id):
    """Detalhes e histórico de um paciente."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_enfermeiro_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        enfermeiro_row = _dictfetchone(cursor)

    if not enfermeiro_row:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')

    enfermeiro = _make_enfermeiro(enfermeiro_row)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_paciente_detalhes_enfermeiro(%s)",
            [paciente_id]
        )
        paciente_row = _dictfetchone(cursor)

    if not paciente_row:
        messages.error(request, "Paciente não encontrado.")
        return redirect('enfermeiro_pacientes')

    paciente = _make_paciente_detalhe(paciente_row)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_consultas_paciente_enfermeiro(%s)",
            [paciente_id]
        )
        consultas_rows = _dictfetchall(cursor)

    consultas = [_make_consulta_paciente(row) for row in consultas_rows]

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_faturas_paciente_enfermeiro(%s)",
            [paciente_id]
        )
        faturas_rows = _dictfetchall(cursor)

    faturas = [_make_fatura(row) for row in faturas_rows]

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_receitas_paciente_enfermeiro(%s)",
            [paciente_id]
        )
        receitas_rows = _dictfetchall(cursor)

    receitas = [_make_receita(row) for row in receitas_rows]
    
    context = {
        'enfermeiro': enfermeiro,
        'paciente': paciente,
        'consultas': consultas,
        'faturas': faturas,
        'receitas': receitas,
    }
    return render(request, 'enfermeiro/paciente_detalhes.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_relatorios(request):
    """Relatórios e estatísticas."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_enfermeiro_por_utilizador(%s)",
            [request.user.id_utilizador]
        )
        enfermeiro_row = _dictfetchone(cursor)

    if not enfermeiro_row:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')

    enfermeiro = _make_enfermeiro(enfermeiro_row)
    
    # Período de análise
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if not data_inicio:
        data_inicio = (timezone.now() - timedelta(days=30)).date()
    else:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = (timezone.now() - timedelta(days=30)).date()

    if not data_fim:
        data_fim = timezone.now().date()
    else:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = timezone.now().date()

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_totais_relatorio_enfermeiro(%s, %s)",
            [data_inicio, data_fim]
        )
        totals = _dictfetchone(cursor) or {}

    total_consultas = totals.get('total_consultas', 0)
    total_receitas = totals.get('total_receitas', 0)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_estado(%s, %s, %s, %s)",
            [data_inicio, data_fim, None, None]
        )
        consultas_por_estado = _dictfetchall(cursor)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_medico(%s, %s, %s, %s, %s)",
            [data_inicio, data_fim, None, None, 10]
        )
        consultas_medico_rows = _dictfetchall(cursor)

    consultas_por_medico = [
        SimpleNamespace(
            id_medico__id_utilizador__nome=row.get('medico_nome'),
            total=row.get('total')
        )
        for row in consultas_medico_rows
    ]
    
    context = {
        'enfermeiro': enfermeiro,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_consultas': total_consultas,
        'consultas_por_estado': consultas_por_estado,
        'consultas_por_medico': consultas_por_medico,
        'total_receitas': total_receitas,
    }
    return render(request, 'enfermeiro/relatorios.html', context)
