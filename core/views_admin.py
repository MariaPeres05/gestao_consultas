# core/views_admin.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
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

@login_required
@role_required('admin')
def admin_dashboard(request):
    """Dashboard principal do administrador com estatísticas gerais"""
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # Estatísticas gerais
    total_pacientes = Paciente.objects.count()
    total_medicos = Medico.objects.count()
    total_enfermeiros = Enfermeiro.objects.count()
    total_unidades = UnidadeSaude.objects.count()
    
    # Consultas - count only confirmed (accepted by both parties) and not canceled
    consultas_hoje = Consulta.objects.filter(
        data_consulta=hoje,
        estado='confirmada'
    ).count()
    consultas_mes = Consulta.objects.filter(
        data_consulta__gte=inicio_mes,
        estado='confirmada'
    ).count()
    consultas_pendentes = Consulta.objects.filter(estado='agendada').count()
    
    # Faturas
    faturas_pendentes = Fatura.objects.filter(estado='pendente').count()
    receita_mes = Fatura.objects.filter(
        estado='paga',
        data_pagamento__gte=inicio_mes
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Últimas atividades (últimas 10 consultas)
    ultimas_consultas = Consulta.objects.select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador'
    ).order_by('-data_consulta', '-hora_consulta')[:10]
    
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
    regioes = Regiao.objects.all().order_by('nome')
    return render(request, 'admin/regioes.html', {'regioes': regioes})


@login_required
@role_required('admin')
def admin_regiao_criar(request):
    """Criar nova região"""
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tipo_regiao = request.POST.get('tipo_regiao')
        
        if nome and tipo_regiao:
            Regiao.objects.create(nome=nome, tipo_regiao=tipo_regiao)
            messages.success(request, f"Região '{nome}' criada com sucesso!")
            return redirect('admin_regioes')
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    return render(request, 'admin/regiao_form.html', {'action': 'Criar'})


@login_required
@role_required('admin')
def admin_regiao_editar(request, regiao_id):
    """Editar região existente"""
    regiao = get_object_or_404(Regiao, id_regiao=regiao_id)
    
    if request.method == 'POST':
        regiao.nome = request.POST.get('nome')
        regiao.tipo_regiao = request.POST.get('tipo_regiao')
        regiao.save()
        messages.success(request, f"Região '{regiao.nome}' atualizada com sucesso!")
        return redirect('admin_regioes')
    
    return render(request, 'admin/regiao_form.html', {
        'action': 'Editar',
        'regiao': regiao
    })


@login_required
@role_required('admin')
def admin_regiao_eliminar(request, regiao_id):
    """Eliminar região"""
    regiao = get_object_or_404(Regiao, id_regiao=regiao_id)
    
    if request.method == 'POST':
        nome = regiao.nome
        try:
            regiao.delete()
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
    especialidades = Especialidade.objects.annotate(
        num_medicos=Count('medicos')
    ).order_by('nome_especialidade')
    return render(request, 'admin/especialidades.html', {'especialidades': especialidades})


@login_required
@role_required('admin')
def admin_especialidade_criar(request):
    """Criar nova especialidade"""
    if request.method == 'POST':
        nome = request.POST.get('nome_especialidade')
        descricao = request.POST.get('descricao', '')
        
        if nome:
            Especialidade.objects.create(
                nome_especialidade=nome,
                descricao=descricao
            )
            messages.success(request, f"Especialidade '{nome}' criada com sucesso!")
            return redirect('admin_especialidades')
        else:
            messages.error(request, "O nome da especialidade é obrigatório.")
    
    return render(request, 'admin/especialidade_form.html', {'action': 'Criar'})


@login_required
@role_required('admin')
def admin_especialidade_editar(request, especialidade_id):
    """Editar especialidade existente"""
    especialidade = get_object_or_404(Especialidade, id_especialidade=especialidade_id)
    
    if request.method == 'POST':
        especialidade.nome_especialidade = request.POST.get('nome_especialidade')
        especialidade.descricao = request.POST.get('descricao', '')
        especialidade.save()
        messages.success(request, f"Especialidade '{especialidade.nome_especialidade}' atualizada!")
        return redirect('admin_especialidades')
    
    return render(request, 'admin/especialidade_form.html', {
        'action': 'Editar',
        'especialidade': especialidade
    })


