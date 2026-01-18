from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    scheduler_started = False  # Flag to prevent multiple initializations

    def ready(self):
        """
        Inicializa o APScheduler quando o Django inicia.
        Configura as tarefas agendadas para envio de lembretes.
        """
        # Evitar inicializar scheduler múltiplas vezes
        if CoreConfig.scheduler_started:
            return
        
        # Só iniciar scheduler no processo principal
        # (Django recarrega o código em desenvolvimento)
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        CoreConfig.scheduler_started = True
        
        from apscheduler.schedulers.background import BackgroundScheduler
        from django.conf import settings
        import atexit
        
        try:
            from .email_utils import enviar_lembretes_24h, enviar_lembretes_2h
            
            # Criar scheduler
            scheduler = BackgroundScheduler(timezone='Europe/Lisbon')
            
            # Tarefa 1: Lembrete 24h - Diariamente às 9:00
            scheduler.add_job(
                enviar_lembretes_24h,
                'cron',
                hour=9,
                minute=0,
                id='lembrete_24h',
                replace_existing=True,
                name='Enviar lembretes de 24h'
            )
            logger.info("✓ Tarefa agendada: Lembretes 24h (diário às 9:00)")
            
            # Tarefa 2: Lembrete 2h - A cada 30 minutos
            scheduler.add_job(
                enviar_lembretes_2h,
                'interval',
                minutes=30,
                id='lembrete_2h',
                replace_existing=True,
                name='Enviar lembretes de 2h'
            )
            logger.info("✓ Tarefa agendada: Lembretes 2h (a cada 30 minutos)")
            
            # Iniciar scheduler
            scheduler.start()
            logger.info("🚀 APScheduler iniciado com sucesso!")
            
            # Garantir que o scheduler para quando Django fecha
            atexit.register(lambda: scheduler.shutdown())
            
        except Exception as e:
            logger.error(f"Erro ao inicializar APScheduler: {str(e)}")
