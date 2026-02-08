# core/email_utils.py

import threading
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db import connection

logger = logging.getLogger(__name__)


def _send_email_thread(subject, html_message, recipient_list):
    """
    Internal function to send email in a separate thread.
    This prevents blocking the main request/response cycle.
    """
    try:
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email '{subject}' enviado com sucesso para {recipient_list}")
    except Exception as e:
        logger.error(f"Erro ao enviar email '{subject}': {str(e)}")


def enviar_email_confirmacao(consulta_id):
    """
    Envia email de confirmação da consulta para o paciente de forma assíncrona.
    Usa threading para não bloquear a resposta HTTP.
    
    Args:
        consulta_id: ID da consulta confirmada
    """
    try:
        # Obter consulta usando SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_consulta_com_relacoes(%s)", [consulta_id])
            consulta_row = cursor.fetchone()
        
        if not consulta_row:
            logger.error(f"Consulta {consulta_id} não encontrada")
            return
        
        consulta_dict = {
            'id_consulta': consulta_row[0],
            'data_consulta': consulta_row[3],
            'hora_consulta': consulta_row[4],
            'motivo': consulta_row[6],
            'paciente_nome': consulta_row[7],
            'paciente_email': consulta_row[8],
            'medico_nome': consulta_row[10],
            'especialidade_nome': consulta_row[11],
            'nome_unidade': consulta_row[12],
        }
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/confirmacao_consulta.html', {
            'consulta': consulta_dict,
        })
        
        subject = 'Consulta Confirmada - MediPulse'
        recipient_list = [consulta_dict['paciente_email']]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de email de confirmação iniciada para consulta {consulta_id}")
        
    except Exception as e:
        logger.error(f"Erro ao preparar email de confirmação para consulta {consulta_id}: {str(e)}")


def enviar_email_cancelamento(consulta_id, motivo_cancelamento=''):
    """
    Envia email de cancelamento da consulta para o paciente de forma assíncrona.
    
    Args:
        consulta_id: ID da consulta cancelada
        motivo_cancelamento: Motivo do cancelamento (opcional)
    """
    try:
        # Obter consulta usando SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_consulta_com_relacoes(%s)", [consulta_id])
            consulta_row = cursor.fetchone()
        
        if not consulta_row:
            logger.error(f"Consulta {consulta_id} não encontrada")
            return
        
        consulta_dict = {
            'id_consulta': consulta_row[0],
            'data_consulta': consulta_row[3],
            'hora_consulta': consulta_row[4],
            'motivo': consulta_row[6],
            'paciente_nome': consulta_row[7],
            'paciente_email': consulta_row[8],
            'medico_nome': consulta_row[10],
            'especialidade_nome': consulta_row[11],
            'nome_unidade': consulta_row[12],
        }
        
        # Default motivo texto
        motivo_texto = motivo_cancelamento if motivo_cancelamento else "pelo sistema"
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/cancelamento_consulta.html', {
            'consulta': consulta_dict,
            'motivo_texto': motivo_texto,
        })
        
        subject = 'Consulta Cancelada - MediPulse'
        recipient_list = [consulta_dict['paciente_email']]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de email de cancelamento iniciada para consulta {consulta_id}")
        
    except Exception as e:
        logger.error(f"Erro ao preparar email de cancelamento para consulta {consulta_id}: {str(e)}")


def enviar_lembrete(consulta_id, tempo_restante):
    """
    Envia lembrete para uma consulta específica.
    
    Args:
        consulta_id: ID da consulta
        tempo_restante: Texto descrevendo quanto tempo falta ("amanhã", "daqui a 2 horas")
    """
    try:
        # Obter consulta usando SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM obter_consulta_com_relacoes(%s)", [consulta_id])
            consulta_row = cursor.fetchone()
        
        if not consulta_row:
            logger.error(f"Consulta {consulta_id} não encontrada")
            return
        
        consulta_dict = {
            'id_consulta': consulta_row[0],
            'data_consulta': consulta_row[3],
            'hora_consulta': consulta_row[4],
            'motivo': consulta_row[6],
            'paciente_nome': consulta_row[7],
            'paciente_email': consulta_row[8],
            'medico_nome': consulta_row[10],
            'especialidade_nome': consulta_row[11],
            'nome_unidade': consulta_row[12],
        }
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/lembrete_consulta.html', {
            'consulta': consulta_dict,
            'tempo_restante': tempo_restante,
        })
        
        subject = f'Lembrete: Consulta {tempo_restante} - MediPulse'
        recipient_list = [consulta_dict['paciente_email']]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de lembrete iniciada para consulta {consulta_id}")
        
    except Exception as e:
        logger.error(f"Erro ao preparar lembrete para consulta {consulta_id}: {str(e)}")


