# core/views_admin.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, connection
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Utilizador, Regiao, UnidadeSaude, Especialidade, Medico, 
    Enfermeiro, Paciente, Consulta, Fatura, Disponibilidade
)
from .decorators import role_required
from django.http import HttpResponse, JsonResponse
import csv
import json
import io

@login_required
@role_required('admin')
def admin_dashboard(request):
    """Dashboard principal do administrador com estatísticas gerais"""
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # Estatísticas gerais via função SQL
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM obter_dashboard_admin_stats(%s)",
            [inicio_mes]
        )
        stats_row = cursor.fetchone()
    
    if stats_row:
        (
            total_pacientes,
            total_medicos,
            total_enfermeiros,
            total_unidades,
            consultas_hoje,
            consultas_mes,
            consultas_pendentes,
            faturas_pendentes,
            receita_mes,
        ) = stats_row
    else:
        total_pacientes = total_medicos = total_enfermeiros = total_unidades = 0
        consultas_hoje = consultas_mes = consultas_pendentes = 0
        faturas_pendentes = 0
        receita_mes = 0

    # Últimas atividades (últimas 10 consultas) via view SQL
    ultimas_consultas = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_consulta, paciente_nome, medico_nome, data_consulta, hora_consulta, estado
            FROM vw_admin_ultimas_consultas
            ORDER BY data_consulta DESC, hora_consulta DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            ultimas_consultas.append({
                'id_consulta': row[0],
                'paciente_nome': row[1],
                'medico_nome': row[2],
                'data_consulta': row[3],
                'hora_consulta': row[4],
                'estado': row[5],
            })
    
    context = {
        'total_pacientes': total_pacientes,
        'total_medicos': total_medicos,
        'total_enfermeiros': total_enfermeiros,
        'total_unidades': total_unidades,
        'consultas_hoje': consultas_hoje,
        'consultas_mes': consultas_mes,
        'consultas_pendentes': consultas_pendentes,
        'faturas_pendentes': faturas_pendentes,
        'receita_mes': receita_mes,
        'ultimas_consultas': ultimas_consultas,
    }
    
    return render(request, 'admin/dashboard.html', context)


# ==================== GESTÃO DE REGIÕES ====================

@login_required
@role_required('admin')
def admin_regioes(request):
    """Listar todas as regiões"""
    regioes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_regioes_admin()")
        for row in cursor.fetchall():
            regioes.append({
                'id_regiao': row[0],
                'nome': row[1],
                'tipo_regiao': row[2],
            })
    return render(request, 'admin/regioes.html', {'regioes': regioes})


@login_required
@role_required('admin')
def admin_regioes_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="regioes.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['id_regiao', 'nome', 'tipo_regiao'])
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_regioes_admin()")
        for row in cursor.fetchall():
            writer.writerow([row[0], row[1], row[2]])
    return response


@login_required
@role_required('admin')
def admin_regioes_export_json(request):
    regioes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_regioes_admin()")
        for row in cursor.fetchall():
            regioes.append({
                'id_regiao': row[0],
                'nome': row[1],
                'tipo_regiao': row[2]
            })
    return JsonResponse(regioes, safe=False, json_dumps_params={'indent': 2})


@login_required
@role_required('admin')
def admin_regioes_import_csv(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro CSV.")
        return redirect('admin_regioes')

    file_obj = request.FILES['file']
    content = file_obj.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    created = 0
    errors = 0

    for row in reader:
        nome = (row.get('nome') or '').strip()
        tipo = (row.get('tipo_regiao') or '').strip()
        if not nome or not tipo:
            errors += 1
            continue
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL admin_criar_regiao(%s, %s)", [nome, tipo])
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_regioes')


@login_required
@role_required('admin')
def admin_regioes_import_json(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro JSON.")
        return redirect('admin_regioes')

    file_obj = request.FILES['file']
    data = json.loads(file_obj.read().decode('utf-8-sig'))
    created = 0
    errors = 0

    for item in data if isinstance(data, list) else []:
        nome = (item.get('nome') or '').strip()
        tipo = (item.get('tipo_regiao') or '').strip()
        if not nome or not tipo:
            errors += 1
            continue
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL admin_criar_regiao(%s, %s)", [nome, tipo])
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_regioes')


@login_required
@role_required('admin')
def admin_regiao_criar(request):
    """Criar nova região"""
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tipo_regiao = request.POST.get('tipo_regiao')
        
        if nome and tipo_regiao:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL admin_criar_regiao(%s, %s)",
                        [nome, tipo_regiao]
                    )
                messages.success(request, f"Região '{nome}' criada com sucesso!")
                return redirect('admin_regioes')
            except Exception as e:
                messages.error(request, f"Erro ao criar região: {str(e)}")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    return render(request, 'admin/regiao_form.html', {'action': 'Criar'})


@login_required
@role_required('admin')
def admin_regiao_editar(request, regiao_id):
    """Editar região existente"""
    regiao = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_regiao_por_id(%s)", [regiao_id])
        row = cursor.fetchone()
        if row:
            regiao = {'id_regiao': row[0], 'nome': row[1], 'tipo_regiao': row[2]}
    if not regiao:
        messages.error(request, "Região não encontrada.")
        return redirect('admin_regioes')
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tipo_regiao = request.POST.get('tipo_regiao')
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_editar_regiao(%s, %s, %s)",
                    [regiao_id, nome, tipo_regiao]
                )
            messages.success(request, f"Região '{nome}' atualizada com sucesso!")
            return redirect('admin_regioes')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar região: {str(e)}")
    
    return render(request, 'admin/regiao_form.html', {
        'action': 'Editar',
        'regiao': regiao
    })


