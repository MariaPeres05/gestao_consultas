# core/email_utils.py

import threading
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Consulta

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
        consulta = Consulta.objects.select_related(
            'paciente', 'medico', 'medico__especialidade', 'medico__unidade_saude'
        ).get(id=consulta_id)
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/confirmacao_consulta.html', {
            'consulta': consulta,
        })
        
        subject = 'Consulta Confirmada - MediPulse'
        recipient_list = [consulta.paciente.email]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de email de confirmação iniciada para consulta {consulta_id}")
        
    except Consulta.DoesNotExist:
        logger.error(f"Consulta {consulta_id} não encontrada")
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
        consulta = Consulta.objects.select_related(
            'paciente', 'medico', 'medico__especialidade', 'medico__unidade_saude'
        ).get(id=consulta_id)
        
        # Determinar quem cancelou
        if hasattr(consulta, 'cancelado_por') and consulta.cancelado_por:
            if consulta.cancelado_por == consulta.paciente:
                motivo_texto = "por si"
            elif consulta.cancelado_por == consulta.medico:
                motivo_texto = "pelo médico"
            else:
                motivo_texto = "pelo sistema"
        else:
            motivo_texto = "pelo sistema"
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/cancelamento_consulta.html', {
            'consulta': consulta,
            'motivo_texto': motivo_texto,
        })
        
        subject = 'Consulta Cancelada - MediPulse'
        recipient_list = [consulta.paciente.email]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de email de cancelamento iniciada para consulta {consulta_id}")
        
    except Consulta.DoesNotExist:
        logger.error(f"Consulta {consulta_id} não encontrada")
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
        consulta = Consulta.objects.select_related(
            'paciente', 'medico', 'medico__especialidade', 'medico__unidade_saude'
        ).get(id=consulta_id)
        
        # Renderizar o template HTML
        html_message = render_to_string('emails/lembrete_consulta.html', {
            'consulta': consulta,
            'tempo_restante': tempo_restante,
        })
        
        subject = f'Lembrete: Consulta {tempo_restante} - MediPulse'
        recipient_list = [consulta.paciente.email]
        
        # Enviar email em thread separada (non-blocking)
        thread = threading.Thread(
            target=_send_email_thread,
            args=(subject, html_message, recipient_list)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Thread de lembrete iniciada para consulta {consulta_id}")
        
    except Consulta.DoesNotExist:
        logger.error(f"Consulta {consulta_id} não encontrada")
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
    
    consultas = Consulta.objects.filter(
        estado='confirmada',
        data__gte=inicio_janela.date(),
        data__lte=fim_janela.date(),
    ).select_related('paciente', 'medico', 'medico__especialidade', 'medico__unidade_saude')
    
    emails_enviados = 0
    
    for consulta in consultas:
        # Combinar data e hora para comparação precisa
        data_hora_consulta = timezone.make_aware(
            timezone.datetime.combine(consulta.data, consulta.hora_inicio)
        )
        
        # Verificar se está na janela de 24h
        if inicio_janela <= data_hora_consulta <= fim_janela:
            try:
                enviar_lembrete(consulta.id, 'amanhã')
                emails_enviados += 1
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete 24h para consulta {consulta.id}: {str(e)}")
    
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
    
    consultas = Consulta.objects.filter(
        estado='confirmada',
        data=agora.date(),
    ).select_related('paciente', 'medico', 'medico__especialidade', 'medico__unidade_saude')
    
    emails_enviados = 0
    
    for consulta in consultas:
        # Combinar data e hora para comparação precisa
        data_hora_consulta = timezone.make_aware(
            timezone.datetime.combine(consulta.data, consulta.hora_inicio)
        )
        
        # Verificar se está na janela de 2h
        if inicio_janela <= data_hora_consulta <= fim_janela:
            try:
                enviar_lembrete(consulta.id, 'daqui a 2 horas')
                emails_enviados += 1
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete 2h para consulta {consulta.id}: {str(e)}")
    
    logger.info(f"Tarefa enviar_lembretes_2h concluída. {emails_enviados} emails enviados.")
    return f"{emails_enviados} lembretes de 2h enviados"