# ============================================================================
# SCHEDULED TASKS - Called by APScheduler
# ============================================================================

def enviar_lembretes_24h():
    """
    Tarefa agendada: Envia lembretes para consultas que acontecerão em 24 horas.
    Chamada automaticamente pelo APScheduler diariamente às 9h.
    """
    logger.info("Iniciando envio de lembretes de 24h...")
    agora = timezone.now()
    
    # Buscar consultas confirmadas para daqui a 24h (±1h de margem)
    inicio_janela = agora + timedelta(hours=23)
    fim_janela = agora + timedelta(hours=25)
    
    # Use SQL to get consultas
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_consulta, data_consulta, hora_consulta
            FROM "CONSULTAS"
            WHERE estado = 'confirmada'
            AND data_consulta BETWEEN %s AND %s
        """, [inicio_janela.date(), fim_janela.date()])
        
        consultas = cursor.fetchall()
    
    emails_enviados = 0
    
    for consulta_row in consultas:
        consulta_id = consulta_row[0]
        data_consulta = consulta_row[1]
        hora_consulta = consulta_row[2]
        
        # Combinar data e hora para comparação precisa
        data_hora_consulta = timezone.make_aware(
            timezone.datetime.combine(data_consulta, hora_consulta)
        )
        
        # Verificar se está na janela de 24h
        if inicio_janela <= data_hora_consulta <= fim_janela:
            try:
                enviar_lembrete(consulta_id, 'amanhã')
                emails_enviados += 1
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete 24h para consulta {consulta_id}: {str(e)}")
    
    logger.info(f"Tarefa enviar_lembretes_24h concluída. {emails_enviados} emails enviados.")
    return f"{emails_enviados} lembretes de 24h enviados"


def enviar_lembretes_2h():
    """
    Tarefa agendada: Envia lembretes para consultas que acontecerão em 2 horas.
    Chamada automaticamente pelo APScheduler a cada 30 minutos.
    """
    logger.info("Iniciando envio de lembretes de 2h...")
    agora = timezone.now()
    
    # Buscar consultas confirmadas para daqui a 2h (±30min de margem)
    inicio_janela = agora + timedelta(hours=1.5)
    fim_janela = agora + timedelta(hours=2.5)
    
    # Use SQL to get consultas
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_consulta, data_consulta, hora_consulta
            FROM "CONSULTAS"
            WHERE estado = 'confirmada'
            AND data_consulta = %s
        """, [agora.date()])
        
        consultas = cursor.fetchall()
    
    emails_enviados = 0
    
    for consulta_row in consultas:
        consulta_id = consulta_row[0]
        data_consulta = consulta_row[1]
        hora_consulta = consulta_row[2]
        
        # Combinar data e hora para comparação precisa
        data_hora_consulta = timezone.make_aware(
            timezone.datetime.combine(data_consulta, hora_consulta)
        )
        
        # Verificar se está na janela de 2h
        if inicio_janela <= data_hora_consulta <= fim_janela:
            try:
                enviar_lembrete(consulta_id, 'daqui a 2 horas')
                emails_enviados += 1
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete 2h para consulta {consulta_id}: {str(e)}")
    
    logger.info(f"Tarefa enviar_lembretes_2h concluída. {emails_enviados} emails enviados.")
    return f"{emails_enviados} lembretes de 2h enviados"


def enviar_email_verificacao(user, request):
    """
    Envia email de verificação para o utilizador com link de ativação.
    Gera um token único e envia email em thread separada.
    
    Args:
        user: Objeto Utilizador que precisa verificar o email
        request: HttpRequest object para construir URL absoluto
    """
    import secrets
    from django.urls import reverse
    
    try:
        # Gerar token único de verificação
        verification_token = secrets.token_urlsafe(32)
        user.verification_token = verification_token
        user.save(update_fields=['verification_token'])
        
        # Construir URL de verificação
        verification_path = reverse('verify_email', kwargs={'token': verification_token})
        verification_url = request.build_absolute_uri(verification_path)
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        
        subject = 'Verificar Email - MediPulse'
        recipient_list = [user.email]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Email de verificação enviado para {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de verificação para {user.email}: {str(e)}")
        return False


def reenviar_email_verificacao(user, request):
    """
    Reenvia email de verificação para utilizadores que ainda não verificaram.
    
    Args:
        user: Objeto Utilizador
        request: HttpRequest object
    """
    if user.email_verified:
        logger.warning(f"Tentativa de reenviar verificação para email já verificado: {user.email}")
        return False
    
    return enviar_email_verificacao(user, request)
