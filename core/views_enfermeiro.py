# core/views_enfermeiro.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Utilizador,
    Enfermeiro,
    Consulta,
    Paciente,
    Medico,
    Fatura,
    Receita,
    UnidadeSaude,
    Disponibilidade,
    Especialidade,
)
from .decorators import role_required


@login_required
@role_required('enfermeiro')
def enfermeiro_dashboard(request):
    """Dashboard principal do enfermeiro."""
    try:
        enfermeiro = Enfermeiro.objects.select_related('id_utilizador').get(
            id_utilizador=request.user
        )
    except Enfermeiro.DoesNotExist:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')
    
    # Estatísticas
    hoje = timezone.now().date()
    
    # Consultas de hoje 
    consultas_hoje = Consulta.objects.filter(
        data_consulta=hoje,
        estado='confirmada'
    ).count()
    
    # Consultas pendentes (agendadas mas não realizadas)
    consultas_pendentes = Consulta.objects.filter(
        estado__in=['agendada', 'marcada', 'confirmada']
    ).count()
    
    # Pacientes atendidos esta semana
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    pacientes_semana = Consulta.objects.filter(
        data_consulta__gte=inicio_semana,
        estado='realizada'
    ).values('id_paciente').distinct().count()
    
    # Próximas consultas
    proximas_consultas = Consulta.objects.filter(
        data_consulta__gte=hoje,
        estado__in=['agendada', 'marcada', 'confirmada']
    ).select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador'
    ).order_by('data_consulta', 'hora_consulta')[:10]
    
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
    try:
        enfermeiro = Enfermeiro.objects.select_related('id_utilizador').get(
            id_utilizador=request.user
        )
    except Enfermeiro.DoesNotExist:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')
    
    # Filtros
    estado_filter = request.GET.get('estado', '')
    data_filter = request.GET.get('data', '')
    medico_filter = request.GET.get('medico', '')
    
    consultas = Consulta.objects.all().select_related(
        'id_paciente__id_utilizador',
        'id_medico__id_utilizador',
        'id_medico__id_especialidade'
    )
    
    if estado_filter:
        consultas = consultas.filter(estado=estado_filter)
    
    if data_filter:
        try:
            data_parsed = datetime.strptime(data_filter, '%Y-%m-%d').date()
            consultas = consultas.filter(data_consulta=data_parsed)
        except:
            pass
    
    if medico_filter:
        consultas = consultas.filter(id_medico__id_medico=medico_filter)
    
    consultas = consultas.order_by('-data_consulta', 'hora_consulta')[:100]
    
    # Todos os médicos para o filtro
    medicos = Medico.objects.all().select_related('id_utilizador').distinct()
    
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
    from core.models import Especialidade, UnidadeSaude
    
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
            
            # Criar consulta - enfermeiro marca, ambos precisam aceitar
            consulta = Consulta.objects.create(
                id_paciente=paciente,
                id_medico=disponibilidade.id_medico,
                id_disponibilidade=disponibilidade,
                data_consulta=disponibilidade.data,
                hora_consulta=hora_inicio_obj,
                motivo=motivo_consulta or "Marcação pelo enfermeiro",
                estado='agendada',  # Aguarda confirmação do médico e paciente
                medico_aceitou=False,  # Médico precisa aceitar
                paciente_aceitou=False  # Paciente precisa aceitar
            )
            
            success_msg = f"Consulta agendada para {paciente.id_utilizador.nome} com Dr(a). {disponibilidade.id_medico.id_utilizador.nome} em {disponibilidade.data.strftime('%d/%m/%Y')} das {hora_inicio} às {hora_fim}. Aguarda confirmação do médico e paciente."
            messages.success(request, success_msg)
            return redirect('enfermeiro_consultas')
            
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
    
    return render(request, 'enfermeiro/consulta_form.html', context)


@login_required
@role_required('enfermeiro')
def enfermeiro_pacientes(request):
    """Lista pacientes."""
    try:
        enfermeiro = Enfermeiro.objects.select_related('id_utilizador').get(
            id_utilizador=request.user
        )
    except Enfermeiro.DoesNotExist:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')
    
    # Buscar pacientes que já tiveram consultas
    pacientes = Paciente.objects.filter(
        consultas__isnull=False
    ).select_related('id_utilizador').annotate(
        total_consultas=Count('consultas')
    ).distinct().order_by('id_utilizador__nome')
    
    # Filtro por nome
    search = request.GET.get('search', '')
    if search:
        pacientes = pacientes.filter(
            Q(id_utilizador__nome__icontains=search) |
            Q(id_utilizador__email__icontains=search) |
            Q(id_utilizador__n_utente__icontains=search)
        )
    
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
    try:
        enfermeiro = Enfermeiro.objects.select_related('id_utilizador').get(
            id_utilizador=request.user
        )
    except Enfermeiro.DoesNotExist:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')
    
    paciente = get_object_or_404(Paciente.objects.select_related('id_utilizador'), id_paciente=paciente_id)
    
    # Histórico de consultas
    consultas = Consulta.objects.filter(
        id_paciente=paciente
    ).select_related(
        'id_medico__id_utilizador',
        'id_medico__id_especialidade'
    ).order_by('-data_consulta', '-hora_consulta')
    
    # Faturas
    faturas = Fatura.objects.filter(
        id_consulta__id_paciente=paciente
    ).select_related('id_consulta').order_by('-data_pagamento')
    
    # Receitas
    receitas = Receita.objects.filter(
        id_consulta__id_paciente=paciente
    ).select_related('id_consulta__id_medico__id_utilizador').order_by('-id_receita')
    
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
    try:
        enfermeiro = Enfermeiro.objects.select_related('id_utilizador').get(
            id_utilizador=request.user
        )
    except Enfermeiro.DoesNotExist:
        messages.error(request, "Registo de enfermeiro não encontrado.")
        return redirect('home')
    
    # Período de análise
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if not data_inicio:
        data_inicio = (timezone.now() - timedelta(days=30)).date()
    else:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    
    if not data_fim:
        data_fim = timezone.now().date()
    else:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    # Consultas no período
    consultas_periodo = Consulta.objects.filter(
        data_consulta__range=[data_inicio, data_fim]
    )
    
    # Estatísticas
    total_consultas = consultas_periodo.count()
    consultas_por_estado = consultas_periodo.values('estado').annotate(
        total=Count('id_consulta')
    ).order_by('-total')
    
    consultas_por_medico = consultas_periodo.values(
        'id_medico__id_utilizador__nome'
    ).annotate(
        total=Count('id_consulta')
    ).order_by('-total')[:10]
    
    # Receitas geradas
    total_receitas = Receita.objects.filter(
        id_consulta__data_consulta__range=[data_inicio, data_fim]
    ).count()
    
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
