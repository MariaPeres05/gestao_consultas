from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from django.db.models import Q, Count
from datetime import datetime, timedelta
from .models import Medico, Consulta, Disponibilidade, Paciente, Receita
from .decorators import role_required
from .mongo_client import NotasClinicasService
import logging
import json

logger = logging.getLogger(__name__)

@login_required
@role_required('medico')
def medico_dashboard(request):
    """Dashboard principal do médico usando funções e procedimentos PostgreSQL"""
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    hoje = timezone.now().date()
    
    try:
        # Opção 1: Usar procedimento único (mais eficiente)
        with connection.cursor() as cursor:
            cursor.callproc('obter_dashboard_medico', [medico.id_medico])
            result = cursor.fetchone()
            
            if result:
                # Desempacotar resultados do procedimento
                consultas_hoje_json = result[0] or '[]'
                consultas_semana = result[1] or 0
                consultas_mes = result[2] or 0
                pedidos_pendentes = result[3] or 0
                estatisticas_json = result[4] or '{}'
                
                consultas_hoje = json.loads(consultas_hoje_json)
                estatisticas = json.loads(estatisticas_json)
            else:
                consultas_hoje = []
                consultas_semana = 0
                consultas_mes = 0
                pedidos_pendentes = 0
                estatisticas = {
                    'consultas_realizadas': 0,
                    'consultas_agendadas': 0,
                    'consultas_confirmadas': 0,
                    'consultas_canceladas': 0,
                    'disponibilidades_disponiveis': 0,
                }
        
        # Obter próximas consultas usando função
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_proximas_consultas_medico(%s, %s)", 
                         [medico.id_medico, 10])
            proximas_consultas = []
            for row in cursor.fetchall():
                consulta_dict = {
                    'id_consulta': row[0],
                    'data_consulta': row[1],
                    'hora_consulta': row[2],
                    'estado': row[3],
                    'motivo': row[4],
                    'paciente_nome': row[5],
                    'especialidade_nome': row[7],
                    'nome_unidade': row[8],
                    'can_cancel_24h': row[9]
                }
                proximas_consultas.append(consulta_dict)
                
    except Exception as e:
        # Fallback para funções individuais em caso de erro
        print(f"Erro no procedimento: {e}")
        
        # Usar funções individuais
        consultas_hoje = []
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_consultas_hoje_medico(%s)", [medico.id_medico])
            for row in cursor.fetchall():
                consulta_dict = {
                    'id_consulta': row[0],
                    'data_consulta': row[1],
                    'hora_consulta': row[2],
                    'estado': row[3],
                    'motivo': row[4],
                    'paciente_nome': row[5],
                    'can_cancel_24h': row[10]
                }
                consultas_hoje.append(consulta_dict)
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT contar_consultas_semana_medico(%s)", [medico.id_medico])
            consultas_semana = cursor.fetchone()[0] or 0
            
        with connection.cursor() as cursor:
            cursor.execute("SELECT contar_consultas_mes_medico(%s)", [medico.id_medico])
            consultas_mes = cursor.fetchone()[0] or 0
            
        with connection.cursor() as cursor:
            cursor.execute("SELECT contar_pedidos_pendentes_medico(%s)", [medico.id_medico])
            pedidos_pendentes = cursor.fetchone()[0] or 0
            
        proximas_consultas = []
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_proximas_consultas_medico(%s, %s)", 
                         [medico.id_medico, 10])
            for row in cursor.fetchall():
                consulta_dict = {
                    'id_consulta': row[0],
                    'data_consulta': row[1],
                    'hora_consulta': row[2],
                    'estado': row[3],
                    'motivo': row[4],
                    'paciente_nome': row[5],
                    'especialidade_nome': row[7],
                    'nome_unidade': row[8],
                    'can_cancel_24h': row[9]
                }
                proximas_consultas.append(consulta_dict)
                
        estatisticas = {
            'consultas_realizadas': 0,
            'consultas_agendadas': 0,
            'consultas_confirmadas': 0,
            'consultas_canceladas': 0,
            'disponibilidades_disponiveis': 0,
        }
    
    context = {
        'medico': medico,
        'consultas_hoje': consultas_hoje,
        'consultas_semana': consultas_semana,
        'consultas_mes': consultas_mes,
        'proximas_consultas': proximas_consultas,
        'pedidos_pendentes': pedidos_pendentes,
        'estatisticas': estatisticas,
        'hoje': hoje,
    }
    
    return render(request, 'medico/dashboard.html', context)