@login_required
@role_required('admin')
def admin_especialidade_eliminar(request, especialidade_id):
    """Eliminar especialidade"""
    especialidade = get_object_or_404(Especialidade, id_especialidade=especialidade_id)
    
    if request.method == 'POST':
        nome = especialidade.nome_especialidade
        try:
            especialidade.delete()
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
    unidades = UnidadeSaude.objects.select_related('id_regiao').order_by('nome_unidade')
    return render(request, 'admin/unidades.html', {'unidades': unidades})


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
            regiao = get_object_or_404(Regiao, id_regiao=regiao_id)
            UnidadeSaude.objects.create(
                nome_unidade=nome,
                morada_unidade=morada,
                tipo_unidade=tipo,
                id_regiao=regiao
            )
            messages.success(request, f"Unidade '{nome}' criada com sucesso!")
            return redirect('admin_unidades')
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    regioes = Regiao.objects.all().order_by('nome')
    return render(request, 'admin/unidade_form.html', {
        'action': 'Criar',
        'regioes': regioes
    })


@login_required
@role_required('admin')
def admin_unidade_editar(request, unidade_id):
    """Editar unidade de saúde existente"""
    unidade = get_object_or_404(UnidadeSaude, id_unidade=unidade_id)
    
    if request.method == 'POST':
        unidade.nome_unidade = request.POST.get('nome_unidade')
        unidade.morada_unidade = request.POST.get('morada_unidade')
        unidade.tipo_unidade = request.POST.get('tipo_unidade')
        regiao_id = request.POST.get('id_regiao')
        unidade.id_regiao = get_object_or_404(Regiao, id_regiao=regiao_id)
        unidade.save()
        messages.success(request, f"Unidade '{unidade.nome_unidade}' atualizada!")
        return redirect('admin_unidades')
    
    regioes = Regiao.objects.all().order_by('nome')
    return render(request, 'admin/unidade_form.html', {
        'action': 'Editar',
        'unidade': unidade,
        'regioes': regioes
    })