@login_required
@role_required('admin')
def admin_regiao_eliminar(request, regiao_id):
    """Eliminar região"""
    regiao = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_regiao_por_id(%s)", [regiao_id])
        row = cursor.fetchone()
        if row:
            regiao = {'id_regiao': row[0], 'nome': row[1], 'tipo_regiao': row[2]}
    if not regiao:
        messages.error(request, "Região não encontrada.")
        return redirect('admin_regioes')
    
    if request.method == 'POST':
        nome = regiao['nome']
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_eliminar_regiao(%s)",
                    [regiao_id]
                )
            messages.success(request, f"Região '{nome}' eliminada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao eliminar região: {str(e)}")
        return redirect('admin_regioes')
    
    return render(request, 'admin/regiao_confirmar_eliminar.html', {'regiao': regiao})


# ==================== GESTÃO DE ESPECIALIDADES ====================

@login_required
@role_required('admin')
def admin_especialidades(request):
    """Listar todas as especialidades"""
    especialidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_especialidades_admin()")
        for row in cursor.fetchall():
            especialidades.append({
                'id_especialidade': row[0],
                'nome_especialidade': row[1],
                'descricao': row[2],
                'num_medicos': row[3],
            })
    return render(request, 'admin/especialidades.html', {'especialidades': especialidades})


@login_required
@role_required('admin')
def admin_especialidades_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="especialidades.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['id_especialidade', 'nome_especialidade', 'descricao'])
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_especialidade, nome_especialidade, descricao, num_medicos FROM listar_especialidades_admin()")
        for row in cursor.fetchall():
            writer.writerow([row[0], row[1], row[2]])
    return response


@login_required
@role_required('admin')
def admin_especialidades_export_json(request):
    especialidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_especialidade, nome_especialidade, descricao, num_medicos FROM listar_especialidades_admin()")
        for row in cursor.fetchall():
            especialidades.append({
                'id_especialidade': row[0],
                'nome_especialidade': row[1],
                'descricao': row[2]
            })
    return JsonResponse(especialidades, safe=False, json_dumps_params={'indent': 2})


@login_required
@role_required('admin')
def admin_especialidades_import_csv(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro CSV.")
        return redirect('admin_especialidades')

    file_obj = request.FILES['file']
    content = file_obj.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    created = 0
    errors = 0

    for row in reader:
        nome = (row.get('nome_especialidade') or row.get('nome') or '').strip()
        descricao = (row.get('descricao') or '').strip()
        if not nome:
            errors += 1
            continue
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL admin_criar_especialidade(%s, %s)", [nome, descricao])
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_especialidades')


@login_required
@role_required('admin')
def admin_especialidades_import_json(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro JSON.")
        return redirect('admin_especialidades')

    file_obj = request.FILES['file']
    data = json.loads(file_obj.read().decode('utf-8-sig'))
    created = 0
    errors = 0

    for item in data if isinstance(data, list) else []:
        nome = (item.get('nome_especialidade') or item.get('nome') or '').strip()
        descricao = (item.get('descricao') or '').strip()
        if not nome:
            errors += 1
            continue
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL admin_criar_especialidade(%s, %s)", [nome, descricao])
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_especialidades')


@login_required
@role_required('admin')
def admin_especialidade_criar(request):
    """Criar nova especialidade"""
    if request.method == 'POST':
        nome = request.POST.get('nome_especialidade')
        descricao = request.POST.get('descricao', '')
        
        if nome:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL admin_criar_especialidade(%s, %s)",
                        [nome, descricao]
                    )
                messages.success(request, f"Especialidade '{nome}' criada com sucesso!")
                return redirect('admin_especialidades')
            except Exception as e:
                messages.error(request, f"Erro ao criar especialidade: {str(e)}")
        else:
            messages.error(request, "O nome da especialidade é obrigatório.")
    
    return render(request, 'admin/especialidade_form.html', {'action': 'Criar'})


@login_required
@role_required('admin')
def admin_especialidade_editar(request, especialidade_id):
    """Editar especialidade existente"""
    especialidade = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_especialidade_por_id(%s)", [especialidade_id])
        row = cursor.fetchone()
        if row:
            especialidade = {
                'id_especialidade': row[0],
                'nome_especialidade': row[1],
                'descricao': row[2],
            }
    if not especialidade:
        messages.error(request, "Especialidade não encontrada.")
        return redirect('admin_especialidades')
    
    if request.method == 'POST':
        nome = request.POST.get('nome_especialidade')
        descricao = request.POST.get('descricao', '')
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_editar_especialidade(%s, %s, %s)",
                    [especialidade_id, nome, descricao]
                )
            messages.success(request, f"Especialidade '{nome}' atualizada!")
            return redirect('admin_especialidades')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar especialidade: {str(e)}")
    
    return render(request, 'admin/especialidade_form.html', {
        'action': 'Editar',
        'especialidade': especialidade
    })


