import pytest
from django.db import connection

@pytest.mark.django_db
def test_view_v_faturas_publico():
    with connection.cursor() as cur:
        # Criar consulta para associar
        cur.execute("""
            INSERT INTO "HORARIOS" ("ID_HORARIO","HORA_INICIO","HORA_FIM","TIPO","DIAS_SEMANA","DATA_INICIO","DATA_FIM","DURACAO")
            VALUES (10, '15:00', '15:30', 'Consulta', 'Friday', CURRENT_DATE, CURRENT_DATE, 30);
        """)
        cur.execute("""
            INSERT INTO "CONSULTAS" ("ID_CONSULTAS","ID_HORARIO","INICIO","FIM","ESTADO","MOTIVO")
            VALUES (10, 10, NOW(), NOW() + INTERVAL '30 minutes', 'concluida', 'Rotina');
        """)

        # Criar fatura 
        cur.execute("""
            INSERT INTO "FATURAS" ("ID_FATURA","ID_CONSULTAS","VALOR","METODO_PAGAMENTO","ESTADO","DATA_PAGAMENTO")
            VALUES (10, 10, 120.00, 'Multibanco', 'Pago', CURRENT_DATE);
        """)

        cur.execute('SELECT * FROM public."V_FATURAS_PUBLICO" WHERE "ID_FATURA" = 10;')
        row = cur.fetchone()
        assert row is not None
        assert float(row[2]) == 120.00
