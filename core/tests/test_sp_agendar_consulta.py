import pytest
from django.db import connection
from datetime import datetime, timedelta

@pytest.mark.django_db
def test_sp_agendar_consulta():
    with connection.cursor() as cur:
        # Inserir registo em HORARIOS (necessário para FK)
        cur.execute("""
            INSERT INTO "HORARIOS" 
            ("ID_HORARIO", "HORA_INICIO", "HORA_FIM", "TIPO", "DIAS_SEMANA", "DATA_INICIO", "DATA_FIM", "DURACAO")
            VALUES 
            (1, '09:00', '09:30', 'Consulta', 'Segunda,Terça,Quarta', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 30);
        """)

        # Chamar a stored procedure
        cur.execute("""
            SELECT public."SP_AGENDAR_CONSULTA"(%s, %s, %s, %s, %s)
        """, [
            1,  # p_id_consulta
            1,  # p_id_horario 
            datetime.now(),
            datetime.now() + timedelta(minutes=30),
            'Agendada'
        ])

     
        cur.execute('SELECT COUNT(*) FROM "CONSULTAS"')
        count = cur.fetchone()[0]
        assert count > 0, "A função SP_AGENDAR_CONSULTA não inseriu nenhum registo em CONSULTAS."