@login_required
@role_required('admin')
def admin_especialidade_eliminar(request, especialidade_id):
    """Eliminar especialidade"""
    especialidade = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_especialidade_por_id(%s)", [especialidade_id])
        row = cursor.fetchone()
        if row:
            especialidade = {
                'id_especialidade': row[0],
                'nome_especialidade': row[1],
                'descricao': row[2],
            }
    if not especialidade:
        messages.error(request, "Especialidade não encontrada.")
        return redirect('admin_especialidades')
    
    if request.method == 'POST':
        nome = especialidade['nome_especialidade']
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_eliminar_especialidade(%s)",
                    [especialidade_id]
                )
            messages.success(request, f"Especialidade '{nome}' eliminada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao eliminar especialidade: {str(e)}")
        return redirect('admin_especialidades')
    
    return render(request, 'admin/especialidade_confirmar_eliminar.html', {'especialidade': especialidade})


# ==================== GESTÃO DE UNIDADES DE SAÚDE ====================

@login_required
@role_required('admin')
def admin_unidades(request):
    """Listar todas as unidades de saúde"""
    unidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_unidades_admin()")
        for row in cursor.fetchall():
            unidades.append({
                'id_unidade': row[0],
                'nome_unidade': row[1],
                'morada_unidade': row[2],
                'tipo_unidade': row[3],
                'id_regiao': {'id_regiao': row[4], 'nome': row[5]},
            })
    return render(request, 'admin/unidades.html', {'unidades': unidades})


@login_required
@role_required('admin')
def admin_unidades_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="unidades.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['id_unidade', 'nome_unidade', 'morada_unidade', 'tipo_unidade', 'id_regiao', 'nome_regiao'])
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_unidades_admin()")
        for row in cursor.fetchall():
            writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5]])
    return response


@login_required
@role_required('admin')
def admin_unidades_export_json(request):
    unidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_unidades_admin()")
        for row in cursor.fetchall():
            unidades.append({
                'id_unidade': row[0],
                'nome_unidade': row[1],
                'morada_unidade': row[2],
                'tipo_unidade': row[3],
                'id_regiao': row[4],
                'nome_regiao': row[5]
            })
    return JsonResponse(unidades, safe=False, json_dumps_params={'indent': 2})


@login_required
@role_required('admin')
def admin_unidades_import_csv(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro CSV.")
        return redirect('admin_unidades')

    file_obj = request.FILES['file']
    content = file_obj.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    created = 0
    errors = 0

    for row in reader:
        nome = (row.get('nome_unidade') or row.get('nome') or '').strip()
        morada = (row.get('morada_unidade') or '').strip()
        tipo = (row.get('tipo_unidade') or '').strip()
        id_regiao = (row.get('id_regiao') or '').strip()
        nome_regiao = (row.get('nome_regiao') or '').strip()

        if not nome or not morada or not tipo:
            errors += 1
            continue

        if not id_regiao and nome_regiao:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id_regiao FROM \"REGIAO\" WHERE nome = %s", [nome_regiao])
                reg_row = cursor.fetchone()
                if reg_row:
                    id_regiao = str(reg_row[0])

        if not id_regiao:
            errors += 1
            continue

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_criar_unidade(%s, %s, %s, %s)",
                    [nome, morada, tipo, id_regiao]
                )
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_unidades')


@login_required
@role_required('admin')
def admin_unidades_import_json(request):
    if request.method != 'POST' or 'file' not in request.FILES:
        messages.error(request, "Selecione um ficheiro JSON.")
        return redirect('admin_unidades')

    file_obj = request.FILES['file']
    data = json.loads(file_obj.read().decode('utf-8-sig'))
    created = 0
    errors = 0

    for item in data if isinstance(data, list) else []:
        nome = (item.get('nome_unidade') or item.get('nome') or '').strip()
        morada = (item.get('morada_unidade') or '').strip()
        tipo = (item.get('tipo_unidade') or '').strip()
        id_regiao = str(item.get('id_regiao') or '').strip()
        nome_regiao = (item.get('nome_regiao') or '').strip()

        if not nome or not morada or not tipo:
            errors += 1
            continue

        if not id_regiao and nome_regiao:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id_regiao FROM \"REGIAO\" WHERE nome = %s", [nome_regiao])
                reg_row = cursor.fetchone()
                if reg_row:
                    id_regiao = str(reg_row[0])

        if not id_regiao:
            errors += 1
            continue

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_criar_unidade(%s, %s, %s, %s)",
                    [nome, morada, tipo, id_regiao]
                )
            created += 1
        except Exception:
            errors += 1

    messages.success(request, f"Importação concluída: {created} criadas, {errors} com erro.")
    return redirect('admin_unidades')