@login_required
@role_required('admin')
def admin_unidade_eliminar(request, unidade_id):
    """Eliminar unidade de saúde"""
    unidade = get_object_or_404(UnidadeSaude, id_unidade=unidade_id)
    
    if request.method == 'POST':
        nome = unidade.nome_unidade
        try:
            unidade.delete()
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
    
    utilizadores = Utilizador.objects.all()
    if role_filter:
        utilizadores = utilizadores.filter(role=role_filter)
    
    utilizadores = utilizadores.order_by('-data_registo')
    
    context = {
        'utilizadores': utilizadores,
        'role_filter': role_filter,
        'roles': Utilizador.ROLE_CHOICES
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
            if Utilizador.objects.filter(email=email).exists():
                messages.error(request, "Já existe um utilizador com este email.")
            else:
                user = Utilizador.objects.create_user(
                    nome=nome,
                    email=email,
                    telefone=telefone,
                    senha=senha,
                    role=role,
                    ativo=True
                )
                
                # Criar perfis específicos conforme o role
                if role == 'medico':
                    numero_ordem = request.POST.get('numero_ordem', '')
                    especialidade_id = request.POST.get('especialidade_id')
                    especialidade = None
                    if especialidade_id:
                        especialidade = Especialidade.objects.get(id_especialidade=especialidade_id)
                    
                    Medico.objects.create(
                        id_utilizador=user,
                        numero_ordem=numero_ordem,
                        id_especialidade=especialidade
                    )
                elif role == 'enfermeiro':
                    n_ordem_enf = request.POST.get('n_ordem_enf', '')
                    Enfermeiro.objects.create(
                        id_utilizador=user,
                        n_ordem_enf=n_ordem_enf
                    )
                elif role == 'paciente':
                    data_nasc = request.POST.get('data_nasc')
                    genero = request.POST.get('genero')
                    morada = request.POST.get('morada', '')
                    
                    if data_nasc and genero:
                        # n_utente is auto-generated by create_user, no need to set it manually
                        Paciente.objects.create(
                            id_utilizador=user,
                            data_nasc=data_nasc,
                            genero=genero,
                            morada=morada
                        )
                
                messages.success(request, f"Utilizador '{nome}' criado com sucesso!")
                return redirect('admin_utilizadores')
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
    
    especialidades = Especialidade.objects.all().order_by('nome_especialidade')
    return render(request, 'admin/utilizador_form.html', {
        'action': 'Criar',
        'roles': Utilizador.ROLE_CHOICES,
        'especialidades': especialidades
    })


@login_required
@role_required('admin')
def admin_utilizador_editar(request, utilizador_id):
    """Editar utilizador existente"""
    utilizador = get_object_or_404(Utilizador, id_utilizador=utilizador_id)
    
    if request.method == 'POST':
        utilizador.nome = request.POST.get('nome')
        utilizador.email = request.POST.get('email')
        utilizador.telefone = request.POST.get('telefone', '')
        utilizador.ativo = request.POST.get('ativo') == 'on'
        
        # Atualizar senha apenas se fornecida
        nova_senha = request.POST.get('senha')
        if nova_senha:
            utilizador.set_password(nova_senha)
        
        utilizador.save()
        messages.success(request, f"Utilizador '{utilizador.nome}' atualizado!")
        return redirect('admin_utilizadores')
    
    return render(request, 'admin/utilizador_form.html', {
        'action': 'Editar',
        'utilizador': utilizador,
        'roles': Utilizador.ROLE_CHOICES
    })


@login_required
@role_required('admin')
def admin_utilizador_desativar(request, utilizador_id):
    """Desativar/Ativar utilizador"""
    utilizador = get_object_or_404(Utilizador, id_utilizador=utilizador_id)
    
    if request.method == 'POST':
        utilizador.ativo = not utilizador.ativo
        utilizador.save()
        estado = "ativado" if utilizador.ativo else "desativado"
        messages.success(request, f"Utilizador '{utilizador.nome}' {estado}!")
        return redirect('admin_utilizadores')
    
    return render(request, 'admin/utilizador_confirmar_desativar.html', {'utilizador': utilizador})


# ==================== GESTÃO DE CONSULTAS ====================

@login_required
@role_required('admin')
def admin_consultas(request):
    """Listar e gerir todas as consultas"""
    estado_filter = request.GET.get('estado', '')
    data_filter = request.GET.get('data', '')
    
    consultas = Consulta.objects.select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador',
        'id_disponibilidade__id_unidade'
    )
    
    if estado_filter:
        consultas = consultas.filter(estado=estado_filter)
    if data_filter:
        consultas = consultas.filter(data_consulta=data_filter)
    
    consultas = consultas.order_by('-data_consulta', '-hora_consulta')[:100]
    
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
    from core.models import Disponibilidade
    
    unidade_id = request.GET.get('unidade')
    data = request.GET.get('data')
    especialidade_id = request.GET.get('especialidade')
    
    if not unidade_id or not data:
        return JsonResponse({'disponibilidades': []})
    
    try:
        # Query disponibilidades
        disponibilidades = Disponibilidade.objects.filter(
            id_unidade_id=unidade_id,
            data=data,
            status_slot='disponivel'
        ).select_related('id_medico__id_utilizador', 'id_medico__id_especialidade')
        
        # Filter by especialidade if provided
        if especialidade_id:
            disponibilidades = disponibilidades.filter(
                id_medico__id_especialidade_id=especialidade_id
            )
        
        # Check for existing consultas to exclude occupied slots
        result = []
        for disp in disponibilidades:
            # Check if there's already a consulta for this slot
            conflito = Consulta.objects.filter(
                id_medico=disp.id_medico,
                data_consulta=disp.data,
                hora_consulta__gte=disp.hora_inicio,
                hora_consulta__lt=disp.hora_fim,
                estado__in=['agendada', 'confirmada', 'marcada']
            ).exists()
            
            if not conflito:
                result.append({
                    'id': disp.id_disponibilidade,
                    'medico_nome': disp.id_medico.id_utilizador.nome,
                    'hora_inicio': disp.hora_inicio.strftime('%H:%M'),
                    'hora_fim': disp.hora_fim.strftime('%H:%M'),
                    'especialidade': disp.id_medico.id_especialidade.nome_especialidade if disp.id_medico.id_especialidade else None
                })
        
        return JsonResponse({'disponibilidades': result})
    except Exception as e:
        return JsonResponse({'disponibilidades': [], 'error': str(e)})