@login_required
@role_required('medico')
def medico_agenda(request):
    """Visualizar e gerenciar agenda com disponibilidades integradas usando PostgreSQL"""
    hoje = timezone.now().date()
    
    # Verificar se médico existe usando função PostgreSQL
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM verificar_medico_por_utilizador(%s)", [request.user.id_utilizador])
        medico_info = cursor.fetchone()
    
    if not medico_info:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    medico = {
        'id_medico': medico_info[0],
        'nome': medico_info[1],
        'email': medico_info[2],
        'numero_ordem': medico_info[3],
        'especialidade_nome': medico_info[4]
    }
    
    # Handle POST requests for availability management
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'agendar_consulta':
            paciente_id = request.POST.get('paciente_id')
            data_consulta = request.POST.get('data_consulta')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            motivo = request.POST.get('motivo', '')
            
            # Chamar procedimento para agendar consulta
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CALL agendar_consulta_medico(%s, %s, %s, %s, %s, NULL, NULL, %s)
                    """, [
                        medico['id_medico'],
                        int(paciente_id),
                        data_consulta,
                        hora_inicio,
                        hora_fim,
                        motivo
                    ])
                messages.success(request, "Consulta agendada com sucesso")
                    
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
            motivo = request.POST.get('motivo', '')
            
            # Chamar procedimento para criar disponibilidade e agendar
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CALL criar_disponibilidade_e_agendar(%s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, %s)
                    """, [
                        medico['id_medico'],
                        int(paciente_id),
                        data_consulta,
                        hora_inicio,
                        hora_fim,
                        int(unidade_id),
                        disp_hora_inicio,
                        disp_hora_fim,
                        motivo
                    ])
                messages.success(request, "Disponibilidade criada e consulta agendada com sucesso")
                    
            except Exception as e:
                messages.error(request, f"Erro ao criar disponibilidade: {str(e)}")
            
            return redirect('medico_agenda')
        
        elif action == 'set_disponibilidade':
            data = request.POST.get('data')
            hora_inicio = request.POST.get('hora_inicio')
            hora_fim = request.POST.get('hora_fim')
            unidade_id = request.POST.get('unidade')
            disponivel = request.POST.get('disponivel') == 'on'
            
            if not unidade_id:
                messages.error(request, "Por favor, selecione uma unidade de saúde.")
                return redirect('medico_agenda')
            
            # Chamar procedimento para definir disponibilidade
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CALL definir_disponibilidade(%s, %s, %s, %s, %s, %s, NULL, NULL)
                    """, [
                        medico['id_medico'],
                        data,
                        hora_inicio,
                        hora_fim,
                        int(unidade_id),
                        disponivel
                    ])
                messages.success(request, "Disponibilidade definida com sucesso")
                    
            except Exception as e:
                messages.error(request, f"Erro ao definir disponibilidade: {str(e)}")
            
            return redirect('medico_agenda')
        
        elif action == 'set_ferias':
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            motivo = request.POST.get('motivo', 'Férias')
            motivo_outro = request.POST.get('motivo_outro', '')
            
            if motivo == 'outro' and motivo_outro:
                motivo = motivo_outro
            
            # Chamar procedimento para definir férias
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        CALL definir_ferias_medico(%s, %s, %s, %s, NULL, NULL)
                    """, [
                        medico['id_medico'],
                        data_inicio,
                        data_fim,
                        motivo
                    ])
                messages.success(request, f"Férias definidas de {data_inicio} a {data_fim}")
                    
            except Exception as e:
                messages.error(request, f"Erro ao definir férias: {str(e)}")
            
            return redirect('medico_agenda')
    
    # Calendar month filter
    cal_year = request.GET.get('cal_year')
    cal_month = request.GET.get('cal_month')
    
    if cal_year and cal_month:
        cal_year = int(cal_year)
        cal_month = int(cal_month)
    else:
        cal_year = hoje.year
        cal_month = hoje.month
    
    # Obter calendário mensal usando função PostgreSQL
    calendario_mensal = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_calendario_mensal_medico(%s, %s, %s)", 
                     [medico['id_medico'], cal_year, cal_month])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            # Renomear 'id' para 'id_consulta' ou 'id_disponibilidade' conforme o tipo
            if item['tipo'] == 'consulta':
                item['id_consulta'] = item['id']
            else:
                item['id_disponibilidade'] = item['id']
            calendario_mensal.append(item)
    
    # Separar consultas e disponibilidades do calendário
    consultas_mes = [item for item in calendario_mensal if item['tipo'] == 'consulta']
    disponibilidades_mes = [item for item in calendario_mensal if item['tipo'] == 'disponibilidade']
    
    # Filtros de data (for consultas tab)
    periodo = request.GET.get('periodo', 'semana')
    data_inicial = request.GET.get('data_inicial')
    
    if data_inicial:
        data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d').date()
    else:
        data_inicial = hoje
    
    # Obter agenda do período usando função PostgreSQL
    agenda_periodo = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_agenda_medico(%s, %s, NULL, %s)", 
                     [medico['id_medico'], data_inicial, periodo])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            # Renomear 'id' para 'id_consulta' ou 'id_disponibilidade' conforme o tipo
            if item['tipo'] == 'consulta':
                item['id_consulta'] = item['id']
            else:
                item['id_disponibilidade'] = item['id']
            agenda_periodo.append(item)
    
    # Separar consultas e disponibilidades do período
    consultas = [item for item in agenda_periodo if item['tipo'] == 'consulta']
    disponibilidades = [item for item in agenda_periodo if item['tipo'] == 'disponibilidade']
    
    # Calcular data_final baseado no período
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
    
    # Obter disponibilidades futuras não ocupadas
    disponibilidades_futuras = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_disponibilidades_futuras_medico(%s, 100)", 
                     [medico['id_medico']])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            disponibilidades_futuras.append(item)
    
    # Obter unidades de saúde
    unidades = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_unidades_saude()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            unidades.append(dict(zip(columns, row)))
    
    # Obter pacientes ativos
    pacientes = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_pacientes_ativos()")
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            pacientes.append(dict(zip(columns, row)))
    
    # Obter disponibilidades para agendamento
    disponibilidades_agendar = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM obter_disponibilidades_agendar_medico(%s, 50)", 
                     [medico['id_medico']])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            # Calcular se há slots disponíveis
            if item['slots_disponiveis'] > 0:
                disponibilidades_agendar.append(item)
    
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
    """Excluir uma disponibilidade que não está ocupada usando procedimento SQL"""
    from core.models import Medico
    from django.db import connection
    
    try:
        medico = Medico.objects.get(id_utilizador=request.user)
    except Medico.DoesNotExist:
        messages.error(request, "Perfil de médico não encontrado.")
        return redirect('index')
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CALL excluir_disponibilidade(
                    %s,  -- p_disponibilidade_id
                    %s,  -- p_id_medico
                    NULL, -- mensagem (OUT)
                    NULL  -- sucesso (OUT)
                )
            """, [disponibilidade_id, medico.id_medico])
            
            # Obter os parâmetros de saída do CALL
            result = cursor.fetchone()
            if result:
                mensagem, sucesso = result
                if sucesso:
                    messages.success(request, mensagem)
                else:
                    messages.error(request, mensagem)
            else:
                messages.error(request, "Erro ao processar exclusão.")
                
    except Exception as e:
        logger.error(f"Erro ao excluir disponibilidade: {str(e)}")
        messages.error(request, f"Erro ao excluir disponibilidade: {str(e)}")
    
    return redirect('medico_agenda')

@login_required
@role_required('medico')
def medico_confirmar_consulta(request, consulta_id):
    """Confirmar pedido de consulta usando procedimento SQL"""
    from django.db import connection
    
    try:
        # Obter médico usando função SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM obter_medico_por_utilizador(%s)
            """, [request.user.id_utilizador])
            
            medico = cursor.fetchone()
            
        if not medico:
            messages.error(request, "Perfil de médico não encontrado.")
            return redirect('index')
        
        # Verificar se consulta pertence ao médico usando função SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM verificar_consulta_medico(%s, %s)
            """, [consulta_id, medico[0]])  # medico[0] é id_medico
            
            consulta_info = cursor.fetchone()
            
        if not consulta_info or not consulta_info[0]:  # consulta_info[0] é 'existe'
            messages.error(request, "Consulta não encontrada ou não pertence a este médico.")
            return redirect('medico_dashboard')
        
        # Chamar procedure para confirmar consulta
        with connection.cursor() as cursor:
            cursor.execute("CALL confirmar_consulta(%s, %s)", [
                consulta_id,
                'medico'
            ])
        messages.success(request, "Consulta confirmada!")
        
    except Exception as e:
        error_msg = str(e)
        if "não encontrada" in error_msg:
            messages.error(request, "Consulta não encontrada.")
        elif "não pode ser confirmada" in error_msg:
            messages.error(request, "Esta consulta não pode ser confirmada.")
        else:
            messages.error(request, f"Erro ao confirmar consulta: {error_msg}")
    
    return redirect('medico_dashboard')


@login_required
@role_required('medico')
def medico_recusar_consulta(request, consulta_id):
    """Recusar pedido de consulta usando procedimento SQL"""
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM obter_medico_por_utilizador(%s)
            """, [request.user.id_utilizador])
            
            medico = cursor.fetchone()
            
        if not medico:
            messages.error(request, "Perfil de médico não encontrado.")
            return redirect('index')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM obter_consulta_completa(%s)
            """, [consulta_id])
            
            consulta_info = cursor.fetchone()
            
        if not consulta_info:
            messages.error(request, "Consulta não encontrada.")
            return redirect('medico_dashboard')
        
        if request.method == 'POST':
            motivo = request.POST.get('motivo', 'Recusado pelo médico')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    CALL recusar_consulta_medico(%s, %s, %s, NULL, NULL)
                """, [consulta_id, medico[0], motivo])

                result = cursor.fetchone()
                
            if result and result[1]:  # result[1] é 'sucesso'
                messages.success(request, result[0])  # result[0] é 'mensagem'
            elif result:
                messages.error(request, result[0])
            else:
                messages.error(request, "Erro ao processar recusa.")
                
            return redirect('medico_dashboard')
   
        consulta_data = {
            'id_consulta': consulta_info[0],
            'data_consulta': consulta_info[1],
            'hora_consulta': consulta_info[2],
            'estado': consulta_info[3],
            'motivo': consulta_info[4],
            'paciente_nome': consulta_info[7],
            'medico_nome': consulta_info[9],
        }
        
        return render(request, 'medico/recusar_consulta.html', {'consulta': consulta_data})
        
    except Exception as e:
        messages.error(request, f"Erro: {str(e)}")
        return redirect('medico_dashboard')