@login_required
@role_required('admin')
def admin_unidade_criar(request):
    """Criar nova unidade de saúde"""
    if request.method == 'POST':
        nome = request.POST.get('nome_unidade')
        morada = request.POST.get('morada_unidade')
        tipo = request.POST.get('tipo_unidade')
        regiao_id = request.POST.get('id_regiao')
        
        if nome and morada and tipo and regiao_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL admin_criar_unidade(%s, %s, %s, %s)",
                        [nome, morada, tipo, regiao_id]
                    )
                messages.success(request, f"Unidade '{nome}' criada com sucesso!")
                return redirect('admin_unidades')
            except Exception as e:
                messages.error(request, f"Erro ao criar unidade: {str(e)}")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    regioes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_regioes_admin()")
        for row in cursor.fetchall():
            regioes.append({'id_regiao': row[0], 'nome': row[1], 'tipo_regiao': row[2]})
    return render(request, 'admin/unidade_form.html', {
        'action': 'Criar',
        'regioes': regioes
    })


@login_required
@role_required('admin')
def admin_unidade_editar(request, unidade_id):
    """Editar unidade de saúde existente"""
    unidade = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_unidade_por_id(%s)", [unidade_id])
        row = cursor.fetchone()
        if row:
            unidade = {
                'id_unidade': row[0],
                'nome_unidade': row[1],
                'morada_unidade': row[2],
                'tipo_unidade': row[3],
                'id_regiao': {'id_regiao': row[4], 'nome': row[5]},
            }
    if not unidade:
        messages.error(request, "Unidade não encontrada.")
        return redirect('admin_unidades')
    
    if request.method == 'POST':
        nome = request.POST.get('nome_unidade')
        morada = request.POST.get('morada_unidade')
        tipo = request.POST.get('tipo_unidade')
        regiao_id = request.POST.get('id_regiao')
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_editar_unidade(%s, %s, %s, %s, %s)",
                    [unidade_id, nome, morada, tipo, regiao_id]
                )
            messages.success(request, f"Unidade '{nome}' atualizada!")
            return redirect('admin_unidades')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar unidade: {str(e)}")
    
    regioes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_regioes_admin()")
        for row in cursor.fetchall():
            regioes.append({'id_regiao': row[0], 'nome': row[1], 'tipo_regiao': row[2]})
    return render(request, 'admin/unidade_form.html', {
        'action': 'Editar',
        'unidade': unidade,
        'regioes': regioes
    })


@login_required
@role_required('admin')
def admin_unidade_eliminar(request, unidade_id):
    """Eliminar unidade de saúde"""
    unidade = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_unidade_por_id(%s)", [unidade_id])
        row = cursor.fetchone()
        if row:
            unidade = {
                'id_unidade': row[0],
                'nome_unidade': row[1],
                'morada_unidade': row[2],
                'tipo_unidade': row[3],
                'id_regiao': {'id_regiao': row[4], 'nome': row[5]},
            }
    if not unidade:
        messages.error(request, "Unidade não encontrada.")
        return redirect('admin_unidades')
    
    if request.method == 'POST':
        nome = unidade['nome_unidade']
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_eliminar_unidade(%s)",
                    [unidade_id]
                )
            messages.success(request, f"Unidade '{nome}' eliminada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao eliminar unidade: {str(e)}")
        return redirect('admin_unidades')
    
    return render(request, 'admin/unidade_confirmar_eliminar.html', {'unidade': unidade})


# ==================== GESTÃO DE UTILIZADORES ====================

@login_required
@role_required('admin')
def admin_utilizadores(request):
    """Listar todos os utilizadores"""
    role_filter = request.GET.get('role', '')
    
    utilizadores = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_utilizadores_admin(%s)", [role_filter or None])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            utilizadores.append(dict(zip(columns, row)))
    
    roles = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
        ('enfermeiro', 'Enfermeiro'),
        ('admin', 'Administrador'),
    ]
    
    context = {
        'utilizadores': utilizadores,
        'role_filter': role_filter,
        'roles': roles
    }
    return render(request, 'admin/utilizadores.html', context)