@login_required
@role_required('admin')
def admin_consulta_cancelar(request, consulta_id):
    """Cancelar consulta em nome do paciente"""
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Cancelada pelo administrativo')
        consulta.estado = 'cancelada'
        consulta.motivo = motivo
        consulta.save()
        messages.success(request, "Consulta cancelada com sucesso!")
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
            
            paciente = get_object_or_404(Paciente, id_paciente=paciente_id)
            disponibilidade = get_object_or_404(Disponibilidade, id_disponibilidade=disponibilidade_id)
            
            # Converter strings de hora para time objects
            from datetime import time as dt_time
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
            
            # Validar que as horas estão dentro da disponibilidade
            if hora_inicio_obj < disponibilidade.hora_inicio or hora_fim_obj > disponibilidade.hora_fim:
                messages.error(request, "O horário da consulta deve estar dentro do horário disponível do médico.")
                raise ValueError("Horário fora da disponibilidade")
            
            if hora_inicio_obj >= hora_fim_obj:
                messages.error(request, "A hora de início deve ser anterior à hora de fim.")
                raise ValueError("Horário inválido")
            
            # Verificar se a data não é no passado
            if disponibilidade.data < hoje:
                messages.error(request, "Não é possível marcar consultas para datas passadas.")
                raise ValueError("Data no passado")
            
            # Verificar se já existe consulta nesse horário para o médico
            conflito = Consulta.objects.filter(
                id_medico=disponibilidade.id_medico,
                data_consulta=disponibilidade.data,
                hora_consulta__gte=hora_inicio_obj,
                hora_consulta__lt=hora_fim_obj,
                estado__in=['agendada', 'confirmada', 'marcada']
            ).exists()
            
            if conflito:
                messages.error(request, "Já existe uma consulta agendada para este horário.")
                raise ValueError("Conflito de horário")
            
            # Criar consulta
            consulta = Consulta.objects.create(
                id_paciente=paciente,
                id_medico=disponibilidade.id_medico,
                id_disponibilidade=disponibilidade,
                data_consulta=disponibilidade.data,
                hora_consulta=hora_inicio_obj,
                motivo=motivo_consulta or "Marcação administrativa",
                estado='agendada',  # Aguarda confirmação do médico e paciente
                medico_aceitou=False,  # Médico precisa aceitar
                paciente_aceitou=False  # Paciente precisa aceitar
            )
            
            success_msg = f"Consulta agendada para {paciente.id_utilizador.nome} com Dr(a). {disponibilidade.id_medico.id_utilizador.nome} em {disponibilidade.data.strftime('%d/%m/%Y')} das {hora_inicio} às {hora_fim}. Aguarda confirmação do médico e paciente."
            messages.success(request, success_msg)
            return redirect('admin_consultas')
            
        except Exception as e:
            messages.error(request, f"Erro ao marcar consulta: {str(e)}")
    
    # GET request - mostrar formulário
    pacientes = Paciente.objects.select_related('id_utilizador').filter(
        id_utilizador__ativo=True
    ).order_by('id_utilizador__nome')
    
    especialidades = Especialidade.objects.all().order_by('nome_especialidade')
    unidades = UnidadeSaude.objects.all().order_by('nome_unidade')
    
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
    
    faturas_qs = Fatura.objects.select_related(
        'id_consulta__id_paciente__id_utilizador',
        'id_consulta__id_medico__id_utilizador'
    )
    
    if estado_filter:
        faturas_qs = faturas_qs.filter(estado=estado_filter)
    
    # Calculate statistics on the unsliced queryset
    total_faturado = faturas_qs.filter(estado='paga').aggregate(total=Sum('valor'))['total'] or 0
    total_pendente = faturas_qs.filter(estado='pendente').aggregate(total=Sum('valor'))['total'] or 0
    
    # Apply ordering and limit for display
    faturas = faturas_qs.order_by('-id_fatura')[:100]
    
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
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id)
    
    # Verificar se já existe fatura
    if Fatura.objects.filter(id_consulta=consulta).exists():
        messages.warning(request, "Esta consulta já tem uma fatura associada.")
        return redirect('admin_faturas')
    
    if request.method == 'POST':
        valor = request.POST.get('valor')
        metodo_pagamento = request.POST.get('metodo_pagamento', 'pendente')
        
        if valor:
            Fatura.objects.create(
                id_consulta=consulta,
                valor=valor,
                metodo_pagamento=metodo_pagamento,
                estado='pendente'
            )
            messages.success(request, "Fatura criada com sucesso!")
            return redirect('admin_faturas')
    
    return render(request, 'admin/fatura_form.html', {
        'consulta': consulta,
        'action': 'Criar'
    })


