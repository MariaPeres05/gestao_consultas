from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
from .models import Medico, Consulta, Disponibilidade, Paciente, Receita
from .decorators import role_required
from .mongo_client import NotasClinicasService
import logging

logger = logging.getLogger(__name__)

@login_required
@role_required('medico')
def medico_dashboard(request):
    """Dashboard principal do médico"""
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    hoje = timezone.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoje.replace(day=1)
    
    # Consultas de hoje
    consultas_hoje = Consulta.objects.filter(
        id_medico=medico,
        data_consulta=hoje
    ).select_related('id_paciente__id_utilizador').order_by('data_consulta')
    
    # Adicionar propriedade can_cancel_24h a cada consulta
    for consulta in consultas_hoje:
        consulta_datetime = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
        if timezone.is_aware(consulta_datetime):
            consulta_datetime = timezone.make_naive(consulta_datetime)
        consulta_datetime = timezone.make_aware(consulta_datetime)
        tempo_restante = consulta_datetime - timezone.now()
        consulta.can_cancel_24h = tempo_restante >= timedelta(hours=24)
    
    # Consultas da semana - count only confirmed (accepted by both parties) and not canceled
    consultas_semana = Consulta.objects.filter(
        id_medico=medico,
        data_consulta__range=[inicio_semana, fim_semana],
        estado='confirmada'
    ).count()
    
    # Consultas do mês - count only confirmed (accepted by both parties) and not canceled
    consultas_mes = Consulta.objects.filter(
        id_medico=medico,
        data_consulta__gte=inicio_mes,
        estado='confirmada'
    ).count()
    
    # Próximas consultas (próximos 7 dias)
    proximas_consultas = Consulta.objects.filter(
        id_medico=medico,
        data_consulta__gte=timezone.now().date(),
        estado__in=['agendada', 'confirmada']
    ).select_related('id_paciente__id_utilizador').order_by('data_consulta')[:10]
    
    # Adicionar propriedade can_cancel_24h a cada consulta
    for consulta in proximas_consultas:
        consulta_datetime = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
        if timezone.is_aware(consulta_datetime):
            consulta_datetime = timezone.make_naive(consulta_datetime)
        consulta_datetime = timezone.make_aware(consulta_datetime)
        tempo_restante = consulta_datetime - timezone.now()
        consulta.can_cancel_24h = tempo_restante >= timedelta(hours=24)
    
    # Pedidos pendentes de confirmação
    pedidos_pendentes = Consulta.objects.filter(
        id_medico=medico,
        estado='agendada'
    ).count()
    
    context = {
        'medico': medico,
        'consultas_hoje': consultas_hoje,
        'consultas_semana': consultas_semana,
        'consultas_mes': consultas_mes,
        'proximas_consultas': proximas_consultas,
        'pedidos_pendentes': pedidos_pendentes,
        'hoje': hoje,
    }
    
    return render(request, 'medico/dashboard.html', context)