@login_required
@role_required('admin')
def admin_utilizador_criar(request):
    """Criar novo utilizador"""
    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone', '')
        role = request.POST.get('role')
        senha = request.POST.get('senha')
        
        if nome and email and role and senha:
            if role == 'paciente':
                data_nasc = request.POST.get('data_nasc')
                genero = request.POST.get('genero')
                if not data_nasc or not genero:
                    messages.error(request, "Preencha os campos obrigatórios do paciente.")
                    return redirect('admin_utilizador_criar')
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT verificar_email_utilizador_admin(%s, NULL)", [email])
                    email_exists = cursor.fetchone()[0]
                if email_exists:
                    messages.error(request, "Já existe um utilizador com este email.")
                else:
                    from django.contrib.auth.hashers import make_password
                    password_hash = make_password(senha)
                    numero_ordem = request.POST.get('numero_ordem', '')
                    especialidade_id = request.POST.get('especialidade_id') or None
                    n_ordem_enf = request.POST.get('n_ordem_enf', '')
                    data_nasc = request.POST.get('data_nasc') or None
                    genero = request.POST.get('genero') or None
                    morada = request.POST.get('morada', '')
                    
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "CALL admin_criar_utilizador(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            [
                                nome, email, telefone, role, password_hash,
                                numero_ordem, especialidade_id, n_ordem_enf,
                                data_nasc, genero, morada
                            ]
                        )
                    messages.success(request, f"Utilizador '{nome}' criado com sucesso!")
                    return redirect('admin_utilizadores')
            except Exception as e:
                messages.error(request, f"Erro ao criar utilizador: {str(e)}")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    especialidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_especialidades()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            especialidades.append(dict(zip(columns, row)))
    roles = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
        ('enfermeiro', 'Enfermeiro'),
        ('admin', 'Administrador'),
    ]
    return render(request, 'admin/utilizador_form.html', {
        'action': 'Criar',
        'roles': roles,
        'especialidades': especialidades
    })


@login_required
@role_required('admin')
def admin_utilizador_editar(request, utilizador_id):
    """Editar utilizador existente"""
    utilizador = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_utilizador_admin_por_id(%s)", [utilizador_id])
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            utilizador = dict(zip(columns, row))
    if not utilizador:
        messages.error(request, "Utilizador não encontrado.")
        return redirect('admin_utilizadores')
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone', '')
        ativo = request.POST.get('ativo') == 'on'
        nova_senha = request.POST.get('senha')
        
        if not nome or not email:
            messages.error(request, "Preencha os campos obrigatórios.")
            return redirect('admin_utilizador_editar', utilizador_id=utilizador_id)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT verificar_email_utilizador_admin(%s, %s)", [email, utilizador_id])
                email_exists = cursor.fetchone()[0]
            if email_exists:
                messages.error(request, "Já existe um utilizador com este email.")
                return redirect('admin_utilizador_editar', utilizador_id=utilizador_id)
            
            password_hash = None
            if nova_senha:
                from django.contrib.auth.hashers import make_password
                password_hash = make_password(nova_senha)
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL admin_editar_utilizador(%s, %s, %s, %s, %s, %s)",
                    [utilizador_id, nome, email, telefone, ativo, password_hash]
                )
            messages.success(request, f"Utilizador '{nome}' atualizado!")
            return redirect('admin_utilizadores')
        except Exception as e:
            messages.error(request, f"Erro ao atualizar utilizador: {str(e)}")
    
    roles = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
        ('enfermeiro', 'Enfermeiro'),
        ('admin', 'Administrador'),
    ]
    return render(request, 'admin/utilizador_form.html', {
        'action': 'Editar',
        'utilizador': utilizador,
        'roles': roles
    })


@login_required
@role_required('admin')
def admin_utilizador_desativar(request, utilizador_id):
    """Desativar/Ativar utilizador"""
    utilizador = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_utilizador_admin_por_id(%s)", [utilizador_id])
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            utilizador = dict(zip(columns, row))
    if not utilizador:
        messages.error(request, "Utilizador não encontrado.")
        return redirect('admin_utilizadores')
    
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL admin_toggle_utilizador_ativo(%s)", [utilizador_id])
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM obter_utilizador_admin_por_id(%s)", [utilizador_id])
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    utilizador = dict(zip(columns, row))
            estado = "ativado" if utilizador and utilizador.get('ativo') else "desativado"
            messages.success(request, f"Utilizador '{utilizador.get('nome', '')}' {estado}!")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar utilizador: {str(e)}")
        return redirect('admin_utilizadores')
    
    return render(request, 'admin/utilizador_confirmar_desativar.html', {'utilizador': utilizador})


# ==================== GESTÃO DE CONSULTAS ====================

@login_required
@role_required('admin')
def admin_consultas(request):
    """Listar e gerir todas as consultas"""
    estado_filter = request.GET.get('estado', '')
    data_filter = request.GET.get('data', '')
    
    consultas = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_consultas_admin(%s, %s, %s)",
            [estado_filter or None, data_filter or None, 100]
        )
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            consultas.append(dict(zip(columns, row)))
    
    context = {
        'consultas': consultas,
        'estado_filter': estado_filter,
        'data_filter': data_filter
    }
    return render(request, 'admin/consultas.html', context)


@login_required
@role_required('admin')
def admin_disponibilidades_list(request):
    """API endpoint to get available disponibilidades for a given unidade and date"""
    from django.http import JsonResponse
    
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
@role_required('admin')
def admin_consulta_cancelar(request, consulta_id):
    """Cancelar consulta em nome do paciente"""
    consulta = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_consulta_admin_por_id(%s)", [consulta_id])
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            consulta = dict(zip(columns, row))
    if not consulta:
        messages.error(request, "Consulta não encontrada.")
        return redirect('admin_consultas')
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Cancelada pelo administrativo')
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL cancelar_consulta(%s, %s, %s, %s)",
                    [consulta_id, motivo, request.user.id_utilizador, 'admin']
                )
            messages.success(request, "Consulta cancelada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao cancelar consulta: {str(e)}")
        return redirect('admin_consultas')
    
    return render(request, 'admin/consulta_cancelar.html', {'consulta': consulta})