@login_required
@role_required('admin')
def admin_fatura_editar(request, fatura_id):
    """Editar fatura"""
    fatura = get_object_or_404(Fatura, id_fatura=fatura_id)
    
    if request.method == 'POST':
        fatura.valor = request.POST.get('valor')
        fatura.metodo_pagamento = request.POST.get('metodo_pagamento')
        fatura.estado = request.POST.get('estado')
        
        if fatura.estado == 'paga' and not fatura.data_pagamento:
            fatura.data_pagamento = timezone.now().date()
        
        fatura.save()
        messages.success(request, "Fatura atualizada com sucesso!")
        return redirect('admin_faturas')
    
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
    
    try:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except:
        data_inicio = inicio_mes
        data_fim = hoje
    
    consultas_por_estado = Consulta.objects.filter(
        data_consulta__range=[data_inicio, data_fim]
    ).values('estado').annotate(total=Count('id_consulta')).order_by('-total')
    
    consultas_por_medico = Consulta.objects.filter(
        data_consulta__range=[data_inicio, data_fim]
    ).values('id_medico__id_utilizador__nome').annotate(
        total=Count('id_consulta')
    ).order_by('-total')[:10]
    
    consultas_por_especialidade = Consulta.objects.filter(
        data_consulta__range=[data_inicio, data_fim]
    ).values('id_medico__id_especialidade__nome_especialidade').annotate(
        total=Count('id_consulta')
    ).order_by('-total')

    receitas = Fatura.objects.filter(
        estado='paga',
        data_pagamento__range=[data_inicio, data_fim]
    ).aggregate(
        total=Sum('valor'),
        count=Count('id_fatura')
    )
    
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
    
    faturas = Fatura.objects.select_related(
        'id_consulta__id_paciente__id_utilizador',
        'id_consulta__id_medico__id_utilizador',
        'id_consulta__id_medico__id_especialidade'
    ).all().order_by('-id_fatura')
    
    if data_inicio:
        faturas = faturas.filter(data_pagamento__gte=data_inicio)
    if data_fim:
        faturas = faturas.filter(data_pagamento__lte=data_fim)
    if estado:
        faturas = faturas.filter(estado=estado)
    
    for fatura in faturas:
        consulta = fatura.id_consulta
        writer.writerow([
            fatura.id_fatura,
            fatura.data_pagamento.strftime('%d/%m/%Y') if fatura.data_pagamento else '',
            fatura.data_pagamento.strftime('%d/%m/%Y') if fatura.data_pagamento else 'Pendente',
            f"{fatura.valor:.2f}".replace('.', ','),  # Formato europeu
            fatura.estado,
            fatura.metodo_pagamento or 'N/A',
            consulta.id_consulta,
            consulta.id_paciente.id_utilizador.nome,
            consulta.id_medico.id_utilizador.nome,
            consulta.id_medico.id_especialidade.nome_especialidade if consulta.id_medico.id_especialidade else 'N/A',
            consulta.data_consulta.strftime('%d/%m/%Y') if consulta.data_consulta else '',
            consulta.hora_consulta.strftime('%H:%M') if consulta.hora_consulta else ''
        ])
    
    return response

