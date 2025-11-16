import pytest
from django.db import connection

@pytest.mark.django_db
def test_sp_marcar_consulta():
    with connection.cursor() as cur:
        # Inserir registo na tabela UTILIZADOR
        cur.execute("""
            INSERT INTO "UTILIZADOR" (
                "ID_UTILIZADOR", 
                "NOMEREGIAO", 
                "EMAIL",
                "TELEFONE", 
                "N_UTENTE", 
                "SENHA", 
                "ROLE", 
                "DATA_REGISTO", 
                "ATIVO", 
                "FOTO_PERFIL"
            ) VALUES (
                50,                         -- ID_UTILIZADOR
                'Maria Teste',              -- NOMEREGIAO
                'maria.teste@example.com',  -- EMAIL
                '912345678',                -- TELEFONE
                'UT123456',                 -- N_UTENTE
                'senha123',                 -- SENHA
                2,                          -- ROLE
                CURRENT_DATE,               -- DATA_REGISTO
                1,                          -- ATIVO
                NULL                        -- FOTO_PERFIL
            );
        """)

        # Criar horário
        cur.execute("""
            INSERT INTO "HORARIOS" (
                "ID_HORARIO", "HORA_INICIO", "HORA_FIM", "TIPO", 
                "DIAS_SEMANA", "DATA_INICIO", "DATA_FIM", "DURACAO"
            ) VALUES (
                5, '13:00', '13:30', 'Consulta', 
                'Friday', CURRENT_DATE, CURRENT_DATE + INTERVAL '10 days', '30'
            );
        """)

        # Inserir paciente
        cur.execute("""
            INSERT INTO "PACIENTES" (
                "ID_UTILIZADOR",
                "ID_PACIENTE",
                "NOMEREGIAO",
                "EMAIL",
                "TELEFONE",
                "N_UTENTE",
                "SENHA",
                "ROLE",
                "DATA_REGISTO",
                "ATIVO",
                "FOTO_PERFIL",
                "DATA_NASC",
                "GENERO",
                "MORADA",
                "ALERGIAS",
                "OBSERVACOES"
            ) VALUES (
                50,
                500,
                'Maria Teste',
                'maria.teste@example.com',
                '912345678',
                'UT123456',
                'senha123',
                1,
                CURRENT_DATE,
                1,
                NULL,
                DATE '1990-05-10',
                'Feminino',
                'Rua das Flores 123',
                'Nenhuma',
                'Paciente de teste'
            );
        """)

        # Verificar se o horário foi criado
        cur.execute('SELECT COUNT(*) FROM "HORARIOS" WHERE "ID_HORARIO" = 5;')
        horario_count = cur.fetchone()[0]
        print(f"Horários existentes com ID 5: {horario_count}")

        
        cur.execute("""
            SELECT public."f_marcar_consulta"(5, 50, 500, 'Dores de cabeça'::text);
        """)
        result = cur.fetchone()
        consulta_id = result[0]  
        print(f"ID da consulta retornado: {consulta_id}")

        # Verificar todas as consultas
        cur.execute('SELECT "ID_CONSULTAS", "ID_HORARIO", "ESTADO" FROM "CONSULTAS";')
        todas_consultas = cur.fetchall()
        print(f"Todas as consultas na tabela: {todas_consultas}")

        # Verificar se a consulta foi inserida usando o ID retornado
        cur.execute('SELECT COUNT(*) FROM "CONSULTAS" WHERE "ID_CONSULTAS" = %s;', [consulta_id])
        count = cur.fetchone()[0]
        
        #Verificar também por horário
        cur.execute('SELECT COUNT(*) FROM "CONSULTAS" WHERE "ID_HORARIO" = 5;')
        count_por_horario = cur.fetchone()[0]
        print(f"Consultas com ID_HORARIO = 5: {count_por_horario}")
        
        assert count == 1, f"Consulta não foi inserida. Count: {count}"