@login_required
@role_required('admin')
def admin_consulta_criar(request):
    """Criar consulta em nome do paciente"""
    hoje = timezone.now().date()
    
    if request.method == 'POST':
        try:
            paciente_id = request.POST.get('paciente')
            disponibilidade_id = request.POST.get('disponibilidade')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            motivo_consulta = request.POST.get('motivo_consulta', '')
            
            # Validações
            if not all([paciente_id, disponibilidade_id, hora_inicio, hora_fim]):
                messages.error(request, "Preencha todos os campos obrigatórios.")
                raise ValueError("Campos obrigatórios não preenchidos")
            
            disponibilidade = None
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM obter_disponibilidade_admin_por_id(%s)", [disponibilidade_id])
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    disponibilidade = dict(zip(columns, row))
            if not disponibilidade:
                messages.error(request, "Disponibilidade não encontrada.")
                raise ValueError("Disponibilidade não encontrada")
            
            # Converter strings de hora para time objects
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
            
            # Validar que as horas estão dentro da disponibilidade
            if hora_inicio_obj < disponibilidade['hora_inicio'] or hora_fim_obj > disponibilidade['hora_fim']:
                messages.error(request, "O horário da consulta deve estar dentro do horário disponível do médico.")
                raise ValueError("Horário fora da disponibilidade")
            
            if hora_inicio_obj >= hora_fim_obj:
                messages.error(request, "A hora de início deve ser anterior à hora de fim.")
                raise ValueError("Horário inválido")
            
            # Verificar se a data não é no passado
            if disponibilidade['data'] < hoje:
                messages.error(request, "Não é possível marcar consultas para datas passadas.")
                raise ValueError("Data no passado")
            
            # Criar consulta via procedure
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL marcar_consulta(%s, %s, %s, %s, %s)",
                    [
                        paciente_id,
                        disponibilidade['id_medico'],
                        disponibilidade['data'],
                        hora_inicio_obj,
                        motivo_consulta or "Marcação administrativa"
                    ]
                )
            
            paciente_info = None
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM obter_paciente_admin_por_id(%s)", [paciente_id])
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    paciente_info = dict(zip(columns, row))
            paciente_nome = paciente_info['nome'] if paciente_info else "Paciente"
            medico_nome = disponibilidade['medico_nome']
            success_msg = (
                f"Consulta agendada para {paciente_nome} com Dr(a). {medico_nome} "
                f"em {disponibilidade['data'].strftime('%d/%m/%Y')} das {hora_inicio} às {hora_fim}. "
                "Aguarda confirmação do médico e paciente."
            )
            messages.success(request, success_msg)
            return redirect('admin_consultas')
            
        except Exception as e:
            messages.error(request, f"Erro ao marcar consulta: {str(e)}")
    
    # GET request - mostrar formulário
    pacientes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_pacientes_ativos()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            pacientes.append(dict(zip(columns, row)))
    
    especialidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_especialidades()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            especialidades.append(dict(zip(columns, row)))
    
    unidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM listar_unidades()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            unidades.append(dict(zip(columns, row)))
    
    context = {
        'pacientes': pacientes,
        'especialidades': especialidades,
        'unidades': unidades,
        'hoje': hoje,
    }
    
    return render(request, 'admin/consulta_form.html', context)


# ==================== GESTÃO DE FATURAS ====================

@login_required
@role_required('admin')
def admin_faturas(request):
    """Listar e gerir todas as faturas"""
    estado_filter = request.GET.get('estado', '')
    
    faturas = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM listar_faturas_admin(%s, %s)",
            [estado_filter or None, 100]
        )
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            faturas.append(dict(zip(columns, row)))
    
    total_faturado = 0
    total_pendente = 0
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_estatisticas_faturas_admin()")
        row = cursor.fetchone()
        if row:
            total_faturado = row[0] or 0
            total_pendente = row[1] or 0
    
    context = {
        'faturas': faturas,
        'estado_filter': estado_filter,
        'total_faturado': total_faturado,
        'total_pendente': total_pendente
    }
    return render(request, 'admin/faturas.html', context)