@login_required
@role_required('medico')
def medico_agenda(request):
    """Visualizar e gerenciar agenda com disponibilidades integradas"""
    from core.models import UnidadeSaude
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    # Handle POST requests for availability management
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'agendar_consulta':
            paciente_id = request.POST.get('paciente_id')
            data_consulta = request.POST.get('data_consulta')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            
            try:
                paciente = Paciente.objects.get(id_paciente=paciente_id)
                
                # Validar data/hora
                if not data_consulta or not hora_inicio or not hora_fim:
                    messages.error(request, "Data e horas são obrigatórias.")
                    return redirect('medico_agenda')
                
                # Converter strings para objetos date e time
                data_obj = datetime.strptime(data_consulta, '%Y-%m-%d').date()
                hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
                hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
                
                # Validar que fim é depois de início
                if hora_fim_obj <= hora_inicio_obj:
                    messages.error(request, "O fim da consulta deve ser posterior ao início.")
                    return redirect('medico_agenda')
                
                # Verificar se já existe consulta no mesmo horário para o médico
                if Consulta.objects.filter(
                    id_medico=medico,
                    data_consulta=data_obj,
                    hora_consulta=hora_inicio_obj
                ).exclude(estado='cancelada').exists():
                    messages.error(request, "Já existe uma consulta agendada neste horário.")
                    return redirect('medico_agenda')
                
                # Procurar disponibilidade que cubra este período
                disponibilidade = Disponibilidade.objects.filter(
                    id_medico=medico,
                    data=data_obj,
                    hora_inicio__lte=hora_inicio_obj,
                    hora_fim__gte=hora_fim_obj
                ).exclude(status_slot__iexact='booked').first()
                
                # Criar a consulta com estado='agendada' - médico já aceita, aguarda paciente
                consulta = Consulta.objects.create(
                    id_paciente=paciente,
                    id_medico=medico,
                    id_disponibilidade=disponibilidade,
                    data_consulta=data_obj,
                    hora_consulta=hora_inicio_obj,
                    estado='agendada',  # Aguarda aceitação do paciente
                    medico_aceitou=True,  # Médico já aceita automaticamente ao criar
                    paciente_aceitou=False  # Paciente precisa aceitar
                )
                
                messages.success(request, f"Consulta agendada com sucesso para {paciente.id_utilizador.nome}. Aguarda aceitação do paciente.")
                return redirect('medico_agenda')
                
            except Paciente.DoesNotExist:
                messages.error(request, "Paciente não encontrado.")
                return redirect('medico_agenda')
            except Exception as e:
                messages.error(request, f"Erro ao agendar consulta: {str(e)}")
                return redirect('medico_agenda')
        
        elif action == 'criar_disponibilidade_e_agendar':
            paciente_id = request.POST.get('paciente_id')
            data_consulta = request.POST.get('data_consulta')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            unidade_id = request.POST.get('unidade_id')
            disp_hora_inicio = request.POST.get('disp_hora_inicio')
            disp_hora_fim = request.POST.get('disp_hora_fim')
            
            try:
                from core.models import UnidadeSaude
                
                paciente = Paciente.objects.get(id_paciente=paciente_id)
                unidade = UnidadeSaude.objects.get(id_unidade=unidade_id)
                
                # Converter strings
                data_obj = datetime.strptime(data_consulta, '%Y-%m-%d').date()
                hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
                hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
                disp_inicio_obj = datetime.strptime(disp_hora_inicio, '%H:%M').time()
                disp_fim_obj = datetime.strptime(disp_hora_fim, '%H:%M').time()
                
                # Validar que a disponibilidade cobre a consulta
                if disp_inicio_obj > hora_inicio_obj or disp_fim_obj < hora_fim_obj:
                    messages.error(request, "A disponibilidade deve cobrir todo o período da consulta.")
                    return redirect('medico_agenda')
                
                # Criar disponibilidade
                disponibilidade = Disponibilidade.objects.create(
                    id_medico=medico,
                    id_unidade=unidade,
                    data=data_obj,
                    hora_inicio=disp_inicio_obj,
                    hora_fim=disp_fim_obj,
                    status_slot='disponivel',
                    duracao_slot=30
                )
                
                # Criar consulta com estado='agendada' - médico aceita, aguarda paciente
                consulta = Consulta.objects.create(
                    id_paciente=paciente,
                    id_medico=medico,
                    id_disponibilidade=disponibilidade,
                    data_consulta=data_obj,
                    hora_consulta=hora_inicio_obj,
                    estado='agendada',  # Aguarda aceitação do paciente
                    medico_aceitou=True,  # Médico aceita ao criar
                    paciente_aceitou=False  # Paciente precisa aceitar
                )
                
                messages.success(request, f"Disponibilidade criada e consulta agendada para {paciente.id_utilizador.nome}. Aguarda aceitação do paciente.")
                return redirect('medico_agenda')
                
            except Exception as e:
                messages.error(request, f"Erro: {str(e)}")
                return redirect('medico_agenda')
        
        elif action == 'set_disponibilidade':
            data = request.POST.get('data')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            unidade_id = request.POST.get('unidade')
            disponivel = request.POST.get('disponivel') == 'on'
            
            # Get selected unidade
            from core.models import UnidadeSaude
            if not unidade_id:
                messages.error(request, "Por favor, selecione uma unidade de saúde.")
                return redirect('medico_agenda')
            
            try:
                unidade = UnidadeSaude.objects.get(id_unidade=unidade_id)
            except UnidadeSaude.DoesNotExist:
                messages.error(request, "Unidade de saúde não encontrada.")
                return redirect('medico_agenda')
            
            status = 'disponivel' if disponivel else 'indisponivel'
            duracao = 30  # default slot duration
            
            try:
                disp, created = Disponibilidade.objects.get_or_create(
                    id_medico=medico,
                    id_unidade=unidade,
                    data=data,
                    hora_inicio=hora_inicio,
                    defaults={
                        'hora_fim': hora_fim,
                        'status_slot': status,
                        'duracao_slot': duracao
                    }
                )
                
                if not created:
                    disp.hora_fim = hora_fim
                    disp.status_slot = status
                    disp.save()
                    messages.success(request, "Disponibilidade atualizada!")
                else:
                    messages.success(request, "Disponibilidade criada!")
            except Exception as e:
                messages.error(request, f"Erro: {str(e)}")
        
        elif action == 'set_ferias':
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            motivo = request.POST.get('motivo', 'Férias')
            motivo_outro = request.POST.get('motivo_outro', '')
            
            if motivo == 'outro' and motivo_outro:
                motivo = motivo_outro
            
            # Get first available unidade
            from core.models import UnidadeSaude
            unidade = UnidadeSaude.objects.first()
            if not unidade:
                messages.error(request, "Nenhuma unidade de saúde disponível. Contacte o administrador.")
                return redirect('medico_agenda')
            
            duracao = 30  # default slot duration
            
            try:
                start = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                end = datetime.strptime(data_fim, '%Y-%m-%d').date()
                
                dias_criados = 0
                current = start
                while current <= end:
                    disp, created = Disponibilidade.objects.get_or_create(
                        id_medico=medico,
                        data=current,
                        hora_inicio='00:00',
                        defaults={
                            'id_unidade': unidade,
                            'hora_fim': '23:59',
                            'status_slot': 'ferias',
                            'duracao_slot': duracao
                        }
                    )
                    if not created:
                        disp.status_slot = 'ferias'
                        disp.save()
                    dias_criados += 1
                    current += timedelta(days=1)
                
                messages.success(request, f"Período de {dias_criados} dia(s) marcado como indisponível!")
            except Exception as e:
                messages.error(request, f"Erro: {str(e)}")
        
        return redirect('medico_agenda')
    
    # Calendar month filter (for calendar tab)
    cal_year = request.GET.get('cal_year')
    cal_month = request.GET.get('cal_month')
    
    if cal_year and cal_month:
        cal_year = int(cal_year)
        cal_month = int(cal_month)
        mes_inicio = datetime(cal_year, cal_month, 1).date()
    else:
        hoje = timezone.now().date()
        mes_inicio = hoje.replace(day=1)
        cal_year = hoje.year
        cal_month = hoje.month
    
    # Calculate end of month
    if mes_inicio.month == 12:
        mes_fim = mes_inicio.replace(year=mes_inicio.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        mes_fim = mes_inicio.replace(month=mes_inicio.month + 1, day=1) - timedelta(days=1)
    
    # Fetch data for calendar (entire month)
    consultas_mes = Consulta.objects.filter(
        id_medico=medico,
        data_consulta__range=[mes_inicio, mes_fim]
    ).exclude(estado='cancelada').select_related('id_paciente__id_utilizador').order_by('data_consulta', 'hora_consulta')
    
    # Adicionar propriedade can_cancel_24h a cada consulta do mês (para o calendário)
    agora = timezone.now()
    for consulta in consultas_mes:
        data_hora_consulta = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
        data_hora_consulta = timezone.make_aware(data_hora_consulta, timezone.get_current_timezone())
        tempo_restante = data_hora_consulta - agora
        consulta.can_cancel_24h = tempo_restante >= timedelta(hours=24)
    
    disponibilidades_mes = Disponibilidade.objects.filter(
        id_medico=medico,
        data__range=[mes_inicio, mes_fim]
    ).order_by('data', 'hora_inicio')
    
    # Filtros de data (for consultas tab)
    periodo = request.GET.get('periodo', 'semana')
    data_inicial = request.GET.get('data_inicial')
    
    hoje = timezone.now().date()
    
    if data_inicial:
        data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d').date()
    else:
        data_inicial = hoje
    
    if periodo == 'dia':
        data_final = data_inicial
    elif periodo == 'semana':
        inicio_semana = data_inicial - timedelta(days=data_inicial.weekday())
        data_inicial = inicio_semana
        data_final = inicio_semana + timedelta(days=6)
    else:  # mês
        data_inicial = data_inicial.replace(day=1)
        if data_inicial.month == 12:
            data_final = data_inicial.replace(year=data_inicial.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            data_final = data_inicial.replace(month=data_inicial.month + 1, day=1) - timedelta(days=1)
    
    # Buscar consultas (filtered by period)
    consultas = Consulta.objects.filter(
        id_medico=medico,
        data_consulta__range=[data_inicial, data_final]
    ).exclude(estado='cancelada').select_related('id_paciente__id_utilizador').order_by('data_consulta', 'hora_consulta')
    
    # Adicionar propriedade can_cancel_24h a cada consulta (para o tab de consultas)
    for consulta in consultas:
        data_hora_consulta = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
        data_hora_consulta = timezone.make_aware(data_hora_consulta, timezone.get_current_timezone())
        tempo_restante = data_hora_consulta - agora
        consulta.can_cancel_24h = tempo_restante >= timedelta(hours=24)
    
    # Buscar disponibilidades para o período selecionado (consultas tab)
    disponibilidades = Disponibilidade.objects.filter(
        id_medico=medico,
        data__range=[data_inicial, data_final]
    ).order_by('data', 'hora_inicio')
   
   # Buscar disponibilidades futuras NÃO ocupadas (status diferente de 'booked')
    disponibilidades_futuras = Disponibilidade.objects.filter(
    Q(id_medico=medico),
    Q(data__gte=hoje),
    ~Q(status_slot__iexact='booked')  # Excluir slots já ocupados
    ).order_by('data', 'hora_inicio')[:100]
    
    # Get all unidades for dropdown
    unidades = UnidadeSaude.objects.all().order_by('nome_unidade')
    
    # Get active patients for scheduling
    pacientes = Paciente.objects.select_related('id_utilizador').filter(
        id_utilizador__ativo=True
    ).order_by('id_utilizador__nome')
    
    # Get future disponibilidades for scheduling (next 60 days)
    disponibilidades_agendar = Disponibilidade.objects.filter(
    id_medico=medico,
    data__gte=hoje,
    status_slot__in=['disponivel', 'available']  # Apenas disponíveis
    ).order_by('data', 'hora_inicio')[:50]
    
    context = {
        'medico': medico,
        'consultas': consultas,
        'disponibilidades': disponibilidades,
        'disponibilidades_futuras': disponibilidades_futuras,
        'consultas_mes': consultas_mes,
        'disponibilidades_mes': disponibilidades_mes,
        'periodo': periodo,
        'data_inicial': data_inicial,
        'data_final': data_final,
        'hoje': hoje,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'unidades': unidades,
        'pacientes': pacientes,
        'disponibilidades_agendar': disponibilidades_agendar,
    }
    
    return render(request, 'medico/agenda.html', context)

@login_required
@role_required('medico')
def medico_excluir_disponibilidade(request, disponibilidade_id):
    """Excluir uma disponibilidade que não está ocupada"""
    from core.models import UnidadeSaude
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    try:
        disponibilidade = Disponibilidade.objects.get(
            id_disponibilidade=disponibilidade_id,
            id_medico=medico
        )
        
        if Consulta.objects.filter(id_disponibilidade=disponibilidade).exists():
            messages.error(request, "Não é possível excluir uma disponibilidade que já tem consultas marcadas.")
        else:
            disponibilidade.delete()
            messages.success(request, "Disponibilidade excluída com sucesso!")
            
    except Disponibilidade.DoesNotExist:
        messages.error(request, "Disponibilidade não encontrada.")
    
    return redirect('medico_agenda')

@login_required
@role_required('medico')
def medico_confirmar_consulta(request, consulta_id):
    """Confirmar pedido de consulta"""
    medico = Medico.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_medico=medico)
    
    if consulta.estado == 'agendada':
        consulta.medico_aceitou = True
        
        # Se o paciente já aceitou, confirma a consulta
        if consulta.paciente_aceitou:
            consulta.estado = 'confirmada'
            messages.success(request, f"Consulta com {consulta.id_paciente.id_utilizador.nome} confirmada!")
        else:
            # Senão, mantém como agendada esperando aceitação do paciente
            messages.success(request, f"Aceitaste a consulta. A aguardar aceitação do paciente.")
        
        consulta.save()
    else:
        messages.warning(request, "Esta consulta não pode ser confirmada.")
    
    return redirect('medico_dashboard')


@login_required
@role_required('medico')
def medico_recusar_consulta(request, consulta_id):
    """Recusar pedido de consulta"""
    medico = Medico.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_medico=medico)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Recusado pelo médico')
        consulta.estado = 'cancelada'
        consulta.motivo_consulta = f"[RECUSADA] {motivo}"
        consulta.save()
        messages.success(request, "Consulta recusada.")
        return redirect('medico_dashboard')
    
    return render(request, 'medico/recusar_consulta.html', {'consulta': consulta})


