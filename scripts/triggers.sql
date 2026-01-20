--Trigger para auto-preenchimento de data_regito
CREATE OR REPLACE FUNCTION set_utilizador_data_registo()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.data_registo IS NULL THEN
        NEW.data_registo = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_utilizador_data_registo
    BEFORE INSERT ON "core_utilizador"
    FOR EACH ROW
    EXECUTE FUNCTION set_utilizador_data_registo();

INSERT INTO "core_utilizador" (
    password,
    nome,
    email,
    role,
    data_registo,  -- ← Vamos deixar NULL para testar
    ativo,
    is_superuser,
    email_verified
) VALUES (
    'pbkdf2_sha256$600000$abc123$hashedpassword123=',  -- Hash fictício
    'João Teste',
    'joao.teste@email.com',
    'paciente',
    NULL,  
    TRUE,
    FALSE,
    FALSE
) RETURNING id_utilizador, nome, email, data_registo;

DELETE FROM "core_utilizador" WHERE email = 'joao.teste@email.com';

-- Trigger para validar horário da consulta com a disponibilidade
CREATE OR REPLACE FUNCTION validate_consulta_horario()
RETURNS TRIGGER AS $$
DECLARE
    v_hora_inicio TIME;
    v_hora_fim TIME;
    v_data DATE;
    v_duracao INTEGER;
BEGIN
    -- Se tem disponibilidade associada, validar contra ela
    IF NEW.id_disponibilidade IS NOT NULL THEN
        SELECT hora_inicio, hora_fim, data, duracao_slot 
        INTO v_hora_inicio, v_hora_fim, v_data, v_duracao
        FROM "DISPONIBILIDADE"
        WHERE id_disponibilidade = NEW.id_disponibilidade;
        
        -- Validar que a data da consulta corresponde à da disponibilidade
        IF NEW.data_consulta != v_data THEN
            RAISE EXCEPTION 'Data da consulta não corresponde à data da disponibilidade';
        END IF;
        
        -- Validar que a hora está dentro do intervalo da disponibilidade
        IF NEW.hora_consulta < v_hora_inicio OR NEW.hora_consulta >= v_hora_fim THEN
            RAISE EXCEPTION 'Hora da consulta fora do intervalo de disponibilidade';
        END IF;
        
        -- Verificar se a hora da consulta respeita a duração dos slots
        IF v_duracao > 0 THEN
            DECLARE
                minutes_since_start INTEGER;
            BEGIN
                minutes_since_start := EXTRACT(EPOCH FROM (NEW.hora_consulta - v_hora_inicio)) / 60;
                IF minutes_since_start % v_duracao != 0 THEN
                    RAISE EXCEPTION 'Hora da consulta não respeita a duração dos slots (% minutos)', v_duracao;
                END IF;
            END;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_consulta_horario
    BEFORE INSERT OR UPDATE ON "CONSULTAS"
    FOR EACH ROW
    EXECUTE FUNCTION validate_consulta_horario();

-- Criar disponibilidade para testes
INSERT INTO "DISPONIBILIDADE" (
    id_medico, id_unidade, data, hora_inicio, hora_fim, duracao_slot, status_slot
) VALUES (
    (SELECT id_medico FROM "MEDICOS" LIMIT 1),
    (SELECT id_unidade FROM "UNIDADE_DE_SAUDE" LIMIT 1),
    '2024-12-25',
    '09:00:00',
    '17:00:00',
    30,  -- Slots de 30 minutos
    'available'
) RETURNING id_disponibilidade;

--Teste falha
INSERT INTO "CONSULTAS" (
    id_paciente, id_medico, id_disponibilidade, data_consulta, hora_consulta,
    estado, medico_aceitou, paciente_aceitou, criado_por, paciente_presente
) VALUES (
    (SELECT id_paciente FROM "PACIENTES" LIMIT 1),
    (SELECT id_medico FROM "MEDICOS" LIMIT 1),
    15,                    -- ID da disponibilidade
    '2024-12-26',         -- Data DIFERENTE (disponibilidade é 2024-12-25)
    '10:00:00',
    'agendada', FALSE, FALSE,
    (SELECT id_utilizador FROM "core_utilizador" LIMIT 1),
	FALSE
);

--Teste funcional
INSERT INTO "CONSULTAS" (
    id_paciente, id_medico, id_disponibilidade, data_consulta, hora_consulta,
    estado, medico_aceitou, paciente_aceitou, criado_por, paciente_presente
) VALUES (
    (SELECT id_paciente FROM "PACIENTES" LIMIT 1),
    (SELECT id_medico FROM "MEDICOS" LIMIT 1),
    15,                    -- ID da disponibilidade
    '2024-12-25',         
    '10:30:00',          
    'agendada', FALSE, FALSE,
    (SELECT id_utilizador FROM "core_utilizador" LIMIT 1),
	FALSE
) RETURNING id_consulta;

DELETE FROM "CONSULTAS" WHERE id_consulta = 26;
DELETE FROM "DISPONIBILIDADE" WHERE id_disponibilidade = 15;