@login_required
@role_required('admin')
def admin_fatura_criar(request, consulta_id):
    """Criar fatura para uma consulta"""
    consulta = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_consulta_admin_para_fatura(%s)", [consulta_id])
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            consulta = dict(zip(columns, row))
    if not consulta:
        messages.error(request, "Consulta não encontrada.")
        return redirect('admin_faturas')
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT verificar_fatura_por_consulta(%s)", [consulta_id])
        if cursor.fetchone()[0]:
            messages.warning(request, "Esta consulta já tem uma fatura associada.")
            return redirect('admin_faturas')
    
    if request.method == 'POST':
        valor = request.POST.get('valor')
        metodo_pagamento = request.POST.get('metodo_pagamento', 'pendente')
        
        if valor:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL admin_criar_fatura(%s, %s, %s)",
                        [consulta_id, valor, metodo_pagamento]
                    )
                messages.success(request, "Fatura criada com sucesso!")
                return redirect('admin_faturas')
            except Exception as e:
                messages.error(request, f"Erro ao criar fatura: {str(e)}")
    
    return render(request, 'admin/fatura_form.html', {
        'consulta': consulta,
        'action': 'Criar'
    })


@login_required
@role_required('admin')
def admin_fatura_editar(request, fatura_id):
    """Editar fatura"""
    fatura = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_fatura_admin_por_id(%s)", [fatura_id])
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            fatura = dict(zip(columns, row))
    if not fatura:
        messages.error(request, "Fatura não encontrada.")
        return redirect('admin_faturas')
    
    if request.method == 'POST':
        valor = request.POST.get('valor')
        metodo_pagamento = request.POST.get('metodo_pagamento')
        estado = request.POST.get('estado')
        
        if valor and metodo_pagamento and estado:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL admin_editar_fatura(%s, %s, %s, %s)",
                        [fatura_id, valor, metodo_pagamento, estado]
                    )
                messages.success(request, "Fatura atualizada com sucesso!")
                return redirect('admin_faturas')
            except Exception as e:
                messages.error(request, f"Erro ao atualizar fatura: {str(e)}")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    return render(request, 'admin/fatura_form.html', {
        'fatura': fatura,
        'action': 'Editar'
    })


# ==================== RELATÓRIOS ====================


@login_required
@role_required('admin')
def admin_relatorios(request):
    """Página de relatórios e estatísticas"""
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    data_inicio = request.GET.get('data_inicio', inicio_mes.isoformat())
    data_fim = request.GET.get('data_fim', hoje.isoformat())
    estado_filter = request.GET.get('estado') or None
    
    try:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except:
        data_inicio = inicio_mes
        data_fim = hoje
    
    consultas_por_estado = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_estado(%s, %s, %s, %s)",
            [data_inicio, data_fim, estado_filter, None]
        )
        for row in cursor.fetchall():
            consultas_por_estado.append({
                'estado': row[0],
                'total': row[1]
            })
    
    consultas_por_medico = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_medico(%s, %s, %s, %s, %s)",
            [data_inicio, data_fim, estado_filter, None, 10]
        )
        for row in cursor.fetchall():
            consultas_por_medico.append({
                'id_medico__id_utilizador__nome': row[0],
                'total': row[1]
            })
    
    consultas_por_especialidade = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_especialidade(%s, %s, %s, %s)",
            [data_inicio, data_fim, estado_filter, None]
        )
        for row in cursor.fetchall():
            consultas_por_especialidade.append({
                'id_medico__id_especialidade__nome_especialidade': row[0],
                'total': row[1]
            })

    receitas = {'total': 0, 'count': 0}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_receitas_periodo(%s, %s)",
            [data_inicio, data_fim]
        )
        row = cursor.fetchone()
        if row:
            receitas = {'total': row[0] or 0, 'count': row[1] or 0}
    
    context = {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'consultas_por_estado': list(consultas_por_estado),
        'consultas_por_medico': list(consultas_por_medico),
        'consultas_por_especialidade': list(consultas_por_especialidade),
        'receitas': receitas,
    }
    
    return render(request, 'admin/relatorios.html', context)

