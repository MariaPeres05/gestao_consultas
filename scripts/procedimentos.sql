-- Procedimento para marcar consulta com todas as validações
CREATE OR REPLACE PROCEDURE marcar_consulta(
    p_id_paciente INTEGER,
    p_id_medico INTEGER,
    p_data_consulta DATE,
    p_hora_consulta TIME,
    p_motivo VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_disponibilidade INTEGER;
    v_hora_fim TIME;
    v_duracao_slot INTEGER;
    v_consultas_count INTEGER;
    v_total_slots INTEGER;
    v_slot_time TIME;
    v_contador INTEGER := 0;
BEGIN
    -- 1. Verificar se paciente existe e está ativo
    IF NOT EXISTS (
        SELECT 1 FROM "PACIENTES" p
        JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
        WHERE p.id_paciente = p_id_paciente
        AND u.ativo = TRUE
    ) THEN
        RAISE EXCEPTION 'Paciente não encontrado ou inativo';
    END IF;
    
    -- 2. Verificar se médico existe e está ativo
    IF NOT EXISTS (
        SELECT 1 FROM "MEDICOS" m
        JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
        WHERE m.id_medico = p_id_medico
        AND u.ativo = TRUE
    ) THEN
        RAISE EXCEPTION 'Médico não encontrado ou inativo';
    END IF;
    
    -- 3. Verificar se já existe consulta no mesmo horário
    IF EXISTS (
        SELECT 1 FROM "CONSULTAS" 
        WHERE id_medico = p_id_medico
        AND data_consulta = p_data_consulta
        AND hora_consulta = p_hora_consulta
        AND estado NOT IN ('cancelada')
    ) THEN
        RAISE EXCEPTION 'Já existe uma consulta agendada neste horário';
    END IF;
    
    -- 4. Encontrar disponibilidade correspondente
    SELECT d.id_disponibilidade, d.hora_fim, d.duracao_slot
    INTO v_id_disponibilidade, v_hora_fim, v_duracao_slot
    FROM "DISPONIBILIDADE" d
    WHERE d.id_medico = p_id_medico
    AND d.data = p_data_consulta
    AND d.hora_inicio <= p_hora_consulta
    AND d.hora_fim > p_hora_consulta
    AND d.status_slot IN ('disponivel', 'available')
    FOR UPDATE SKIP LOCKED
    LIMIT 1;
    
    IF v_id_disponibilidade IS NULL THEN
        RAISE EXCEPTION 'Não há disponibilidade para este horário';
    END IF;
    
    -- 5. Criar consulta
    INSERT INTO "CONSULTAS" (
        id_paciente, id_medico, id_disponibilidade,
        data_consulta, hora_consulta, estado,
        motivo, medico_aceitou, paciente_aceitou,
        criado_em
    ) VALUES (
        p_id_paciente, p_id_medico, v_id_disponibilidade,
        p_data_consulta, p_hora_consulta, 'agendada',
        p_motivo, FALSE, FALSE,
        CURRENT_TIMESTAMP
    );
    
    -- 6. Verificar se disponibilidade está completa
    -- Calcular total de slots possíveis
    v_total_slots := EXTRACT(EPOCH FROM (v_hora_fim - (
        SELECT hora_inicio FROM "DISPONIBILIDADE" 
        WHERE id_disponibilidade = v_id_disponibilidade
    ))) / 60 / v_duracao_slot;
    
    -- Contar consultas agendadas nesta disponibilidade
    SELECT COUNT(*) INTO v_consultas_count
    FROM "CONSULTAS"
    WHERE id_disponibilidade = v_id_disponibilidade
    AND estado NOT IN ('cancelada');
    
    -- Marcar como booked se todos slots estiverem ocupados
    IF v_consultas_count >= v_total_slots THEN
        UPDATE "DISPONIBILIDADE"
        SET status_slot = 'booked'
        WHERE id_disponibilidade = v_id_disponibilidade;
    END IF;
    
    COMMIT;
END;
$$;

-- 1. Ver os dados que existem
SELECT * FROM "MEDICOS" LIMIT 5;
SELECT * FROM "PACIENTES" LIMIT 5;
SELECT * FROM "DISPONIBILIDADE" WHERE status_slot = 'disponivel' LIMIT 5;

-- 2. Executar o procedure 
CALL marcar_consulta(
    p_id_paciente := 1,          
    p_id_medico := 1,             
    p_data_consulta := '2026-01-27',
    p_hora_consulta := '18:05',
    p_motivo := 'Teste de marcação'
);

-- Procedimento para confirmar consulta (aceitação)
CREATE OR REPLACE PROCEDURE confirmar_consulta(
    p_id_consulta INTEGER,
    p_tipo_confirmacao VARCHAR(10) -- 'medico' ou 'paciente'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_medico_aceitou BOOLEAN;
    v_paciente_aceitou BOOLEAN;
    v_estado VARCHAR(50);
BEGIN
    -- Bloquear consulta para atualização
    SELECT medico_aceitou, paciente_aceitou, estado
    INTO v_medico_aceitou, v_paciente_aceitou, v_estado
    FROM "CONSULTAS"
    WHERE id_consulta = p_id_consulta
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consulta não encontrada';
    END IF;
    
    IF v_estado != 'agendada' THEN
        RAISE EXCEPTION 'Esta consulta não pode ser confirmada';
    END IF;
    
    -- Atualizar aceitação conforme tipo
    IF p_tipo_confirmacao = 'medico' THEN
        UPDATE "CONSULTAS"
        SET medico_aceitou = TRUE
        WHERE id_consulta = p_id_consulta;
    ELSIF p_tipo_confirmacao = 'paciente' THEN
        UPDATE "CONSULTAS"
        SET paciente_aceitou = TRUE
        WHERE id_consulta = p_id_consulta;
    END IF;
    
    -- Verificar se ambos aceitaram para confirmar consulta
    IF (p_tipo_confirmacao = 'medico' AND v_paciente_aceitou = TRUE) OR
       (p_tipo_confirmacao = 'paciente' AND v_medico_aceitou = TRUE) THEN
       
        UPDATE "CONSULTAS"
        SET estado = 'confirmada',
            modificado_em = CURRENT_TIMESTAMP
        WHERE id_consulta = p_id_consulta;
    END IF;
    
    COMMIT;
END;
$$;

-- Criar consulta
INSERT INTO "CONSULTAS" (
    id_paciente,
    id_medico,
    data_consulta,
    hora_consulta,
    estado,
    medico_aceitou,
    paciente_aceitou,
    paciente_presente,      
    motivo,
    criado_em,
    criado_por
) VALUES (
    1,                        -- id_paciente
    1,                        -- id_medico
    '2026-02-10',             -- data_consulta
    '10:00:00',               -- hora_consulta
    'agendada',               -- estado
    FALSE,                     -- medico_aceitou
    FALSE,                     -- paciente_aceitou
    FALSE,                    -- paciente_presente (default: false)
    'Consulta criada pelo administrador',
    CURRENT_TIMESTAMP,        -- criado_em
    7                         -- criado_por
);

-- Ver todas as consultas "agendadas" disponíveis para teste
SELECT 
    id_consulta,
    data_consulta,
    hora_consulta,
    estado,
    medico_aceitou,
    paciente_aceitou,
    motivo
FROM "CONSULTAS" 
WHERE estado = 'agendada'
ORDER BY id_consulta DESC
LIMIT 10;

-- 1. Médico aceita a consulta
CALL confirmar_consulta(10, 'medico');

-- 2. Verificar o resultado
SELECT 
    id_consulta,
    estado,
    medico_aceitou,
    paciente_aceitou,
    modificado_em
FROM "CONSULTAS" 
WHERE id_consulta = 10;

-- 1. Paciente aceita a consulta
CALL confirmar_consulta(10, 'paciente');

-- 2. Verificar resultado
SELECT 
    id_consulta,
    estado,
    medico_aceitou,
    paciente_aceitou,
    modificado_em
FROM "CONSULTAS" 
WHERE id_consulta = 10;

-- Procedimento para criar fatura automaticamente após consulta realizada
CREATE OR REPLACE PROCEDURE criar_fatura_automatica(
    p_id_consulta INTEGER,
    p_valor DECIMAL(10,2) DEFAULT NULL,
    p_metodo_pagamento VARCHAR(50) DEFAULT 'pendente'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_estado_consulta VARCHAR(50);
    v_valor_fatura DECIMAL(10,2);
    v_especialidade_nome VARCHAR(255);
    v_fatura_exists BOOLEAN;
BEGIN
    -- Verificar estado da consulta
    SELECT c.estado, e.nome_especialidade
    INTO v_estado_consulta, v_especialidade_nome
    FROM "CONSULTAS" c
    LEFT JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE c.id_consulta = p_id_consulta;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consulta não encontrada';
    END IF;
    
    IF v_estado_consulta != 'realizada' THEN
        RAISE EXCEPTION 'Apenas consultas realizadas podem ter faturas';
    END IF;
    
    -- Verificar se já existe fatura
    SELECT EXISTS(
        SELECT 1 FROM "FATURAS" 
        WHERE id_consulta = p_id_consulta
    ) INTO v_fatura_exists;
    
    IF v_fatura_exists THEN
        RAISE EXCEPTION 'Já existe uma fatura para esta consulta';
    END IF;
    
    -- Definir valor padrão se não fornecido
    IF p_valor IS NULL THEN
        -- Valor baseado na especialidade (exemplo)
        CASE v_especialidade_nome
            WHEN 'Clínica Geral' THEN v_valor_fatura := 50.00;
            WHEN 'Cardiologia' THEN v_valor_fatura := 80.00;
            WHEN 'Dermatologia' THEN v_valor_fatura := 70.00;
            WHEN 'Ortopedia' THEN v_valor_fatura := 90.00;
            WHEN 'Pediatria' THEN v_valor_fatura := 60.00;
            ELSE v_valor_fatura := 55.00;
        END CASE;
    ELSE
        v_valor_fatura := p_valor;
    END IF;
    
    -- Criar fatura
    INSERT INTO "FATURAS" (
        id_consulta, valor, metodo_pagamento,
        estado, data_pagamento
    ) VALUES (
        p_id_consulta, v_valor_fatura, p_metodo_pagamento,
        'pendente', NULL
    );
    
    COMMIT;
END;
$$;

-- Criar consulta
INSERT INTO "CONSULTAS" (
    id_paciente, id_medico, data_consulta, hora_consulta,
    estado, motivo, paciente_presente, medico_aceitou, paciente_aceitou
) VALUES (
    1, 1, CURRENT_DATE, '12:00:00',
    'realizada', 'Consulta teste para fatura', TRUE, TRUE, TRUE
) RETURNING id_consulta;

CALL criar_fatura_automatica(14);

SELECT 
    f.id_fatura,
    f.valor,
    f.estado,
    f.metodo_pagamento,
    f.data_pagamento,
    c.id_consulta,
    c.estado as estado_consulta,
    e.nome_especialidade
FROM "FATURAS" f
JOIN "CONSULTAS" c ON f.id_consulta = c.id_consulta
LEFT JOIN "MEDICOS" m ON c.id_medico = m.id_medico
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
WHERE f.id_consulta = 14;