@login_required
@role_required('medico')
def medico_cancelar_consulta(request, consulta_id):
    """Médico cancela uma consulta usando procedure SQL"""
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM obter_medico_por_utilizador(%s)
            """, [request.user.id_utilizador])
            
            medico = cursor.fetchone()
            
        if not medico:
            messages.error(request, "Perfil de médico não encontrado.")
            return redirect('index')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM verificar_consulta_medico(%s, %s)
            """, [consulta_id, medico[0]])
            
            consulta_info = cursor.fetchone()
            
        if not consulta_info or not consulta_info[0]:
            messages.error(request, "Consulta não encontrada ou não pertence a este médico.")
            return redirect('medico_dashboard')
     
        motivo = request.POST.get("motivo", "Cancelada pelo médico")
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL cancelar_consulta(%s, %s, %s, %s)",
                [
                    consulta_id,
                    motivo,
                    request.user.id_utilizador,
                    'medico'
                ]
            )
        messages.success(request, "Consulta cancelada com sucesso.")
        
    except Exception as e:
        error_msg = str(e)
        if "24 horas" in error_msg:
            messages.error(request, "Não é possível cancelar consultas com menos de 24 horas de antecedência.")
        elif "já está cancelada" in error_msg:
            messages.info(request, "Esta consulta já está cancelada.")
        elif "não pode ser cancelada" in error_msg:
            messages.error(request, "Esta consulta não pode ser cancelada.")
        elif "não encontrada" in error_msg:
            messages.error(request, "Consulta não encontrada.")
        else:
            messages.error(request, f"Erro ao cancelar consulta: {error_msg}")
    
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
def agendar_consulta(request):
    from django.db import connection
    from datetime import datetime, timedelta
    
    if not request.user.is_authenticated:
        return redirect("login")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id_medico FROM obter_medico_por_utilizador_id(%s)", [request.user.id_utilizador])
            result = cursor.fetchone()
            if not result:
                messages.error(request, "Não foi possível encontrar o registo de médico.")
                return redirect("medico_dashboard")
            medico_id = result[0]
    except Exception as e:
        messages.error(request, f"Erro ao obter dados do médico: {str(e)}")
        return redirect("medico_dashboard")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        disp_id = request.POST.get("disponibilidade_id")
        hora_consulta_str = request.POST.get("hora_consulta")
        motivo = request.POST.get("motivo", "")
        
        if not paciente_id or not disp_id or not hora_consulta_str:
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect("medico_agenda")
        
        try:
            hora_consulta = datetime.strptime(hora_consulta_str, "%H:%M").time()

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT d.data, d.id_medico, d.id_unidade
                    FROM "DISPONIBILIDADE" d
                    WHERE d.id_disponibilidade = %s
                    AND d.id_medico = %s
                    AND d.status_slot IN ('disponivel', 'available')
                """, [disp_id, medico_id])
                disp_data = cursor.fetchone()
                
                if not disp_data:
                    messages.error(request, "Disponibilidade não encontrada ou não pertence a este médico.")
                    return redirect("medico_agenda")
                
                data_consulta = disp_data[0]

            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL marcar_consulta(%s, %s, %s, %s, %s)",
                        [paciente_id, medico_id, data_consulta, hora_consulta, motivo or "Consulta agendada pelo médico"]
                    )
                messages.success(request, "Consulta marcada com sucesso!")
                return redirect("medico_agenda")
                
            except Exception as e:
                messages.error(request, f"Erro ao marcar consulta: {str(e)}")
                return redirect("medico_agenda")
            
        except Exception as e:
            messages.error(request, f"Erro ao processar dados: {str(e)}")
            return redirect("medico_agenda")
        
    unidade_id = request.GET.get("unidade")
    data_q = request.GET.get("data")
    
    pacientes = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_pacientes_ativos()")
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                pacientes.append(dict(zip(columns, row)))
        logger.info(f"✓ Pacientes obtidos com sucesso: {len(pacientes)} encontrados")
        if pacientes:
            logger.info(f"  Primeiro paciente: {pacientes[0]}")
    except Exception as e:
        logger.error(f"✗ Erro ao obter pacientes: {str(e)}")
        messages.error(request, f"Erro ao carregar pacientes: {str(e)}")
    
    unidades = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_unidades_saude()")
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                unidades.append(dict(zip(columns, row)))
    except Exception as e:
        logger.error(f"✗ Erro ao obter unidades: {str(e)}")
        messages.error(request, f"Erro ao carregar unidades: {str(e)}")

    disponibilidades = []
    
    def gerar_slots(disponibilidade_row, disp_id):
        slots = []
        hora_inicio = disponibilidade_row[2]
        hora_fim = disponibilidade_row[3]
        duracao = disponibilidade_row[4]
        
        if not hora_inicio or not hora_fim or not duracao:
            return slots
        
        hora_atual = hora_inicio
        with connection.cursor() as cursor_slots:
            while hora_atual < hora_fim:
                hora_atual_dt = datetime.combine(datetime.today(), hora_atual)
                hora_fim_slot = (hora_atual_dt + timedelta(minutes=duracao)).time()
                
                if hora_fim_slot > hora_fim:
                    break
                
                try:
                    cursor_slots.execute("SELECT verificar_slot_disponivel(%s, %s)", [disp_id, hora_atual])
                    disponivel = cursor_slots.fetchone()[0]
                except:
                    disponivel = True
                
                slots.append({
                    'time': hora_atual.strftime("%H:%M"),
                    'available': disponivel
                })
                
                hora_atual = hora_fim_slot
        
        return slots
    
    # Filtrar disponibilidades 
    try:
        query_params = [medico_id]
        query_conditions = ["d.id_medico = %s", "d.status_slot IN ('disponivel', 'available')", "d.data >= CURRENT_DATE"]
        
        if unidade_id:
            query_conditions.append("d.id_unidade = %s")
            query_params.append(unidade_id)
        
        if data_q:
            query_conditions.append("d.data = %s")
            query_params.append(data_q)
        
        with connection.cursor() as cursor:
            query = """
                SELECT d.id_disponibilidade, d.data, d.hora_inicio, d.hora_fim,
                       d.duracao_slot, d.status_slot, un.nome_unidade
                FROM "DISPONIBILIDADE" d
                JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
                WHERE """ + " AND ".join(query_conditions) + """
                ORDER BY d.data, d.hora_inicio
                LIMIT 50
            """
            cursor.execute(query, query_params)
            
            for row in cursor.fetchall():
                disp_id = row[0]
                slots = gerar_slots(row, disp_id)
                
                disponibilidades.append({
                    'id_disponibilidade': disp_id,
                    'data': row[1],
                    'hora_inicio': row[2],
                    'hora_fim': row[3],
                    'duracao_slot': row[4],
                    'status_slot': row[5],
                    'unidade_nome': row[6] if row[6] else "Não especificada",
                    'slots': slots
                })
    except Exception as e:
        logger.error(f"✗ Erro ao obter disponibilidades: {str(e)}")
        messages.error(request, f"Erro ao carregar disponibilidades: {str(e)}")

    context = {
        "pacientes": pacientes,
        "unidades": unidades,
        "disponibilidades": disponibilidades,
        "selected": {
            "unidade": unidade_id,
            "data": data_q,
        },
    }

    return render(request, "medico/agendar_consulta.html", context)


@login_required
@role_required('medico')
def medico_verificar_disponibilidade(request):
    """AJAX endpoint to verify if disponibilidade exists for given time"""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT verificar_utilizador_eh_medico(%s)", [request.user.id_utilizador])
            eh_medico = cursor.fetchone()[0]
            
            if not eh_medico:
                return JsonResponse({'error': 'Médico not found'}, status=404)
            
            cursor.execute("SELECT id_medico FROM obter_medico_por_utilizador_id(%s)", [request.user.id_utilizador])
            result = cursor.fetchone()
            if not result:
                return JsonResponse({'error': 'Médico not found'}, status=404)
            
            medico_id = result[0]
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    data = request.POST.get('data')
    hora_inicio = request.POST.get('hora_inicio')
    hora_fim = request.POST.get('hora_fim')
    
    if not data or not hora_inicio or not hora_fim:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT validar_horario_disponibilidade(%s, %s, %s, %s)
            """, [data_obj, hora_inicio_obj, hora_fim_obj, medico_id])
            disponibilidade_exists = cursor.fetchone()[0]
        
        return JsonResponse({'exists': disponibilidade_exists})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)