@login_required
@role_required('admin')
def relatorio_financeiro_csv(request):
    """Relatório financeiro em CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_financeiro.csv"'
    
    writer = csv.writer(response, delimiter=';') 
    writer.writerow([
        'ID Fatura', 
        'Data Emissão', 
        'Data Pagamento', 
        'Valor Total (€)', 
        'Estado', 
        'Método Pagamento', 
        'ID Consulta',
        'Paciente', 
        'Médico', 
        'Especialidade',
        'Data Consulta',
        'Hora Consulta'
    ])

    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    estado = request.GET.get('estado')
    
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_faturas_listar(%s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None]
        )
        for row in cursor.fetchall():
            writer.writerow([
                row[0],
                row[1].strftime('%d/%m/%Y') if row[1] else '',
                row[1].strftime('%d/%m/%Y') if row[1] else 'Pendente',
                f"{row[2]:.2f}".replace('.', ','),
                row[3],
                row[4] or 'N/A',
                row[5],
                row[6],
                row[7],
                row[8] or 'N/A',
                row[9].strftime('%d/%m/%Y') if row[9] else '',
                row[10].strftime('%H:%M') if row[10] else ''
            ])
    
    return response

@login_required
@role_required('admin')
def relatorio_financeiro_json(request):
    """Relatório financeiro em JSON com estatísticas"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    estado = request.GET.get('estado')
    
    total_faturas = 0
    valor_total = 0
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_faturas_stats(%s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None]
        )
        row = cursor.fetchone()
        if row:
            total_faturas = row[0] or 0
            valor_total = row[1] or 0
    
    faturas_por_estado = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_faturas_por_estado(%s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None]
        )
        for row in cursor.fetchall():
            faturas_por_estado.append({
                'estado': row[0],
                'count': row[1],
                'total': row[2]
            })
    
    faturas_detalhes = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_faturas_detalhes(%s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, 100]
        )
        for row in cursor.fetchall():
            faturas_detalhes.append({
                'id_fatura': row[0],
                'data_pagamento': row[1].strftime('%Y-%m-%d') if row[1] else None,
                'valor': float(row[2]),
                'estado': row[3],
                'metodo_pagamento': row[4],
                'consulta': {
                    'id_consulta': row[5],
                    'data_consulta': row[6].strftime('%Y-%m-%d') if row[6] else None,
                    'hora_consulta': row[7].strftime('%H:%M') if row[7] else None,
                    'paciente': {
                        'id': row[8],
                        'nome': row[9],
                        'n_utente': row[10]
                    },
                    'medico': {
                        'id': row[11],
                        'nome': row[12],
                        'especialidade': row[13]
                    }
                }
            })
    
    resposta = {
        'periodo': {
            'data_inicio': data_inicio,
            'data_fim': data_fim
        },
        'estatisticas': {
            'total_faturas': total_faturas,
            'valor_total': float(valor_total),
            'valor_medio': float(valor_total / total_faturas) if total_faturas > 0 else 0
        },
        'resumo_por_estado': [
            {
                'estado': item['estado'],
                'quantidade': item['count'],
                'valor_total': float(item['total']) if item['total'] else 0
            }
            for item in faturas_por_estado
        ],
        'faturas': faturas_detalhes
    }
    
    return JsonResponse(resposta, safe=False, json_dumps_params={'indent': 2})

@login_required
@role_required('admin')
def relatorio_consultas_csv(request):
    """Relatório de consultas em CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_consultas.csv"'
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID Consulta',
        'Data',
        'Hora',
        'Paciente',
        'Médico',
        'Especialidade',
        'Estado',
        'Motivo',
        'Valor (€)',
        'Fatura ID',
        'Data Criação'
    ])
    
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    estado = request.GET.get('estado')
    medico_id = request.GET.get('medico_id')
    
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_listar(%s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, medico_id or None]
        )
        for row in cursor.fetchall():
            writer.writerow([
                row[0],
                row[1].strftime('%d/%m/%Y') if row[1] else '',
                row[2].strftime('%H:%M') if row[2] else '',
                row[3],
                row[4],
                row[5] or 'N/A',
                row[6],
                row[7] or '',
                f"{row[8]:.2f}".replace('.', ','),
                row[9] if row[9] else 'N/A',
                row[10].strftime('%d/%m/%Y %H:%M') if row[10] else ''
            ])
    
    return response

@login_required
@role_required('admin')
def relatorio_consultas_json(request):
    """Relatório de consultas em JSON"""
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    estado = request.GET.get('estado')
    medico_id = request.GET.get('medico_id')
    
    total_consultas = 0
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relatorio_consultas_total(%s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, medico_id or None]
        )
        row = cursor.fetchone()
        if row:
            total_consultas = row[0] or 0
    
    consultas_por_estado = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_estado(%s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, medico_id or None]
        )
        for row in cursor.fetchall():
            consultas_por_estado.append({
                'estado': row[0],
                'count': row[1]
            })
    
    consultas_por_medico = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_por_medico(%s, %s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, medico_id or None, 10]
        )
        for row in cursor.fetchall():
            consultas_por_medico.append({
                'id_medico__id_utilizador__nome': row[0],
                'count': row[1]
            })
    
    consultas_detalhes = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM relatorio_consultas_detalhes(%s, %s, %s, %s, %s)",
            [data_inicio or None, data_fim or None, estado or None, medico_id or None, 100]
        )
        for row in cursor.fetchall():
            fatura_info = None
            if row[10]:
                fatura_info = {
                    'id': row[10],
                    'valor': float(row[11]),
                    'estado': row[12]
                }
            consultas_detalhes.append({
                'id_consulta': row[0],
                'data_consulta': row[1].strftime('%Y-%m-%d') if row[1] else None,
                'hora_consulta': row[2].strftime('%H:%M') if row[2] else None,
                'estado': row[3],
                'motivo': row[4],
                'paciente': {
                    'id': row[5],
                    'nome': row[6]
                },
                'medico': {
                    'id': row[7],
                    'nome': row[8],
                    'especialidade': row[9]
                },
                'fatura': fatura_info
            })
    
    resposta = {
        'periodo': {
            'data_inicio': data_inicio,
            'data_fim': data_fim
        },
        'estatisticas': {
            'total_consultas': total_consultas,
            'por_estado': list(consultas_por_estado),
            'top_medicos': list(consultas_por_medico)
        },
        'consultas': consultas_detalhes
    }
    
    return JsonResponse(resposta, safe=False, json_dumps_params={'indent': 2})