@login_required
@role_required('medico')
def medico_cancelar_consulta(request, consulta_id):
    """Médico cancela uma consulta confirmada (até 24h antes)"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    medico = Medico.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_medico=medico)
    
    # Combinar data e hora da consulta
    consulta_datetime = datetime.combine(consulta.data_consulta, consulta.hora_consulta)
    if timezone.is_aware(consulta_datetime):
        consulta_datetime = timezone.make_naive(consulta_datetime)
    consulta_datetime = timezone.make_aware(consulta_datetime)
    
    # Verificar se faltam mais de 24 horas
    tempo_restante = consulta_datetime - timezone.now()
    
    if tempo_restante < timedelta(hours=24):
        messages.error(request, "Não é possível cancelar consultas com menos de 24 horas de antecedência.")
        return redirect('medico_dashboard')
    
    if consulta.estado in ['agendada', 'confirmada']:
        consulta.estado = 'cancelada'
        consulta.motivo = "Cancelada pelo médico"
        consulta.save()
        messages.success(request, "Consulta cancelada com sucesso.")
    else:
        messages.warning(request, "Esta consulta não pode ser cancelada.")
    
    return redirect('medico_dashboard')


@login_required
@role_required('medico')
@login_required
@role_required('medico')
def medico_detalhes_consulta(request, consulta_id):
    """Ver detalhes da consulta e informações do paciente"""
    medico = Medico.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(
        Consulta.objects.select_related('id_paciente__id_utilizador'),
        id_consulta=consulta_id,
        id_medico=medico
    )
    
    paciente = consulta.id_paciente
    
    # Histórico de consultas do paciente com este médico
    historico = Consulta.objects.filter(
        id_paciente=paciente,
        id_medico=medico,
        estado='realizada'
    ).order_by('-data_consulta')[:10]
    
    # Get notas clínicas from MongoDB if available
    notas_clinicas_service = NotasClinicasService()
    mongo_notes = notas_clinicas_service.get_note_by_consulta(consulta_id)
    
    # Get all patient notes from MongoDB
    patient_history_notes = notas_clinicas_service.get_notes_by_patient(paciente.id_paciente, limit=10)
    
    context = {
        'consulta': consulta,
        'paciente': paciente,
        'historico': historico,
        'mongo_notes': mongo_notes,
        'patient_history_notes': patient_history_notes,
    }
    
    return render(request, 'medico/detalhes_consulta.html', context)


@login_required
@role_required('medico')
def medico_registar_consulta(request, consulta_id):
    """Registar notas médicas e receitas após a consulta - salva no MongoDB"""
    medico = Medico.objects.get(id_utilizador=request.user)
    consulta = get_object_or_404(Consulta, id_consulta=consulta_id, id_medico=medico)
    
    if request.method == 'POST':
        # Collect all notas clínicas data
        # Parse comma-separated values into arrays
        sintomas_str = request.POST.get('sintomas', '')
        sintomas = [s.strip() for s in sintomas_str.split(',') if s.strip()] if sintomas_str else []
        
        prescricoes_str = request.POST.get('prescricoes', '')
        prescricoes = [p.strip() for p in prescricoes_str.split('\n') if p.strip()] if prescricoes_str else []
        
        exames_str = request.POST.get('exames_solicitados', '')
        exames = [e.strip() for e in exames_str.split(',') if e.strip()] if exames_str else []
        
        notes_data = {
            'notas_clinicas': request.POST.get('notas_clinicas', ''),
            'observacoes': request.POST.get('observacoes', ''),
            'diagnostico': request.POST.get('diagnostico', ''),
            'tratamento': request.POST.get('tratamento', ''),
            'sintomas': sintomas,
            'prescricoes': prescricoes,
            'exames_solicitados': exames,
            'seguimento': request.POST.get('seguimento', ''),
            'exame_fisico': {
                'pressao_arterial': request.POST.get('pressao_arterial', ''),
                'temperatura': request.POST.get('temperatura', ''),
                'frequencia_cardiaca': request.POST.get('frequencia_cardiaca', ''),
                'peso': request.POST.get('peso', ''),
                'altura': request.POST.get('altura', ''),
            }
        }
        
        # Save to MongoDB - update if exists, create if not
        notas_clinicas_service = NotasClinicasService()
        existing_note = notas_clinicas_service.get_note_by_consulta(consulta.id_consulta)
        
        if existing_note is not None:
            # Update existing note
            success = notas_clinicas_service.update_note(consulta.id_consulta, notes_data)
            if success:
                logger.info(f"Updated nota clínica for consulta {consulta.id_consulta}")
            note_id = existing_note.get('_id')
        else:
            # Create new note
            note_id = notas_clinicas_service.create_note(
                consulta_id=consulta.id_consulta,
                medico_id=medico.id_medico,
                paciente_id=consulta.id_paciente.id_paciente,
                notes_data=notes_data
            )

        
        # Update consulta status in PostgreSQL (but don't store notes - they're in MongoDB)
        consulta.estado = 'realizada'
        consulta.save()
        
        # Create receita if prescriptions exist
        if notes_data['prescricoes']:
            for prescricao in notes_data['prescricoes']:
                if prescricao.strip():
                    Receita.objects.create(
                        id_consulta=consulta,
                        medicamento=prescricao,
                        dosagem='Conforme prescrição',
                        instrucoes=notes_data['diagnostico'][:255],
                        data_prescricao=timezone.now().date()
                    )
        
        if note_id or success:
            messages.success(request, "Consulta registada com sucesso! Notas clínicas salvas no MongoDB.")
        else:
            messages.warning(request, "Consulta registada, mas houve um problema ao salvar as notas clínicas detalhadas.")
        
        return redirect('medico_dashboard')
    
    # GET request - show form
    # Load existing notes from MongoDB
    notas_clinicas_service = NotasClinicasService()
    mongo_notes = notas_clinicas_service.get_note_by_consulta(consulta_id)
    
    context = {
        'consulta': consulta,
        'mongo_notes': mongo_notes,
        'existing_notes': mongo_notes,  # Keep both for compatibility
    }
    
    return render(request, 'medico/registar_consulta.html', context)


@login_required
@role_required('medico')
@login_required
@role_required('medico')
def medico_agendar_consulta(request):
    """Permite ao médico agendar uma consulta diretamente para um paciente"""
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    if request.method == 'POST':
        paciente_id = request.POST.get('paciente_id')
        data_consulta = request.POST.get('data_consulta')
        hora_consulta = request.POST.get('hora_consulta')
        id_disponibilidade = request.POST.get('id_disponibilidade')
        
        try:
            paciente = Paciente.objects.get(id_paciente=paciente_id)
            
            # Validar data/hora
            if not data_consulta or not hora_consulta:
                messages.error(request, "Data e hora são obrigatórias.")
                return redirect('medico_agendar_consulta')
            
            # Converter strings para objetos date e time
            from datetime import datetime
            data_obj = datetime.strptime(data_consulta, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_consulta, '%H:%M').time()
            
            # Verificar se já existe consulta no mesmo horário para o médico
            if Consulta.objects.filter(
                id_medico=medico,
                data_consulta=data_obj,
                hora_consulta=hora_obj
            ).exclude(estado='cancelada').exists():
                messages.error(request, "Já existe uma consulta agendada neste horário.")
                return redirect('medico_agendar_consulta')
            
            # Se foi selecionada uma disponibilidade, associá-la
            disponibilidade = None
            if id_disponibilidade:
                try:
                    disponibilidade = Disponibilidade.objects.get(id_disponibilidade=id_disponibilidade)
                except Disponibilidade.DoesNotExist:
                    pass
            
            # Criar a consulta com estado='confirmada' já que o médico está agendando
            consulta = Consulta.objects.create(
                id_paciente=paciente,
                id_medico=medico,
                id_disponibilidade=disponibilidade,
                data_consulta=data_obj,
                hora_consulta=hora_obj,
                estado='confirmada',  # Médico já confirma ao criar
                medico_aceitou=True,  # Médico já aceita automaticamente
                paciente_aceitou=True  # Assumir que paciente também aceita (ou pode ser False)
            )
            
            messages.success(request, f"Consulta agendada com sucesso para {paciente.id_utilizador.nome}.")
            return redirect('medico_agenda')
            
        except Paciente.DoesNotExist:
            messages.error(request, "Paciente não encontrado.")
            return redirect('medico_agendar_consulta')
        except Exception as e:
            messages.error(request, f"Erro ao agendar consulta: {str(e)}")
            return redirect('medico_agendar_consulta')
    
    # GET: mostrar formulário
    pacientes = Paciente.objects.select_related('id_utilizador').filter(id_utilizador__ativo=True).order_by('id_utilizador__nome')
    
    # Buscar disponibilidades futuras do médico
    from datetime import date
    hoje = date.today()
    disponibilidades = Disponibilidade.objects.filter(
        id_medico=medico,
        data__gte=hoje
    ).exclude(status_slot__iexact='booked').order_by('data', 'hora_inicio')[:50]
    
    context = {
        'pacientes': pacientes,
        'disponibilidades': disponibilidades,
    }
    return render(request, 'medico/agendar_consulta.html', context)


@login_required
@role_required('medico')
def medico_verificar_disponibilidade(request):
    """AJAX endpoint to verify if disponibilidade exists for given time"""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        return JsonResponse({'error': 'Medico not found'}, status=404)
    
    data = request.POST.get('data')
    hora_inicio = request.POST.get('hora_inicio')
    hora_fim = request.POST.get('hora_fim')
    
    if not data or not hora_inicio or not hora_fim:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
        
        # Check if disponibilidade exists that covers this time period
        disponibilidade_exists = Disponibilidade.objects.filter(
            id_medico=medico,
            data=data_obj,
            hora_inicio__lte=hora_inicio_obj,
            hora_fim__gte=hora_fim_obj
        ).exclude(status_slot__iexact='booked').exists()
        
        return JsonResponse({'exists': disponibilidade_exists})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)