@login_required
@role_required('admin')
def relatorio_financeiro_json(request):
    """Relatório financeiro em JSON com estatísticas"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    estado = request.GET.get('estado')
    
    faturas_qs = Fatura.objects.select_related(
        'id_consulta__id_paciente__id_utilizador',
        'id_consulta__id_medico__id_utilizador',
        'id_consulta__id_medico__id_especialidade'
    ).all()
    
    if data_inicio:
        faturas_qs = faturas_qs.filter(data_pagamento__gte=data_inicio)
    if data_fim:
        faturas_qs = faturas_qs.filter(data_pagamento__lte=data_fim)
    if estado:
        faturas_qs = faturas_qs.filter(estado=estado)
    
    total_faturas = faturas_qs.count()
    valor_total = faturas_qs.aggregate(Sum('valor'))['valor__sum'] or 0
    
    faturas_por_estado = faturas_qs.values('estado').annotate(
        count=Count('id_fatura'),
        total=Sum('valor')
    )
    
    faturas_detalhes = []
    for fatura in faturas_qs.order_by('-id_fatura')[:100]:  # Limitar a 100 registros
        consulta = fatura.id_consulta
        faturas_detalhes.append({
            'id_fatura': fatura.id_fatura,
            'data_pagamento': fatura.data_pagamento.strftime('%Y-%m-%d') if fatura.data_pagamento else None,
            'valor': float(fatura.valor),
            'estado': fatura.estado,
            'metodo_pagamento': fatura.metodo_pagamento,
            'consulta': {
                'id_consulta': consulta.id_consulta,
                'data_consulta': consulta.data_consulta.strftime('%Y-%m-%d') if consulta.data_consulta else None,
                'hora_consulta': consulta.hora_consulta.strftime('%H:%M') if consulta.hora_consulta else None,
                'paciente': {
                    'id': consulta.id_paciente.id_paciente,
                    'nome': consulta.id_paciente.id_utilizador.nome,
                    'n_utente': consulta.id_paciente.id_utilizador.n_utente
                },
                'medico': {
                    'id': consulta.id_medico.id_medico,
                    'nome': consulta.id_medico.id_utilizador.nome,
                    'especialidade': consulta.id_medico.id_especialidade.nome_especialidade if consulta.id_medico.id_especialidade else None
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
    
    consultas = Consulta.objects.select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador',
        'id_medico__id_especialidade'
    ).all().order_by('-data_consulta')
    
    if data_inicio:
        consultas = consultas.filter(data_consulta__gte=data_inicio)
    if data_fim:
        consultas = consultas.filter(data_consulta__lte=data_fim)
    if estado:
        consultas = consultas.filter(estado=estado)
    if medico_id:
        consultas = consultas.filter(id_medico__id_medico=medico_id)
    
    for consulta in consultas:
        try:
            fatura = Fatura.objects.get(id_consulta=consulta)
            valor = fatura.valor
            fatura_id = fatura.id_fatura
        except Fatura.DoesNotExist:
            valor = 0
            fatura_id = 'N/A'
        
        writer.writerow([
            consulta.id_consulta,
            consulta.data_consulta.strftime('%d/%m/%Y') if consulta.data_consulta else '',
            consulta.hora_consulta.strftime('%H:%M') if consulta.hora_consulta else '',
            consulta.id_paciente.id_utilizador.nome,
            consulta.id_medico.id_utilizador.nome,
            consulta.id_medico.id_especialidade.nome_especialidade if consulta.id_medico.id_especialidade else 'N/A',
            consulta.estado,
            consulta.motivo or '',
            f"{valor:.2f}".replace('.', ','),
            fatura_id,
            consulta.criado_em.strftime('%d/%m/%Y %H:%M') if consulta.criado_em else ''
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
    
    consultas_qs = Consulta.objects.select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador',
        'id_medico__id_especialidade'
    ).all()
    
    if data_inicio:
        consultas_qs = consultas_qs.filter(data_consulta__gte=data_inicio)
    if data_fim:
        consultas_qs = consultas_qs.filter(data_consulta__lte=data_fim)
    if estado:
        consultas_qs = consultas_qs.filter(estado=estado)
    if medico_id:
        consultas_qs = consultas_qs.filter(id_medico__id_medico=medico_id)
    
    total_consultas = consultas_qs.count()
    consultas_por_estado = consultas_qs.values('estado').annotate(
        count=Count('id_consulta')
    )
    
    consultas_por_medico = consultas_qs.values(
        'id_medico__id_utilizador__nome'
    ).annotate(
        count=Count('id_consulta')
    ).order_by('-count')[:10]
    
    consultas_detalhes = []
    for consulta in consultas_qs.order_by('-data_consulta')[:100]:
        try:
            fatura = Fatura.objects.get(id_consulta=consulta)
            fatura_info = {
                'id': fatura.id_fatura,
                'valor': float(fatura.valor),
                'estado': fatura.estado
            }
        except Fatura.DoesNotExist:
            fatura_info = None
        
        consultas_detalhes.append({
            'id_consulta': consulta.id_consulta,
            'data_consulta': consulta.data_consulta.strftime('%Y-%m-%d') if consulta.data_consulta else None,
            'hora_consulta': consulta.hora_consulta.strftime('%H:%M') if consulta.hora_consulta else None,
            'estado': consulta.estado,
            'motivo': consulta.motivo,
            'paciente': {
                'id': consulta.id_paciente.id_paciente,
                'nome': consulta.id_paciente.id_utilizador.nome
            },
            'medico': {
                'id': consulta.id_medico.id_medico,
                'nome': consulta.id_medico.id_utilizador.nome,
                'especialidade': consulta.id_medico.id_especialidade.nome_especialidade if consulta.id_medico.id_especialidade else None
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