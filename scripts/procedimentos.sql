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
        paciente_presente, criado_em
    ) VALUES (
        p_id_paciente, p_id_medico, v_id_disponibilidade,
        p_data_consulta, p_hora_consulta, 'agendada',
        p_motivo, FALSE, FALSE,
        TRUE, CURRENT_TIMESTAMP
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


CREATE OR REPLACE PROCEDURE cancelar_consulta(
    p_id_consulta INTEGER,
    p_motivo VARCHAR(255) DEFAULT NULL,
    p_id_utilizador INTEGER DEFAULT NULL,
    p_role_utilizador VARCHAR(20) DEFAULT NULL  -- 'medico' ou 'paciente'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_disponibilidade INTEGER;
    v_estado_atual VARCHAR(50);
    v_data_consulta DATE;
    v_hora_consulta TIME;
    v_antes_24h BOOLEAN;
BEGIN
    -- Bloquear e obter dados da consulta
    SELECT estado, id_disponibilidade, data_consulta, hora_consulta 
    INTO v_estado_atual, v_id_disponibilidade, v_data_consulta, v_hora_consulta
    FROM "CONSULTAS" 
    WHERE id_consulta = p_id_consulta
    FOR UPDATE;
    
    IF v_estado_atual = 'cancelada' THEN
        RAISE EXCEPTION 'Consulta já está cancelada';
    END IF;
    
    -- Verificar se está em estado cancelável
    IF v_estado_atual NOT IN ('agendada', 'confirmada', 'marcada') THEN
        RAISE EXCEPTION 'Esta consulta não pode ser cancelada';
    END IF;
    
    -- Verificar regra das 24 horas para pacientes
    IF p_role_utilizador = 'paciente' THEN
        -- Combinar data e hora
        v_antes_24h := (v_data_consulta || ' ' || v_hora_consulta)::timestamp 
                      - INTERVAL '24 hours' > NOW();
        
        IF NOT v_antes_24h THEN
            RAISE EXCEPTION 'Não é possível cancelar consultas com menos de 24 horas de antecedência';
        END IF;
    END IF;
    
    -- Verificar regra das 24 horas para médicos
    IF p_role_utilizador = 'medico' THEN
        -- Combinar data e hora
        v_antes_24h := (v_data_consulta || ' ' || v_hora_consulta)::timestamp 
                      - INTERVAL '24 hours' > NOW();
        
        IF NOT v_antes_24h THEN
            RAISE EXCEPTION 'Não é possível cancelar consultas com menos de 24 horas de antecedência';
        END IF;
    END IF;
    
    -- Determinar o motivo baseado no tipo de utilizador
    DECLARE
        v_motivo_final VARCHAR(255);
    BEGIN
        IF p_role_utilizador = 'paciente' THEN
            v_motivo_final := COALESCE(p_motivo, 'Cancelada pelo paciente');
        ELSIF p_role_utilizador = 'medico' THEN
            v_motivo_final := COALESCE(p_motivo, 'Cancelada pelo médico');
        ELSE
            v_motivo_final := COALESCE(p_motivo, 'Cancelada');
        END IF;
        
        -- Atualizar consulta
        UPDATE "CONSULTAS" 
        SET estado = 'cancelada',
            motivo = v_motivo_final,
            modificado_por = p_id_utilizador,
            modificado_em = NOW()
        WHERE id_consulta = p_id_consulta;
    END;
    
    -- Libertar disponibilidade se existir
    IF v_id_disponibilidade IS NOT NULL THEN
        UPDATE "DISPONIBILIDADE" 
        SET status_slot = 'available'
        WHERE id_disponibilidade = v_id_disponibilidade;
    END IF;
    
    -- Se houver fatura associada, marcá-la como cancelada
    UPDATE "FATURAS"
    SET estado = 'cancelada'
    WHERE id_consulta = p_id_consulta AND estado = 'pendente';
    
    COMMIT;
END;
$$;


-- Procedure para criar receita
CREATE OR REPLACE PROCEDURE criar_receita(
    p_id_consulta INTEGER,
    p_medicamento VARCHAR(255),
    p_dosagem VARCHAR(255),
    p_instrucoes VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_estado_consulta VARCHAR(50);
BEGIN
    -- Verificar se consulta está realizada
    SELECT estado INTO v_estado_consulta
    FROM "CONSULTAS"
    WHERE id_consulta = p_id_consulta;
    
    IF v_estado_consulta != 'realizada' THEN
        RAISE EXCEPTION 'Só pode criar receitas para consultas realizadas';
    END IF;
    
    -- Inserir receita
    INSERT INTO "RECEITAS" (
        id_consulta,
        medicamento,
        dosagem,
        instrucoes,
        data_prescricao
    ) VALUES (
        p_id_consulta,
        p_medicamento,
        p_dosagem,
        p_instrucoes,
        CURRENT_DATE
    );
    
    COMMIT;
END;
$$;

CREATE OR REPLACE PROCEDURE atualizar_perfil_utilizador(
    p_id_utilizador INTEGER,
    p_nome VARCHAR(255),
    p_telefone VARCHAR(20),
    p_nova_senha VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_nova_senha IS NOT NULL AND LENGTH(p_nova_senha) >= 6 THEN
        -- Atualizar com nova senha
        UPDATE "core_utilizador"
        SET nome = p_nome,
            telefone = p_telefone,
            password = crypt(p_nova_senha, gen_salt('bf', 8)),
            modificado_em = NOW()
        WHERE id_utilizador = p_id_utilizador;
    ELSE
        -- Atualizar sem mudar senha
        UPDATE "core_utilizador"
        SET nome = p_nome,
            telefone = p_telefone,
            modificado_em = NOW()
        WHERE id_utilizador = p_id_utilizador;
    END IF;
    
    COMMIT;
END;
$$;

CREATE OR REPLACE PROCEDURE atualizar_paciente(
    p_id_paciente INTEGER,
    p_data_nasc DATE,
    p_genero VARCHAR(50),
    p_morada VARCHAR(255),
    p_alergias VARCHAR(255),
    p_observacoes VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "PACIENTES"
    SET data_nasc = p_data_nasc,
        genero = p_genero,
        morada = p_morada,
        alergias = p_alergias,
        observacoes = p_observacoes
    WHERE id_paciente = p_id_paciente;
    
    COMMIT;
END;
$$;

CREATE OR REPLACE PROCEDURE verificar_email_utilizador(p_token VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "core_utilizador"
    SET email_verified = TRUE,
        verification_token = NULL,
        modificado_em = NOW()
    WHERE verification_token = p_token;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Token inválido ou expirado';
    END IF;
    
    COMMIT;
END;
$$;

-- Procedimento para reagendar consulta
CREATE OR REPLACE PROCEDURE reagendar_consulta(
    p_id_consulta INTEGER,
    p_nova_disponibilidade_id INTEGER,
    p_id_utilizador INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_disponibilidade_antiga INTEGER;
    v_estado_atual VARCHAR(50);
    v_novo_data DATE;
    v_novo_hora TIME;
    v_novo_id_medico INTEGER;
BEGIN
    -- Bloquear registos
    SELECT estado, id_disponibilidade INTO v_estado_atual, v_id_disponibilidade_antiga
    FROM "CONSULTAS" 
    WHERE id_consulta = p_id_consulta
    FOR UPDATE;
    
    -- Verificar se pode ser reagendada
    IF v_estado_atual NOT IN ('agendada', 'marcada') THEN
        RAISE EXCEPTION 'Esta consulta não pode ser reagendada';
    END IF;
    
    -- Obter dados da nova disponibilidade
    SELECT data, hora_inicio, id_medico 
    INTO v_novo_data, v_novo_hora, v_novo_id_medico
    FROM "DISPONIBILIDADE" 
    WHERE id_disponibilidade = p_nova_disponibilidade_id
    AND status_slot = 'available'
    FOR UPDATE;
    
    IF v_novo_data IS NULL THEN
        RAISE EXCEPTION 'Disponibilidade não encontrada ou já ocupada';
    END IF;
    
    -- Libertar disponibilidade antiga
    IF v_id_disponibilidade_antiga IS NOT NULL THEN
        UPDATE "DISPONIBILIDADE" 
        SET status_slot = 'available'
        WHERE id_disponibilidade = v_id_disponibilidade_antiga;
    END IF;
    
    -- Atualizar consulta
    UPDATE "CONSULTAS" 
    SET id_disponibilidade = p_nova_disponibilidade_id,
        id_medico = v_novo_medico_id,
        data_consulta = v_novo_data,
        hora_consulta = v_novo_hora,
        estado = 'agendada',
        medico_aceitou = FALSE,
        paciente_aceitou = FALSE,
        modificado_por = p_id_utilizador,
        modificado_em = NOW()
    WHERE id_consulta = p_id_consulta;
    
    -- Marcar nova disponibilidade como ocupada
    UPDATE "DISPONIBILIDADE" 
    SET status_slot = 'booked'
    WHERE id_disponibilidade = p_nova_disponibilidade_id;
    
    COMMIT;
END;
$$;

-- Procedure para criar utilizador e paciente
CREATE OR REPLACE PROCEDURE criar_utilizador_paciente(
    p_nome VARCHAR(255),
    p_email VARCHAR(255),
    p_telefone VARCHAR(20),
    p_senha VARCHAR(255),
    p_data_nasc DATE DEFAULT NULL,
    p_genero VARCHAR(50) DEFAULT 'Não especificado',
    p_morada VARCHAR(255) DEFAULT '',
    p_alergias VARCHAR(255) DEFAULT '',
    p_observacoes VARCHAR(255) DEFAULT ''
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_utilizador INTEGER;
    v_n_utente VARCHAR(20);
BEGIN
    -- Gerar número de utente único
    SELECT LPAD(FLOOR(RANDOM() * 1000000000)::TEXT, 10, '0') INTO v_n_utente
    FROM generate_series(1, 100)
    WHERE NOT EXISTS (
        SELECT 1 FROM "core_utilizador" WHERE n_utente = v_n_utente
    )
    LIMIT 1;
    
    IF v_n_utente IS NULL THEN
        -- Se falhou, usar sequencial
        v_n_utente := 'U' || LPAD(NEXTVAL('utilizador_seq')::TEXT, 9, '0');
    END IF;
    
    -- Inserir utilizador
    INSERT INTO "core_utilizador" (
        nome, email, telefone, n_utente, password, 
        role, data_registo, ativo, email_verified,
        verification_token
    ) VALUES (
        p_nome, 
        p_email, 
        p_telefone,
        v_n_utente,
        crypt(p_senha, gen_salt('bf', 8)),
        'paciente',
        NOW(),
        TRUE,
        FALSE,
        md5(random()::text || p_email || random()::text)
    ) RETURNING id_utilizador INTO v_id_utilizador;
    
    -- Inserir paciente
    INSERT INTO "PACIENTES" (
        id_utilizador, data_nasc, genero, morada, alergias, observacoes
    ) VALUES (
        v_id_utilizador,
        COALESCE(p_data_nasc, '2000-01-01'::date),
        p_genero,
        p_morada,
        p_alergias,
        p_observacoes
    );
    
    COMMIT;
END;
$$;

-- Procedure para realizar check-in do paciente
CREATE OR REPLACE PROCEDURE realizar_checkin(
    p_id_consulta INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "CONSULTAS"
    SET paciente_presente = TRUE,
        hora_checkin = NOW(),
        modificado_em = NOW()
    WHERE id_consulta = p_id_consulta;
    
    COMMIT;
END;
$$;

CREATE OR REPLACE PROCEDURE obter_dashboard_medico(
    p_id_medico INTEGER,
    OUT consultas_hoje JSON,
    OUT consultas_semana INTEGER,
    OUT consultas_mes INTEGER,
    OUT pedidos_pendentes INTEGER,
    OUT estatisticas JSON
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
    v_inicio_semana DATE := DATE_TRUNC('week', CURRENT_DATE)::DATE;
    v_fim_semana DATE := (DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days')::DATE;
    v_inicio_mes DATE := DATE_TRUNC('month', CURRENT_DATE)::DATE;
BEGIN
    -- Consultas de hoje
    SELECT json_agg(json_build_object(
        'id_consulta', c.id_consulta,
        'data_consulta', c.data_consulta,
        'hora_consulta', c.hora_consulta,
        'estado', c.estado,
        'motivo', c.motivo,
        'paciente_nome', c.paciente_nome,
        'can_cancel_24h', c.pode_cancelar_24h
    )) INTO consultas_hoje
    FROM vw_consultas_completas c
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta = v_hoje
        AND c.estado NOT IN ('cancelada')
    ORDER BY c.hora_consulta;
    
    -- Consultas da semana
    SELECT COUNT(*) INTO consultas_semana
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta BETWEEN v_inicio_semana AND v_fim_semana
        AND c.estado = 'confirmada';
    
    -- Consultas do mês
    SELECT COUNT(*) INTO consultas_mes
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta >= v_inicio_mes
        AND c.estado = 'confirmada';
    
    -- Pedidos pendentes
    SELECT COUNT(*) INTO pedidos_pendentes
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.estado = 'agendada'
        AND (c.medico_aceitou = FALSE OR c.paciente_aceitou = FALSE);
    
    -- Estatísticas do médico
    SELECT json_build_object(
        'consultas_realizadas', COALESCE(vm.consultas_realizadas, 0),
        'consultas_agendadas', COALESCE(vm.consultas_agendadas, 0),
        'consultas_confirmadas', COALESCE(vm.consultas_confirmadas, 0),
        'consultas_canceladas', COALESCE(vm.consultas_canceladas, 0),
        'disponibilidades_disponiveis', COALESCE(vm.disponibilidades_disponiveis, 0)
    ) INTO estatisticas
    FROM vw_estatisticas_medicos vm
    WHERE vm.id_medico = p_id_medico;
    
    -- Se não encontrou estatísticas, retornar zeros
    IF estatisticas IS NULL THEN
        estatisticas := json_build_object(
            'consultas_realizadas', 0,
            'consultas_agendadas', 0,
            'consultas_confirmadas', 0,
            'consultas_canceladas', 0,
            'disponibilidades_disponiveis', 0
        );
    END IF;
    
    -- Garantir que consultas_hoje não seja nulo
    IF consultas_hoje IS NULL THEN
        consultas_hoje := '[]'::JSON;
    END IF;
END;
$$;

-- Procedimento para agendar consulta com validações
CREATE OR REPLACE PROCEDURE agendar_consulta_medico(
    p_id_medico INTEGER,
    p_id_paciente INTEGER,
    p_data_consulta DATE,
    p_hora_inicio TIME,
    p_hora_fim TIME,
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN,
    p_motivo VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_disponibilidade_id INTEGER;
    v_disponibilidade_hora_fim TIME;
    v_duracao_slot INTEGER;
    v_consultas_count INTEGER;
    v_total_slots INTEGER;
    v_paciente_nome VARCHAR(255);
BEGIN
    sucesso := FALSE;
    
    -- 1. Verificar se paciente existe e está ativo
    IF NOT EXISTS (
        SELECT 1 FROM "PACIENTES" p
        JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
        WHERE p.id_paciente = p_id_paciente
        AND u.ativo = TRUE
    ) THEN
        mensagem := 'Paciente não encontrado ou inativo';
        RETURN;
    END IF;
    
    -- 2. Verificar se já existe consulta no mesmo horário
    IF EXISTS (
        SELECT 1 FROM "CONSULTAS" 
        WHERE id_medico = p_id_medico
        AND data_consulta = p_data_consulta
        AND hora_consulta = p_hora_inicio
        AND estado NOT IN ('cancelada')
    ) THEN
        mensagem := 'Já existe uma consulta agendada neste horário';
        RETURN;
    END IF;
    
    -- 3. Validar que fim é depois de início
    IF p_hora_fim <= p_hora_inicio THEN
        mensagem := 'O fim da consulta deve ser posterior ao início';
        RETURN;
    END IF;
    
    -- 4. Encontrar disponibilidade correspondente
    SELECT d.id_disponibilidade, d.hora_fim, d.duracao_slot
    INTO v_disponibilidade_id, v_disponibilidade_hora_fim, v_duracao_slot
    FROM "DISPONIBILIDADE" d
    WHERE d.id_medico = p_id_medico
    AND d.data = p_data_consulta
    AND d.hora_inicio <= p_hora_inicio
    AND d.hora_fim >= p_hora_fim
    AND d.status_slot IN ('disponivel', 'available')
    FOR UPDATE SKIP LOCKED
    LIMIT 1;
    
    IF v_disponibilidade_id IS NULL THEN
        mensagem := 'Não há disponibilidade para este horário';
        RETURN;
    END IF;
    
    -- 5. Obter nome do paciente
    SELECT u.nome INTO v_paciente_nome
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    WHERE p.id_paciente = p_id_paciente;
    
    -- 6. Criar consulta
    INSERT INTO "CONSULTAS" (
        id_paciente, id_medico, id_disponibilidade,
        data_consulta, hora_consulta, estado,
        motivo, medico_aceitou, paciente_aceitou,
        paciente_presente, criado_em, criado_por
    ) VALUES (
        p_id_paciente, p_id_medico, v_disponibilidade_id,
        p_data_consulta, p_hora_inicio, 'agendada',
        p_motivo, TRUE, FALSE,
        FALSE, CURRENT_TIMESTAMP, (SELECT id_utilizador FROM "MEDICOS" WHERE id_medico = p_id_medico)
    );
    
    -- 7. Verificar se disponibilidade está completa
    v_total_slots := EXTRACT(EPOCH FROM (v_disponibilidade_hora_fim - (
        SELECT hora_inicio FROM "DISPONIBILIDADE" 
        WHERE id_disponibilidade = v_disponibilidade_id
    ))) / 60 / v_duracao_slot;
    
    SELECT COUNT(*) INTO v_consultas_count
    FROM "CONSULTAS"
    WHERE id_disponibilidade = v_disponibilidade_id
    AND estado NOT IN ('cancelada');
    
    -- Marcar como booked se todos slots estiverem ocupados
    IF v_consultas_count >= v_total_slots THEN
        UPDATE "DISPONIBILIDADE"
        SET status_slot = 'booked'
        WHERE id_disponibilidade = v_disponibilidade_id;
    END IF;
    
    mensagem := 'Consulta agendada com sucesso para ' || v_paciente_nome || '. Aguarda aceitação do paciente.';
    sucesso := TRUE;
    
    COMMIT;
END;
$$;

-- Procedimento para criar disponibilidade e agendar consulta
CREATE OR REPLACE PROCEDURE criar_disponibilidade_e_agendar(
    p_id_medico INTEGER,
    p_id_paciente INTEGER,
    p_data_consulta DATE,
    p_hora_inicio TIME,
    p_hora_fim TIME,
    p_unidade_id INTEGER,
    p_disp_hora_inicio TIME,
    p_disp_hora_fim TIME,
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN,
    p_motivo VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_disponibilidade_id INTEGER;
    v_paciente_nome VARCHAR(255);
    v_unidade_nome VARCHAR(255);
BEGIN
    sucesso := FALSE;
    
    -- 1. Validar que a disponibilidade cobre a consulta
    IF p_disp_hora_inicio > p_hora_inicio OR p_disp_hora_fim < p_hora_fim THEN
        mensagem := 'A disponibilidade deve cobrir todo o período da consulta';
        RETURN;
    END IF;
    
    -- 2. Verificar se unidade existe
    IF NOT EXISTS (SELECT 1 FROM "UNIDADE_DE_SAUDE" WHERE id_unidade = p_unidade_id) THEN
        mensagem := 'Unidade de saúde não encontrada';
        RETURN;
    END IF;
    
    -- 3. Verificar se já existe consulta no mesmo horário
    IF EXISTS (
        SELECT 1 FROM "CONSULTAS" 
        WHERE id_medico = p_id_medico
        AND data_consulta = p_data_consulta
        AND hora_consulta = p_hora_inicio
        AND estado NOT IN ('cancelada')
    ) THEN
        mensagem := 'Já existe uma consulta agendada neste horário';
        RETURN;
    END IF;
    
    -- 4. Obter nomes
    SELECT u.nome INTO v_paciente_nome
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    WHERE p.id_paciente = p_id_paciente;
    
    SELECT nome_unidade INTO v_unidade_nome
    FROM "UNIDADE_DE_SAUDE"
    WHERE id_unidade = p_unidade_id;
    
    -- 5. Criar disponibilidade
    INSERT INTO "DISPONIBILIDADE" (
        id_medico, id_unidade, data,
        hora_inicio, hora_fim, duracao_slot,
        status_slot
    ) VALUES (
        p_id_medico, p_unidade_id, p_data_consulta,
        p_disp_hora_inicio, p_disp_hora_fim, 30,
        'disponivel'
    )
    RETURNING id_disponibilidade INTO v_disponibilidade_id;
    
    -- 6. Criar consulta
    INSERT INTO "CONSULTAS" (
        id_paciente, id_medico, id_disponibilidade,
        data_consulta, hora_consulta, estado,
        motivo, medico_aceitou, paciente_aceitou,
        paciente_presente, criado_em, criado_por
    ) VALUES (
        p_id_paciente, p_id_medico, v_disponibilidade_id,
        p_data_consulta, p_hora_inicio, 'agendada',
        p_motivo, TRUE, FALSE,
        FALSE, CURRENT_TIMESTAMP, (SELECT id_utilizador FROM "MEDICOS" WHERE id_medico = p_id_medico)
    );
    
    mensagem := 'Disponibilidade criada e consulta agendada para ' || v_paciente_nome || 
                ' na unidade ' || v_unidade_nome || '. Aguarda aceitação do paciente.';
    sucesso := TRUE;
    
    COMMIT;
END;
$$;

-- Procedimento para definir disponibilidade
CREATE OR REPLACE PROCEDURE definir_disponibilidade(
    p_id_medico INTEGER,
    p_data DATE,
    p_hora_inicio TIME,
    p_hora_fim TIME,
    p_unidade_id INTEGER,
    p_disponivel BOOLEAN,
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR(20);
    v_duracao INTEGER := 30;
    v_unidade_nome VARCHAR(255);
    v_criado BOOLEAN;
BEGIN
    sucesso := FALSE;
    
    -- Verificar se unidade existe
    SELECT nome_unidade INTO v_unidade_nome
    FROM "UNIDADE_DE_SAUDE"
    WHERE id_unidade = p_unidade_id;
    
    IF v_unidade_nome IS NULL THEN
        mensagem := 'Unidade de saúde não encontrada';
        RETURN;
    END IF;
    
    -- Definir status
    IF p_disponivel THEN
        v_status := 'disponivel';
    ELSE
        v_status := 'indisponivel';
    END IF;
    
    -- Inserir ou atualizar disponibilidade
    INSERT INTO "DISPONIBILIDADE" (
        id_medico, id_unidade, data,
        hora_inicio, hora_fim, duracao_slot,
        status_slot
    ) VALUES (
        p_id_medico, p_unidade_id, p_data,
        p_hora_inicio, p_hora_fim, v_duracao,
        v_status
    )
    ON CONFLICT (id_medico, data, hora_inicio, id_unidade) 
    DO UPDATE SET 
        hora_fim = EXCLUDED.hora_fim,
        status_slot = EXCLUDED.status_slot,
        duracao_slot = EXCLUDED.duracao_slot
    RETURNING (xmax = 0) INTO v_criado;
    
    IF v_criado THEN
        mensagem := 'Disponibilidade criada com sucesso!';
    ELSE
        mensagem := 'Disponibilidade atualizada com sucesso!';
    END IF;
    
    sucesso := TRUE;
    COMMIT;
END;
$$;

-- Procedimento para definir férias
CREATE OR REPLACE PROCEDURE definir_ferias_medico(
    p_id_medico INTEGER,
    p_data_inicio DATE,
    p_data_fim DATE,
    p_motivo VARCHAR(255),
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_unidade_id INTEGER;
    v_dias_criados INTEGER := 0;
    v_current_date DATE;
BEGIN
    sucesso := FALSE;
    
    -- Obter primeira unidade disponível
    SELECT id_unidade INTO v_unidade_id
    FROM "UNIDADE_DE_SAUDE"
    LIMIT 1;
    
    IF v_unidade_id IS NULL THEN
        mensagem := 'Nenhuma unidade de saúde disponível. Contacte o administrador.';
        RETURN;
    END IF;
    
    -- Validar datas
    IF p_data_fim < p_data_inicio THEN
        mensagem := 'Data de fim deve ser posterior à data de início';
        RETURN;
    END IF;
    
    v_current_date := p_data_inicio;
    
    -- Criar disponibilidades para cada dia
    WHILE v_current_date <= p_data_fim LOOP
        INSERT INTO "DISPONIBILIDADE" (
            id_medico, id_unidade, data,
            hora_inicio, hora_fim, duracao_slot,
            status_slot
        ) VALUES (
            p_id_medico, v_unidade_id, v_current_date,
            '00:00', '23:59', 30,
            'ferias'
        )
        ON CONFLICT (id_medico, data, hora_inicio, id_unidade) 
        DO UPDATE SET 
            status_slot = 'ferias',
            hora_fim = '23:59';
        
        v_dias_criados := v_dias_criados + 1;
        v_current_date := v_current_date + 1;
    END LOOP;
    
    mensagem := 'Período de ' || v_dias_criados || ' dia(s) marcado como indisponível!';
    sucesso := TRUE;
    
    COMMIT;
END;
$$;

-- Procedimento para excluir disponibilidade
CREATE OR REPLACE PROCEDURE excluir_disponibilidade(
    p_disponibilidade_id INTEGER,
    p_id_medico INTEGER,
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_pode_excluir BOOLEAN;
    v_mensagem_validacao VARCHAR(500);
BEGIN
    sucesso := FALSE;
    
    -- Verificar se pode excluir
    SELECT ve.pode_excluir, ve.mensagem
    INTO v_pode_excluir, v_mensagem_validacao
    FROM verificar_exclusao_disponibilidade(p_disponibilidade_id, p_id_medico) AS ve;
    
    IF NOT v_pode_excluir THEN
        mensagem := v_mensagem_validacao;
        RETURN;
    END IF;
    
    -- Excluir disponibilidade
    DELETE FROM "DISPONIBILIDADE" 
    WHERE id_disponibilidade = p_disponibilidade_id
    AND id_medico = p_id_medico;
    
    IF FOUND THEN
        mensagem := 'Disponibilidade excluída com sucesso!';
        sucesso := TRUE;
    ELSE
        mensagem := 'Erro ao excluir disponibilidade.';
        sucesso := FALSE;
    END IF;
    
    COMMIT;
END;
$$;

-- Procedimento para recusar consulta
CREATE OR REPLACE PROCEDURE recusar_consulta_medico(
    p_id_consulta INTEGER,
    p_id_medico INTEGER,
    p_motivo VARCHAR(255),
    OUT mensagem VARCHAR(500),
    OUT sucesso BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existe BOOLEAN;
    v_estado VARCHAR(50);
BEGIN
    sucesso := FALSE;
    
    -- Verificar se consulta existe e pertence ao médico
    SELECT EXISTS(
        SELECT 1 FROM "CONSULTAS" c
        WHERE c.id_consulta = p_id_consulta
        AND c.id_medico = p_id_medico
    ) INTO v_existe;
    
    IF NOT v_existe THEN
        mensagem := 'Consulta não encontrada ou não pertence a este médico.';
        RETURN;
    END IF;
    
    -- Verificar estado da consulta
    SELECT estado INTO v_estado
    FROM "CONSULTAS"
    WHERE id_consulta = p_id_consulta;
    
    IF v_estado = 'cancelada' THEN
        mensagem := 'Esta consulta já está cancelada.';
        RETURN;
    END IF;
    
    IF v_estado NOT IN ('agendada', 'marcada') THEN
        mensagem := 'Esta consulta não pode ser recusada.';
        RETURN;
    END IF;
    
    -- Atualizar consulta como recusada
    UPDATE "CONSULTAS"
    SET estado = 'cancelada',
        motivo = '[RECUSADA] ' || COALESCE(p_motivo, 'Recusada pelo médico'),
        medico_aceitou = FALSE,
        modificado_em = NOW()
    WHERE id_consulta = p_id_consulta;
    
    -- Libertar disponibilidade se existir
    UPDATE "DISPONIBILIDADE" 
    SET status_slot = 'available'
    WHERE id_disponibilidade = (
        SELECT id_disponibilidade 
        FROM "CONSULTAS" 
        WHERE id_consulta = p_id_consulta
    );
    
    mensagem := 'Consulta recusada com sucesso.';
    sucesso := TRUE;
    
    COMMIT;
END;
$$;