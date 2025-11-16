import pytest
from django.db import connection

@pytest.mark.django_db
def test_sp_gerar_fatura():
    with connection.cursor() as cur:
        # Criar horário e consulta
        cur.execute("""
            INSERT INTO "HORARIOS" ("ID_HORARIO","HORA_INICIO","HORA_FIM","TIPO","DIAS_SEMANA","DATA_INICIO","DATA_FIM","DURACAO")
            VALUES (4, '12:00', '12:30', 'Consulta', 'Friday', CURRENT_DATE, CURRENT_DATE, 30);
        """)
        cur.execute("""
            INSERT INTO "CONSULTAS" ("ID_CONSULTAS","ID_HORARIO","INICIO","FIM","ESTADO","MOTIVO")
            VALUES (4, 4, NOW(), NOW() + INTERVAL '30 minutes', 'concluida', 'Pós-operação');
        """)

        # Chamar procedure
        cur.execute("""CALL public."SP_GERAR_FATURA"(4, 75.00::numeric, 'Cartão'::text);""")
        


        # Verificar se fatura foi criada
        cur.execute('SELECT COUNT(*) FROM "FATURAS" WHERE "ID_CONSULTAS" = 4;')
        count = cur.fetchone()[0]
        assert count == 1
