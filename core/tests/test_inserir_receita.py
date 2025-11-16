import pytest
from django.db import connection
from datetime import date, datetime, timedelta

@pytest.mark.django_db
def test_inserir_receita():
    with connection.cursor() as cur:
        #Criar horário
        cur.execute("""
            INSERT INTO "HORARIOS" 
            ("ID_HORARIO", "HORA_INICIO", "HORA_FIM", "TIPO", "DIAS_SEMANA", "DATA_INICIO", "DATA_FIM", "DURACAO")
            VALUES 
            (1, '10:00', '10:30', 'Consulta', 'Segunda,Terça,Quarta', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 30);
        """)

        # Criar consulta (precisa de existir antes da fatura)
        cur.execute("""
            INSERT INTO "CONSULTAS" 
            ("ID_CONSULTAS", "ID_HORARIO", "INICIO", "FIM", "ESTADO", "MOTIVO")
            VALUES 
            (1, 1, NOW(), NOW() + INTERVAL '30 minutes', 'Concluída', 'Rotina de check-up');
        """)

        # Criar fatura 
        cur.execute("""
            INSERT INTO "FATURAS" 
            ("ID_FATURA", "ID_CONSULTAS", "VALOR", "METODO_PAGAMENTO", "ESTADO", "DATA_PAGAMENTO")
            VALUES 
            (1, 1, 50.00, 'Dinheiro', 'Pago', CURRENT_DATE);
        """)

        #Chamar procedure inserir_receita
        cur.execute("""
            CALL public.inserir_receita(%s, %s, %s, %s, %s, %s)
        """, [
            1,      # ID_CONSULTAS
            1,      # ID_FATURA
            'Ibuprofeno',
            '200mg',
            'Tomar 1 comprimido de 8 em 8h',
            date.today()
        ])

        cur.execute('SELECT COUNT(*) FROM "RECEITAS"')
        count = cur.fetchone()[0]
        assert count > 0
