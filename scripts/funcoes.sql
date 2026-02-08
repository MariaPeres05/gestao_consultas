-- ============================================================================
-- FUNÇÕES DO SISTEMA
-- ============================================================================

-- Função para gerar número de utente único (10 dígitos)
CREATE OR REPLACE FUNCTION gerar_n_utente() 
RETURNS VARCHAR(10) AS $$
DECLARE
    novo_numero VARCHAR(10);
    tentativas INTEGER := 0;
BEGIN
    WHILE tentativas < 1000 LOOP
        -- Gerar número aleatório de 10 dígitos
        novo_numero := lpad(floor(random() * 10000000000)::bigint::text, 10, '0');
        
        -- Verificar se não existe
        IF NOT EXISTS (SELECT 1 FROM "core_utilizador" WHERE n_utente = novo_numero) THEN
            RETURN novo_numero;
        END IF;
        
        tentativas := tentativas + 1;
    END LOOP;
    
    -- Fallback: timestamp + random
    RETURN to_char(EXTRACT(EPOCH FROM now())::bigint, 'FM9999999999');
END;
$$ LANGUAGE plpgsql;

-- Função para validar se horário está dentro do período de disponibilidade
CREATE OR REPLACE FUNCTION validar_horario_disponibilidade(
    p_data DATE,
    p_hora_inicio TIME,
    p_hora_fim TIME,
    p_id_medico INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    disponibilidade_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM "DISPONIBILIDADE" d
        WHERE d.id_medico = p_id_medico
        AND d.data = p_data
        AND d.hora_inicio <= p_hora_inicio
        AND d.hora_fim >= p_hora_fim
        AND d.status_slot IN ('disponivel', 'available')
    ) INTO disponibilidade_exists;
    
    RETURN disponibilidade_exists;
END;
$$ LANGUAGE plpgsql;

-- Função para obter estatísticas do paciente
CREATE OR REPLACE FUNCTION obter_estatisticas_paciente(p_id_utilizador INTEGER)
RETURNS TABLE (
    consultas_confirmadas INTEGER,
    faturas_total INTEGER,
    proxima_consulta_date DATE,
    proxima_consulta_time TIME
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Consultas confirmadas
    SELECT COUNT(*) INTO consultas_confirmadas
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    WHERE p.id_utilizador = p_id_utilizador
    AND c.estado = 'confirmada'
    AND c.data_consulta >= CURRENT_DATE;
    
    -- Total de faturas
    SELECT COUNT(*) INTO faturas_total
    FROM "FATURAS" f
    JOIN "CONSULTAS" c ON f.id_consulta = c.id_consulta
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    WHERE p.id_utilizador = p_id_utilizador;
    
    -- Próxima consulta
    SELECT c.data_consulta, c.hora_consulta 
    INTO proxima_consulta_date, proxima_consulta_time
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    WHERE p.id_utilizador = p_id_utilizador
    AND c.estado = 'confirmada'
    AND (c.data_consulta > CURRENT_DATE OR 
         (c.data_consulta = CURRENT_DATE AND c.hora_consulta > CURRENT_TIME))
    ORDER BY c.data_consulta, c.hora_consulta
    LIMIT 1;
    
    RETURN NEXT;
END;
$$;

-- Função para obter paciente por utilizador
CREATE OR REPLACE FUNCTION obter_paciente_por_utilizador(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_paciente INTEGER,
    data_nasc DATE,
    genero VARCHAR(50),
    morada VARCHAR(255),
    alergias VARCHAR(255),
    observacoes VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id_paciente,
        p.data_nasc,
        p.genero,
        COALESCE(p.morada, ''),
        COALESCE(p.alergias, ''),
        COALESCE(p.observacoes, '')
    FROM "PACIENTES" p
    WHERE p.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para obter ID do paciente por ID do utilizador
CREATE OR REPLACE FUNCTION obter_paciente_por_utilizador_id(p_id_utilizador INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_paciente INTEGER;
BEGIN
    SELECT id_paciente INTO v_id_paciente
    FROM "PACIENTES"
    WHERE id_utilizador = p_id_utilizador
    LIMIT 1;
    
    RETURN v_id_paciente;
END;
$$;

-- Função para obter utilizador por email
CREATE OR REPLACE FUNCTION obter_utilizador_por_email(p_email VARCHAR)
RETURNS TABLE (
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    role VARCHAR(20),
    data_registo TIMESTAMP,
    ativo BOOLEAN,
    email_verified BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_utilizador,
        u.nome,
        u.email,
        u.telefone,
        u.n_utente,
        u.role,
        u.data_registo::timestamp,
        u.ativo,
        u.email_verified
    FROM "UTILIZADOR" u
    WHERE u.email = p_email
    LIMIT 1;
END;
$$;

-- Função para obter utilizador por token de verificação
CREATE OR REPLACE FUNCTION obter_utilizador_por_token(p_token VARCHAR)
RETURNS TABLE (
    id_utilizador INTEGER,
    email_verified BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_utilizador,
        u.email_verified
    FROM "UTILIZADOR" u
    WHERE u.verification_token = p_token
    LIMIT 1;
END;
$$;

-- Função para obter utilizador por ID
CREATE OR REPLACE FUNCTION obter_utilizador_por_id(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_utilizador INTEGER,
    email_verified BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_utilizador,
        u.email_verified
    FROM "core_utilizador" u
    WHERE u.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para listar utilizadores (admin) com filtro opcional por role
CREATE OR REPLACE FUNCTION listar_utilizadores_admin(p_role VARCHAR DEFAULT NULL)
RETURNS TABLE (
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    role VARCHAR(20),
    ativo BOOLEAN,
    data_registo TIMESTAMPTZ,
    role_display VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id_utilizador,
        u.nome,
        u.email,
        u.telefone,
        u.role,
        u.ativo,
        u.data_registo::timestamp,
        CASE u.role
            WHEN 'admin' THEN 'Administrador'
            WHEN 'medico' THEN 'Médico'
            WHEN 'enfermeiro' THEN 'Enfermeiro'
            WHEN 'paciente' THEN 'Paciente'
            ELSE u.role
        END AS role_display
    FROM "core_utilizador" u
    WHERE (p_role IS NULL OR p_role = '' OR u.role = p_role)
    ORDER BY u.data_registo DESC;
END;
$$;

-- Função para obter utilizador por ID (admin)
CREATE OR REPLACE FUNCTION obter_utilizador_admin_por_id(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    role VARCHAR(20),
    ativo BOOLEAN,
    data_registo TIMESTAMP,
    role_display VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id_utilizador,
        u.nome,
        u.email,
        u.telefone,
        u.role,
        u.ativo,
        u.data_registo::timestamp,
        CASE u.role
            WHEN 'admin' THEN 'Administrador'
            WHEN 'medico' THEN 'Médico'
            WHEN 'enfermeiro' THEN 'Enfermeiro'
            WHEN 'paciente' THEN 'Paciente'
            ELSE u.role
        END AS role_display
    FROM "core_utilizador" u
    WHERE u.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para verificar se email já existe (admin)
CREATE OR REPLACE FUNCTION verificar_email_utilizador_admin(
    p_email VARCHAR,
    p_excluir_id INTEGER DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM "core_utilizador"
        WHERE email = p_email
        AND (p_excluir_id IS NULL OR id_utilizador <> p_excluir_id)
    ) INTO v_exists;

    RETURN v_exists;
END;
$$;

-- Função para listar consultas (admin) com filtros
CREATE OR REPLACE FUNCTION listar_consultas_admin(
    p_estado VARCHAR DEFAULT NULL,
    p_data DATE DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        u_p.nome AS paciente_nome,
        u_m.nome AS medico_nome
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" u_m ON m.id_utilizador = u_m.id_utilizador
    WHERE (p_estado IS NULL OR p_estado = '' OR c.estado = p_estado)
      AND (p_data IS NULL OR c.data_consulta = p_data)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC
    LIMIT p_limite;
END;
$$;

-- Função para obter consulta por ID (admin)
CREATE OR REPLACE FUNCTION obter_consulta_admin_por_id(p_id_consulta INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.motivo,
        u_p.nome AS paciente_nome,
        u_m.nome AS medico_nome
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" u_m ON m.id_utilizador = u_m.id_utilizador
    WHERE c.id_consulta = p_id_consulta
    LIMIT 1;
END;
$$;

-- Função para listar disponibilidades (admin) com filtros
CREATE OR REPLACE FUNCTION listar_disponibilidades_admin(
    p_id_unidade INTEGER,
    p_data DATE,
    p_id_especialidade INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id_disponibilidade INTEGER,
    hora_inicio TIME,
    hora_fim TIME,
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id_disponibilidade,
        gs.slot_inicio::time AS hora_inicio,
        (gs.slot_inicio + (d.duracao_slot || ' minutes')::interval)::time AS hora_fim,
        u.nome AS medico_nome,
        COALESCE(e.nome_especialidade, 'Sem especialidade') AS especialidade_nome
    FROM "DISPONIBILIDADE" d
    JOIN "MEDICOS" m ON d.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    JOIN LATERAL generate_series(
        d.hora_inicio,
        d.hora_fim - (d.duracao_slot || ' minutes')::interval,
        (d.duracao_slot || ' minutes')::interval
    ) AS gs(slot_inicio) ON TRUE
    WHERE d.id_unidade = p_id_unidade
      AND d.data = p_data
      AND d.status_slot IN ('disponivel', 'available')
      AND (p_id_especialidade IS NULL OR m.id_especialidade = p_id_especialidade)
      AND NOT EXISTS (
          SELECT 1
          FROM "CONSULTAS" c
          WHERE c.id_disponibilidade = d.id_disponibilidade
            AND c.hora_consulta = gs.slot_inicio::time
            AND c.estado NOT IN ('cancelada')
      )
    ORDER BY gs.slot_inicio;
END;
$$;

-- Função para obter disponibilidade por ID (admin)
CREATE OR REPLACE FUNCTION obter_disponibilidade_admin_por_id(p_id_disponibilidade INTEGER)
RETURNS TABLE (
    id_disponibilidade INTEGER,
    id_medico INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id_disponibilidade,
        d.id_medico,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        u.nome AS medico_nome,
        COALESCE(e.nome_especialidade, 'Sem especialidade') AS especialidade_nome
    FROM "DISPONIBILIDADE" d
    JOIN "MEDICOS" m ON d.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE d.id_disponibilidade = p_id_disponibilidade
    LIMIT 1;
END;
$$;

-- Função para obter paciente por ID (admin)
CREATE OR REPLACE FUNCTION obter_paciente_admin_por_id(p_id_paciente INTEGER)
RETURNS TABLE (
    id_paciente INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT p.id_paciente, u.nome, u.email
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    WHERE p.id_paciente = p_id_paciente
    LIMIT 1;
END;
$$;

-- Função para listar faturas (admin) com filtro opcional por estado
CREATE OR REPLACE FUNCTION listar_faturas_admin(
    p_estado VARCHAR DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_fatura INTEGER,
    id_consulta INTEGER,
    paciente_nome VARCHAR(255),
    valor NUMERIC,
    metodo_pagamento VARCHAR(50),
    estado VARCHAR(50),
    data_pagamento DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id_fatura,
        f.id_consulta,
        f.paciente_nome,
        f.valor,
        f.metodo_pagamento,
        f.estado_fatura,
        f.data_pagamento
    FROM vw_faturas_completas f
    WHERE (p_estado IS NULL OR p_estado = '' OR f.estado_fatura = p_estado)
    ORDER BY f.id_fatura DESC
    LIMIT p_limite;
END;
$$;

-- Função para obter fatura por ID (admin)
CREATE OR REPLACE FUNCTION obter_fatura_admin_por_id(p_id_fatura INTEGER)
RETURNS TABLE (
    id_fatura INTEGER,
    id_consulta INTEGER,
    paciente_nome VARCHAR(255),
    valor NUMERIC,
    metodo_pagamento VARCHAR(50),
    estado VARCHAR(50),
    data_pagamento DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id_fatura,
        f.id_consulta,
        f.paciente_nome,
        f.valor,
        f.metodo_pagamento,
        f.estado_fatura,
        f.data_pagamento
    FROM vw_faturas_completas f
    WHERE f.id_fatura = p_id_fatura
    LIMIT 1;
END;
$$;

-- Função para obter consulta para fatura (admin)
CREATE OR REPLACE FUNCTION obter_consulta_admin_para_fatura(p_id_consulta INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    paciente_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.paciente_nome
    FROM vw_consultas_completas c
    WHERE c.id_consulta = p_id_consulta
    LIMIT 1;
END;
$$;

-- Função para verificar se consulta já tem fatura (admin)
CREATE OR REPLACE FUNCTION verificar_fatura_por_consulta(p_id_consulta INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM "FATURAS" f WHERE f.id_consulta = p_id_consulta
    ) INTO v_exists;
    RETURN v_exists;
END;
$$;

-- Função para estatísticas de faturas (admin)
CREATE OR REPLACE FUNCTION obter_estatisticas_faturas_admin()
RETURNS TABLE (
    total_faturado NUMERIC,
    total_pendente NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(CASE WHEN estado = 'paga' THEN valor END), 0) AS total_faturado,
        COALESCE(SUM(CASE WHEN estado = 'pendente' THEN valor END), 0) AS total_pendente
    FROM "FATURAS";
END;
$$;

-- Funções de relatórios (admin)
CREATE OR REPLACE FUNCTION relatorio_receitas_periodo(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL
)
RETURNS TABLE (
    total NUMERIC,
    count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(valor), 0) AS total,
        COUNT(*)::BIGINT AS count
    FROM "FATURAS"
    WHERE estado = 'paga'
      AND (p_data_inicio IS NULL OR data_pagamento >= p_data_inicio)
      AND (p_data_fim IS NULL OR data_pagamento <= p_data_fim);
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_por_estado(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    estado VARCHAR(50),
    total BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT c.estado, COUNT(*)::BIGINT
    FROM vw_consultas_completas c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id)
    GROUP BY c.estado
    ORDER BY COUNT(*) DESC;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_por_medico(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL,
    p_limite INTEGER DEFAULT 10
)
RETURNS TABLE (
    medico_nome VARCHAR(255),
    total BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT c.medico_nome, COUNT(*)::BIGINT
    FROM vw_consultas_completas c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id)
    GROUP BY c.medico_nome
    ORDER BY COUNT(*) DESC
    LIMIT p_limite;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_por_especialidade(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    especialidade_nome VARCHAR(255),
    total BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT COALESCE(c.nome_especialidade, 'Sem especialidade') AS especialidade_nome,
           COUNT(*)::BIGINT
    FROM vw_consultas_completas c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id)
    GROUP BY COALESCE(c.nome_especialidade, 'Sem especialidade')
    ORDER BY COUNT(*) DESC;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_faturas_listar(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id_fatura INTEGER,
    data_pagamento DATE,
    valor NUMERIC,
    estado VARCHAR(50),
    metodo_pagamento VARCHAR(50),
    id_consulta INTEGER,
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255),
    data_consulta DATE,
    hora_consulta TIME
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id_fatura,
        v.data_pagamento,
        v.valor,
        v.estado_fatura,
        v.metodo_pagamento,
        v.id_consulta,
        v.paciente_nome,
        v.medico_nome,
        v.nome_especialidade,
        v.data_consulta,
        v.hora_consulta
    FROM vw_faturas_completas v
    WHERE (p_data_inicio IS NULL OR v.data_pagamento >= p_data_inicio)
      AND (p_data_fim IS NULL OR v.data_pagamento <= p_data_fim)
      AND (p_estado IS NULL OR v.estado_fatura = p_estado)
    ORDER BY v.id_fatura DESC;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_faturas_stats(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    total_faturas BIGINT,
    valor_total NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        COALESCE(SUM(valor), 0)
    FROM vw_faturas_completas v
    WHERE (p_data_inicio IS NULL OR v.data_pagamento >= p_data_inicio)
      AND (p_data_fim IS NULL OR v.data_pagamento <= p_data_fim)
      AND (p_estado IS NULL OR v.estado_fatura = p_estado);
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_faturas_por_estado(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    estado VARCHAR(50),
    quantidade BIGINT,
    valor_total NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.estado_fatura,
        COUNT(*)::BIGINT,
        COALESCE(SUM(v.valor), 0)
    FROM vw_faturas_completas v
    WHERE (p_data_inicio IS NULL OR v.data_pagamento >= p_data_inicio)
      AND (p_data_fim IS NULL OR v.data_pagamento <= p_data_fim)
      AND (p_estado IS NULL OR v.estado_fatura = p_estado)
    GROUP BY v.estado_fatura
    ORDER BY COUNT(*) DESC;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_faturas_detalhes(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_fatura INTEGER,
    data_pagamento DATE,
    valor NUMERIC,
    estado VARCHAR(50),
    metodo_pagamento VARCHAR(50),
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    id_paciente INTEGER,
    paciente_nome VARCHAR(255),
    n_utente VARCHAR(20),
    id_medico INTEGER,
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id_fatura,
        v.data_pagamento,
        v.valor,
        v.estado_fatura,
        v.metodo_pagamento,
        v.id_consulta,
        v.data_consulta,
        v.hora_consulta,
        v.id_paciente,
        v.paciente_nome,
        v.n_utente,
        v.id_medico,
        v.medico_nome,
        v.nome_especialidade
    FROM vw_faturas_completas v
    WHERE (p_data_inicio IS NULL OR v.data_pagamento >= p_data_inicio)
      AND (p_data_fim IS NULL OR v.data_pagamento <= p_data_fim)
      AND (p_estado IS NULL OR v.estado_fatura = p_estado)
    ORDER BY v.id_fatura DESC
    LIMIT p_limite;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_listar(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255),
    estado VARCHAR(50),
    motivo VARCHAR(255),
    valor NUMERIC,
    id_fatura INTEGER,
    criado_em TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.paciente_nome,
        c.medico_nome,
        c.nome_especialidade,
        c.estado,
        c.motivo,
        COALESCE(c.fatura_valor, 0),
        c.id_fatura,
        c.criado_em::timestamp
    FROM vw_consultas_com_fatura c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC;
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_total(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total
    FROM vw_consultas_com_fatura c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id);

    RETURN COALESCE(v_total, 0);
END;
$$;

CREATE OR REPLACE FUNCTION relatorio_consultas_detalhes(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR DEFAULT NULL,
    p_medico_id INTEGER DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    id_paciente INTEGER,
    paciente_nome VARCHAR(255),
    id_medico INTEGER,
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255),
    id_fatura INTEGER,
    fatura_valor NUMERIC,
    fatura_estado VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.motivo,
        c.id_paciente,
        c.paciente_nome,
        c.id_medico,
        c.medico_nome,
        c.nome_especialidade,
        c.id_fatura,
        c.fatura_valor,
        c.fatura_estado
    FROM vw_consultas_com_fatura c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
      AND (p_estado IS NULL OR c.estado = p_estado)
      AND (p_medico_id IS NULL OR c.id_medico = p_medico_id)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC
    LIMIT p_limite;
END;
$$;

-- Função para listar especialidades
CREATE OR REPLACE FUNCTION listar_especialidades()
RETURNS TABLE (
    id_especialidade INTEGER,
    nome_especialidade VARCHAR(255),
    descricao VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT e.id_especialidade, e.nome_especialidade, e.descricao
    FROM "ESPECIALIDADES" e
    ORDER BY e.nome_especialidade;
END;
$$;

-- Função para listar especialidades (admin) com nº de médicos
CREATE OR REPLACE FUNCTION listar_especialidades_admin()
RETURNS TABLE (
    id_especialidade INTEGER,
    nome_especialidade VARCHAR(255),
    descricao VARCHAR(255),
    num_medicos BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id_especialidade,
        e.nome_especialidade,
        e.descricao,
        COUNT(m.id_medico) AS num_medicos
    FROM "ESPECIALIDADES" e
    LEFT JOIN "MEDICOS" m ON m.id_especialidade = e.id_especialidade
    GROUP BY e.id_especialidade, e.nome_especialidade, e.descricao
    ORDER BY e.nome_especialidade;
END;
$$;

-- Função para obter especialidade por ID (admin)
CREATE OR REPLACE FUNCTION obter_especialidade_por_id(p_id_especialidade INTEGER)
RETURNS TABLE (
    id_especialidade INTEGER,
    nome_especialidade VARCHAR(255),
    descricao VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT e.id_especialidade, e.nome_especialidade, e.descricao
    FROM "ESPECIALIDADES" e
    WHERE e.id_especialidade = p_id_especialidade
    LIMIT 1;
END;
$$;

-- Função para listar unidades (admin) com nome da região
CREATE OR REPLACE FUNCTION listar_unidades_admin()
RETURNS TABLE (
    id_unidade INTEGER,
    nome_unidade VARCHAR(255),
    morada_unidade VARCHAR(255),
    tipo_unidade VARCHAR(255),
    id_regiao INTEGER,
    nome_regiao VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id_unidade,
           u.nome_unidade,
           u.morada_unidade,
           u.tipo_unidade,
           r.id_regiao,
           r.nome
    FROM "UNIDADE_DE_SAUDE" u
    JOIN "REGIAO" r ON u.id_regiao = r.id_regiao
    ORDER BY u.nome_unidade;
END;
$$;

-- Função para obter unidade por ID (admin)
CREATE OR REPLACE FUNCTION obter_unidade_por_id(p_id_unidade INTEGER)
RETURNS TABLE (
    id_unidade INTEGER,
    nome_unidade VARCHAR(255),
    morada_unidade VARCHAR(255),
    tipo_unidade VARCHAR(255),
    id_regiao INTEGER,
    nome_regiao VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id_unidade,
           u.nome_unidade,
           u.morada_unidade,
           u.tipo_unidade,
           r.id_regiao,
           r.nome
    FROM "UNIDADE_DE_SAUDE" u
    JOIN "REGIAO" r ON u.id_regiao = r.id_regiao
    WHERE u.id_unidade = p_id_unidade
    LIMIT 1;
END;
$$;

-- Função para listar unidades de saúde
CREATE OR REPLACE FUNCTION listar_unidades()
RETURNS TABLE (
    id_unidade INTEGER,
    nome_unidade VARCHAR(255),
    morada_unidade VARCHAR(255),
    tipo_unidade VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id_unidade, u.nome_unidade, u.morada_unidade, u.tipo_unidade
    FROM "UNIDADE_DE_SAUDE" u
    ORDER BY u.nome_unidade;
END;
$$;

-- Função para listar médicos com filtros (CORRIGIDA)
CREATE OR REPLACE FUNCTION listar_medicos_filtrados(
    p_especialidade_id INTEGER DEFAULT NULL,
    p_unidade_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id_medico INTEGER,
    nome VARCHAR(255),
    especialidade VARCHAR(255),
    tem_disponibilidade_unidade BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        m.id_medico,
        u.nome,
        COALESCE(e.nome_especialidade, 'Sem especialidade') as especialidade,
        CASE 
            WHEN p_unidade_id IS NULL THEN TRUE
            ELSE EXISTS (
                SELECT 1 FROM "DISPONIBILIDADE" d
                WHERE d.id_medico = m.id_medico
                AND d.id_unidade = p_unidade_id
                AND d.status_slot IN ('disponivel', 'available')
                AND d.data >= CURRENT_DATE
            )
        END as tem_disponibilidade_unidade
    FROM "MEDICOS" m
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE (p_especialidade_id IS NULL OR m.id_especialidade = p_especialidade_id)
    AND u.ativo = TRUE
    ORDER BY u.nome;
END;
$$;

-- Função para verificar se slot está disponível
CREATE OR REPLACE FUNCTION verificar_slot_disponivel(
    p_disponibilidade_id INTEGER,
    p_hora_consulta TIME
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_disponivel BOOLEAN;
BEGIN
    SELECT NOT EXISTS (
        SELECT 1 
        FROM "CONSULTAS" c
        WHERE c.id_disponibilidade = p_disponibilidade_id
        AND c.hora_consulta = p_hora_consulta
        AND c.estado != 'cancelada'
    ) INTO v_disponivel;
    
    RETURN v_disponivel;
END;
$$;

-- Função para calcular idade do paciente
CREATE OR REPLACE FUNCTION calcular_idade_paciente(p_id_paciente INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_data_nasc DATE;
    v_idade INTEGER;
BEGIN
    SELECT data_nasc INTO v_data_nasc
    FROM "PACIENTES"
    WHERE id_paciente = p_id_paciente;
    
    v_idade := EXTRACT(YEAR FROM AGE(CURRENT_DATE, v_data_nasc));
    
    RETURN v_idade;
END;
$$;

-- Função para contar consultas por estado
CREATE OR REPLACE FUNCTION contar_consultas_por_estado(
    p_id_paciente INTEGER DEFAULT NULL,
    p_id_medico INTEGER DEFAULT NULL
)
RETURNS TABLE (
    estado VARCHAR(50),
    quantidade INTEGER
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.estado,
        COUNT(*) as quantidade
    FROM "CONSULTAS" c
    WHERE (p_id_paciente IS NULL OR c.id_paciente = p_id_paciente)
    AND (p_id_medico IS NULL OR c.id_medico = p_id_medico)
    GROUP BY c.estado
    ORDER BY quantidade DESC;
END;
$$;

-- Função para obter próxima consulta do paciente
CREATE OR REPLACE FUNCTION obter_proxima_consulta_paciente(p_id_paciente INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    medico_nome VARCHAR(255),
    especialidade VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        u.nome as medico_nome,
        COALESCE(e.nome_especialidade, 'Sem especialidade') as especialidade
    FROM "CONSULTAS" c
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE c.id_paciente = p_id_paciente
    AND c.estado IN ('agendada', 'confirmada')
    AND (c.data_consulta > CURRENT_DATE OR 
         (c.data_consulta = CURRENT_DATE AND c.hora_consulta > CURRENT_TIME))
    ORDER BY c.data_consulta, c.hora_consulta
    LIMIT 1;
END;
$$;

-- Função para verificar se utilizador tem consulta ativa
CREATE OR REPLACE FUNCTION verificar_consulta_ativa(p_id_utilizador INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_tem_consulta BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM "CONSULTAS" c
        JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
        WHERE p.id_utilizador = p_id_utilizador
        AND c.estado IN ('agendada', 'confirmada')
        AND (c.data_consulta > CURRENT_DATE OR 
             (c.data_consulta = CURRENT_DATE AND c.hora_consulta > CURRENT_TIME))
    ) INTO v_tem_consulta;
    
    RETURN v_tem_consulta;
END;
$$;

-- Função para obter disponibilidades filtradas
CREATE OR REPLACE FUNCTION obter_disponibilidades_filtradas(
    p_id_medico INTEGER DEFAULT NULL,
    p_id_unidade INTEGER DEFAULT NULL,
    p_data DATE DEFAULT NULL
)
RETURNS TABLE (
    id_disponibilidade INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    duracao_slot INTEGER,
    status_slot VARCHAR(20),
    id_unidade INTEGER,
    nome_unidade VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id_disponibilidade,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        d.duracao_slot,
        d.status_slot,
        d.id_unidade,
        un.nome_unidade,
        u.nome as medico_nome,
        COALESCE(e.nome_especialidade, 'Sem especialidade') as especialidade_nome
    FROM "DISPONIBILIDADE" d
    JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    JOIN "MEDICOS" m ON d.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE d.status_slot IN ('disponivel', 'available')
    AND d.data >= CURRENT_DATE
    AND (p_id_medico IS NULL OR d.id_medico = p_id_medico)
    AND (p_id_unidade IS NULL OR d.id_unidade = p_id_unidade)
    AND (p_data IS NULL OR d.data = p_data)
    ORDER BY d.data, d.hora_inicio;
END;
$$;

-- Função para obter consultas de hoje do médico
CREATE OR REPLACE FUNCTION obter_consultas_hoje_medico(p_id_medico INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    medico_nome VARCHAR(255),
    nome_especialidade VARCHAR(255),
    nome_unidade VARCHAR(255),
    can_cancel_24h BOOLEAN
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
BEGIN
    RETURN QUERY
    SELECT 
        vc.id_consulta,
        vc.data_consulta,
        vc.hora_consulta,
        vc.estado,
        vc.motivo,
        vc.paciente_nome,
        vc.paciente_email,
        vc.medico_nome,
        vc.nome_especialidade,
        vc.nome_unidade,
        CASE 
            WHEN (vc.data_consulta || ' ' || vc.hora_consulta)::timestamp - INTERVAL '24 hours' > CURRENT_TIMESTAMP 
            THEN TRUE 
            ELSE FALSE 
        END as can_cancel_24h
    FROM vw_consultas_completas vc
    WHERE vc.id_medico = p_id_medico
        AND vc.data_consulta = v_hoje
        AND vc.estado NOT IN ('cancelada')
    ORDER BY vc.hora_consulta;
END;
$$;

-- Função para obter próximas consultas do médico
CREATE OR REPLACE FUNCTION obter_proximas_consultas_medico(p_id_medico INTEGER, p_limite INTEGER DEFAULT 10)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    nome_especialidade VARCHAR(255),
    nome_unidade VARCHAR(255),
    can_cancel_24h BOOLEAN
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
BEGIN
    RETURN QUERY
    SELECT 
        vc.id_consulta,
        vc.data_consulta,
        vc.hora_consulta,
        vc.estado,
        vc.motivo,
        vc.paciente_nome,
        vc.paciente_email,
        vc.nome_especialidade,
        vc.nome_unidade,
        CASE 
            WHEN (vc.data_consulta || ' ' || vc.hora_consulta)::timestamp - INTERVAL '24 hours' > CURRENT_TIMESTAMP 
            THEN TRUE 
            ELSE FALSE 
        END as can_cancel_24h
    FROM vw_consultas_completas vc
    WHERE vc.id_medico = p_id_medico
        AND vc.data_consulta >= v_hoje
        AND vc.estado IN ('agendada', 'confirmada')
    ORDER BY vc.data_consulta, vc.hora_consulta
    LIMIT p_limite;
END;
$$;

-- Função para contar consultas da semana do médico
CREATE OR REPLACE FUNCTION contar_consultas_semana_medico(p_id_medico INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio_semana DATE := DATE_TRUNC('week', CURRENT_DATE)::DATE;
    v_fim_semana DATE := (DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days')::DATE;
    v_contagem INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_contagem
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta BETWEEN v_inicio_semana AND v_fim_semana
        AND c.estado = 'confirmada';
    
    RETURN COALESCE(v_contagem, 0);
END;
$$;

-- Função para contar consultas do mês do médico
CREATE OR REPLACE FUNCTION contar_consultas_mes_medico(p_id_medico INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio_mes DATE := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    v_contagem INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_contagem
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta >= v_inicio_mes
        AND c.estado = 'confirmada';
    
    RETURN COALESCE(v_contagem, 0);
END;
$$;

-- Função para contar pedidos pendentes do médico
CREATE OR REPLACE FUNCTION contar_pedidos_pendentes_medico(p_id_medico INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_contagem INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_contagem
    FROM "CONSULTAS" c
    WHERE c.id_medico = p_id_medico
        AND c.estado = 'agendada'
        AND (c.medico_aceitou = FALSE OR c.paciente_aceitou = FALSE);
    
    RETURN COALESCE(v_contagem, 0);
END;
$$;

-- Função para obter estatísticas do médico
CREATE OR REPLACE FUNCTION obter_estatisticas_medico(p_id_medico INTEGER)
RETURNS TABLE (
    consultas_realizadas BIGINT,
    consultas_agendadas BIGINT,
    consultas_confirmadas BIGINT,
    consultas_canceladas BIGINT,
    disponibilidades_disponiveis BIGINT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(vm.consultas_realizadas, 0)::BIGINT,
        COALESCE(vm.consultas_agendadas, 0)::BIGINT,
        COALESCE(vm.consultas_confirmadas, 0)::BIGINT,
        COALESCE(vm.consultas_canceladas, 0)::BIGINT,
        COALESCE(vm.disponibilidades_disponiveis, 0)::BIGINT
    FROM vw_estatisticas_medicos vm
    WHERE vm.id_medico = p_id_medico;
    
    -- Se não retornou nada, retornar zeros
    IF NOT FOUND THEN
        RETURN QUERY SELECT 0::BIGINT, 0::BIGINT, 0::BIGINT, 0::BIGINT, 0::BIGINT;
    END IF;
END;
$$;

-- Função para obter agenda do médico (consultas e disponibilidades)
CREATE OR REPLACE FUNCTION obter_agenda_medico(
    p_id_medico INTEGER,
    p_data_inicial DATE DEFAULT NULL,
    p_data_final DATE DEFAULT NULL,
    p_periodo VARCHAR(10) DEFAULT 'semana'
)
RETURNS TABLE (
    tipo VARCHAR(20),
    id INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    unidade_nome VARCHAR(255),
    can_cancel_24h BOOLEAN,
    status_slot VARCHAR(20),
    duracao_slot INTEGER
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio DATE;
    v_fim DATE;
    v_hoje DATE := CURRENT_DATE;
BEGIN
    -- Definir período baseado nos parâmetros
    IF p_data_inicial IS NULL THEN
        p_data_inicial := v_hoje;
    END IF;
    
    IF p_periodo = 'dia' THEN
        v_inicio := p_data_inicial;
        v_fim := p_data_inicial;
    ELSIF p_periodo = 'semana' THEN
        v_inicio := DATE_TRUNC('week', p_data_inicial)::DATE;
        v_fim := v_inicio + 6;
    ELSE -- mês
        v_inicio := DATE_TRUNC('month', p_data_inicial)::DATE;
        v_fim := (v_inicio + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
    END IF;
    
    -- Se data_final foi especificada, usar ela
    IF p_data_final IS NOT NULL THEN
        v_fim := p_data_final;
    END IF;
    
    -- Retornar consultas
    RETURN QUERY
    SELECT 
        'consulta'::VARCHAR(20) as tipo,
        c.id_consulta as id,
        c.data_consulta as data,
        c.hora_consulta as hora_inicio,
        (c.hora_consulta + INTERVAL '30 minutes')::TIME as hora_fim,
        c.estado,
        c.motivo,
        u_p.nome as paciente_nome,
        u_p.email as paciente_email,
        un.nome_unidade as unidade_nome,
        CASE 
            WHEN (c.data_consulta || ' ' || c.hora_consulta)::timestamp - INTERVAL '24 hours' > CURRENT_TIMESTAMP 
            THEN TRUE 
            ELSE FALSE 
        END as can_cancel_24h,
        NULL::VARCHAR(20) as status_slot,
        30 as duracao_slot
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
    LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
    LEFT JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta BETWEEN v_inicio AND v_fim
        AND c.estado NOT IN ('cancelada')
    ORDER BY c.data_consulta, c.hora_consulta;
    
    -- Retornar disponibilidades (apenas se ainda houver registros para retornar)
    IF NOT FOUND THEN
        -- Forçar retorno de disponibilidades mesmo sem consultas
        NULL;
    END IF;
    
    RETURN QUERY
    SELECT 
        'disponibilidade'::VARCHAR(20) as tipo,
        d.id_disponibilidade as id,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        NULL::VARCHAR(50) as estado,
        NULL::VARCHAR(255) as motivo,
        NULL::VARCHAR(255) as paciente_nome,
        NULL::VARCHAR(255) as paciente_email,
        un.nome_unidade as unidade_nome,
        NULL::BOOLEAN as can_cancel_24h,
        d.status_slot,
        d.duracao_slot
    FROM "DISPONIBILIDADE" d
    JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE d.id_medico = p_id_medico
        AND d.data BETWEEN v_inicio AND v_fim
    ORDER BY d.data, d.hora_inicio;
END;
$$;

-- Função para obter calendário mensal do médico
CREATE OR REPLACE FUNCTION obter_calendario_mensal_medico(
    p_id_medico INTEGER,
    p_ano INTEGER,
    p_mes INTEGER
)
RETURNS TABLE (
    tipo VARCHAR(20),
    id INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    paciente_nome VARCHAR(255),
    unidade_nome VARCHAR(255),
    can_cancel_24h BOOLEAN,
    status_slot VARCHAR(20)
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio_mes DATE;
    v_fim_mes DATE;
BEGIN
    -- Definir início e fim do mês
    v_inicio_mes := MAKE_DATE(p_ano, p_mes, 1);
    v_fim_mes := (v_inicio_mes + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
    
    -- Retornar consultas do mês
    RETURN QUERY
    SELECT 
        'consulta'::VARCHAR(20) as tipo,
        c.id_consulta as id,
        c.data_consulta as data,
        c.hora_consulta as hora_inicio,
        (c.hora_consulta + INTERVAL '30 minutes')::TIME as hora_fim,
        c.estado,
        c.motivo,
        u_p.nome as paciente_nome,
        un.nome_unidade as unidade_nome,
        CASE 
            WHEN (c.data_consulta || ' ' || c.hora_consulta)::timestamp - INTERVAL '24 hours' > CURRENT_TIMESTAMP 
            THEN TRUE 
            ELSE FALSE 
        END as can_cancel_24h,
        NULL::VARCHAR(20) as status_slot
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
    LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
    LEFT JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE c.id_medico = p_id_medico
        AND c.data_consulta BETWEEN v_inicio_mes AND v_fim_mes
        AND c.estado NOT IN ('cancelada')
    ORDER BY c.data_consulta, c.hora_consulta;
    
    -- Retornar disponibilidades do mês
    RETURN QUERY
    SELECT 
        'disponibilidade'::VARCHAR(20) as tipo,
        d.id_disponibilidade as id,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        NULL::VARCHAR(50) as estado,
        NULL::VARCHAR(255) as motivo,
        NULL::VARCHAR(255) as paciente_nome,
        un.nome_unidade as unidade_nome,
        NULL::BOOLEAN as can_cancel_24h,
        d.status_slot
    FROM "DISPONIBILIDADE" d
    JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE d.id_medico = p_id_medico
        AND d.data BETWEEN v_inicio_mes AND v_fim_mes
    ORDER BY d.data, d.hora_inicio;
END;
$$;

-- Função para obter pacientes ativos
CREATE OR REPLACE FUNCTION obter_pacientes_ativos()
RETURNS TABLE (
    id_paciente INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    data_nasc DATE,
    genero VARCHAR(50)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id_paciente,
        u.nome,
        u.email,
        u.telefone,
        u.n_utente,
        p.data_nasc,
        p.genero
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    WHERE u.ativo = TRUE
    ORDER BY u.nome;
END;
$$;

-- Função para obter unidades de saúde
CREATE OR REPLACE FUNCTION obter_unidades_saude()
RETURNS TABLE (
    id_unidade INTEGER,
    nome_unidade VARCHAR(255),
    morada_unidade VARCHAR(255),
    tipo_unidade VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_unidade,
        u.nome_unidade,
        u.morada_unidade,
        u.tipo_unidade
    FROM "UNIDADE_DE_SAUDE" u
    ORDER BY u.nome_unidade;
END;
$$;

-- ============================================================================
-- FUNÇÕES PARA ENFERMEIRO (Dashboard e Consultas)
-- ============================================================================

-- Função para obter enfermeiro pelo utilizador
CREATE OR REPLACE FUNCTION obter_enfermeiro_por_utilizador(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_enfermeiro INTEGER,
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_ordem_enf VARCHAR(50),
    unidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id_enfermeiro,
        u.id_utilizador,
        u.nome,
        u.email,
        u.telefone,
        e.n_ordem_enf,
        NULL::VARCHAR(255) AS unidade_nome
    FROM "ENFERMEIRO" e
    JOIN "core_utilizador" u ON e.id_utilizador = u.id_utilizador
    WHERE u.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para estatísticas do dashboard do enfermeiro
CREATE OR REPLACE FUNCTION obter_estatisticas_enfermeiro()
RETURNS TABLE (
    consultas_hoje INTEGER,
    consultas_pendentes INTEGER,
    pacientes_semana INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
    v_inicio_semana DATE := DATE_TRUNC('week', CURRENT_DATE)::DATE;
BEGIN
    SELECT COUNT(*) INTO consultas_hoje
    FROM "CONSULTAS"
    WHERE data_consulta = v_hoje
      AND estado = 'confirmada';

    SELECT COUNT(*) INTO consultas_pendentes
    FROM "CONSULTAS"
    WHERE estado IN ('agendada', 'marcada', 'confirmada');

    SELECT COUNT(DISTINCT id_paciente) INTO pacientes_semana
    FROM "CONSULTAS"
    WHERE data_consulta >= v_inicio_semana
      AND estado = 'realizada';

    RETURN NEXT;
END;
$$;

-- Função para listar consultas com filtros (enfermeiro)
CREATE OR REPLACE FUNCTION listar_consultas_enfermeiro(
    p_estado VARCHAR DEFAULT NULL,
    p_data DATE DEFAULT NULL,
    p_id_medico INTEGER DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.paciente_nome,
        c.medico_nome,
        c.nome_especialidade
    FROM vw_consultas_completas c
    WHERE (p_estado IS NULL OR p_estado = '' OR c.estado = p_estado)
      AND (p_data IS NULL OR c.data_consulta = p_data)
      AND (p_id_medico IS NULL OR c.id_medico = p_id_medico)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC
    LIMIT p_limite;
END;
$$;

-- Função para listar próximas consultas (enfermeiro)
CREATE OR REPLACE FUNCTION listar_proximas_consultas_enfermeiro(
    p_limite INTEGER DEFAULT 10
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    paciente_nome VARCHAR(255),
    medico_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.paciente_nome,
        c.medico_nome
    FROM vw_consultas_completas c
    WHERE c.data_consulta >= CURRENT_DATE
      AND c.estado IN ('agendada', 'marcada', 'confirmada')
    ORDER BY c.data_consulta, c.hora_consulta
    LIMIT p_limite;
END;
$$;

-- Função para listar médicos (enfermeiro)
CREATE OR REPLACE FUNCTION listar_medicos_enfermeiro()
RETURNS TABLE (
    id_medico INTEGER,
    nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id_medico,
        u.nome,
        e.nome_especialidade
    FROM "MEDICOS" m
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    ORDER BY u.nome;
END;
$$;

-- Função para listar pacientes com consultas (enfermeiro)
CREATE OR REPLACE FUNCTION listar_pacientes_enfermeiro(
    p_search VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id_paciente INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    total_consultas BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id_paciente,
        u.nome,
        u.email,
        u.telefone,
        u.n_utente,
        COUNT(c.id_consulta)::BIGINT as total_consultas
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    JOIN "CONSULTAS" c ON c.id_paciente = p.id_paciente
    WHERE u.ativo = TRUE
      AND (
          p_search IS NULL OR p_search = ''
          OR u.nome ILIKE '%' || p_search || '%'
          OR u.email ILIKE '%' || p_search || '%'
          OR u.n_utente ILIKE '%' || p_search || '%'
      )
    GROUP BY p.id_paciente, u.nome, u.email, u.telefone, u.n_utente
    ORDER BY u.nome;
END;
$$;

-- Função para obter detalhes do paciente (enfermeiro)
CREATE OR REPLACE FUNCTION obter_paciente_detalhes_enfermeiro(
    p_id_paciente INTEGER
)
RETURNS TABLE (
    id_paciente INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    data_nasc DATE,
    genero VARCHAR(50),
    morada VARCHAR(255),
    alergias VARCHAR(255),
    observacoes VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id_paciente,
        u.nome,
        u.email,
        u.telefone,
        u.n_utente,
        p.data_nasc,
        p.genero,
        COALESCE(p.morada, ''),
        COALESCE(p.alergias, ''),
        COALESCE(p.observacoes, '')
    FROM "PACIENTES" p
    JOIN "core_utilizador" u ON p.id_utilizador = u.id_utilizador
    WHERE p.id_paciente = p_id_paciente
    LIMIT 1;
END;
$$;

-- Função para listar consultas do paciente (enfermeiro)
CREATE OR REPLACE FUNCTION listar_consultas_paciente_enfermeiro(
    p_id_paciente INTEGER
)
RETURNS TABLE (
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.medico_nome,
        c.nome_especialidade
    FROM vw_consultas_completas c
    WHERE c.id_paciente = p_id_paciente
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC;
END;
$$;

-- Função para listar faturas do paciente (enfermeiro)
CREATE OR REPLACE FUNCTION listar_faturas_paciente_enfermeiro(
    p_id_paciente INTEGER
)
RETURNS TABLE (
    data_pagamento DATE,
    valor NUMERIC,
    metodo_pagamento VARCHAR(50),
    estado VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.data_pagamento,
        f.valor,
        f.metodo_pagamento,
        f.estado
    FROM "FATURAS" f
    JOIN "CONSULTAS" c ON f.id_consulta = c.id_consulta
    WHERE c.id_paciente = p_id_paciente
    ORDER BY f.data_pagamento DESC NULLS LAST, f.id_fatura DESC;
END;
$$;

-- Função para listar receitas do paciente (enfermeiro)
CREATE OR REPLACE FUNCTION listar_receitas_paciente_enfermeiro(
    p_id_paciente INTEGER
)
RETURNS TABLE (
    data_prescricao DATE,
    medicamento VARCHAR(255),
    dosagem VARCHAR(255),
    medico_nome VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.data_prescricao,
        r.medicamento,
        r.dosagem,
        u.nome as medico_nome
    FROM "RECEITAS" r
    JOIN "CONSULTAS" c ON r.id_consulta = c.id_consulta
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    WHERE c.id_paciente = p_id_paciente
    ORDER BY r.id_receita DESC;
END;
$$;

-- Função para totais do relatório do enfermeiro
CREATE OR REPLACE FUNCTION obter_totais_relatorio_enfermeiro(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL
)
RETURNS TABLE (
    total_consultas BIGINT,
    total_receitas BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_consultas,
        (
            SELECT COUNT(*)::BIGINT
            FROM "RECEITAS" r
            JOIN "CONSULTAS" c2 ON r.id_consulta = c2.id_consulta
            WHERE (p_data_inicio IS NULL OR c2.data_consulta >= p_data_inicio)
              AND (p_data_fim IS NULL OR c2.data_consulta <= p_data_fim)
        ) AS total_receitas
    FROM "CONSULTAS" c
    WHERE (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
      AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim);
END;
$$;

-- Função para obter disponibilidades futuras para agendamento
CREATE OR REPLACE FUNCTION obter_disponibilidades_agendar_medico(
    p_id_medico INTEGER,
    p_limite INTEGER DEFAULT 50
)
RETURNS TABLE (
    id_disponibilidade INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    duracao_slot INTEGER,
    nome_unidade VARCHAR(255),
    morada_unidade VARCHAR(255),
    slots_disponiveis INTEGER
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
BEGIN
    RETURN QUERY
    SELECT 
        d.id_disponibilidade,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        d.duracao_slot,
        un.nome_unidade,
        un.morada_unidade,
        -- Calcular slots disponíveis
        (((EXTRACT(EPOCH FROM (d.hora_fim - d.hora_inicio)) / 60) / d.duracao_slot)
        - (SELECT COUNT(*) 
           FROM "CONSULTAS" c 
           WHERE c.id_disponibilidade = d.id_disponibilidade 
           AND c.estado NOT IN ('cancelada')))::INTEGER as slots_disponiveis
    FROM "DISPONIBILIDADE" d
    JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE d.id_medico = p_id_medico
        AND d.data >= v_hoje
        AND d.status_slot IN ('disponivel', 'available')
        AND ((EXTRACT(EPOCH FROM (d.hora_fim - d.hora_inicio)) / 60) / d.duracao_slot)
            > (SELECT COUNT(*) 
               FROM "CONSULTAS" c 
               WHERE c.id_disponibilidade = d.id_disponibilidade 
               AND c.estado NOT IN ('cancelada'))
    ORDER BY d.data, d.hora_inicio
    LIMIT p_limite;
END;
$$;

-- Função para obter disponibilidades futuras não ocupadas
CREATE OR REPLACE FUNCTION obter_disponibilidades_futuras_medico(
    p_id_medico INTEGER,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_disponibilidade INTEGER,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    status_slot VARCHAR(20),
    nome_unidade VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_hoje DATE := CURRENT_DATE;
BEGIN
    RETURN QUERY
    SELECT 
        d.id_disponibilidade,
        d.data,
        d.hora_inicio,
        d.hora_fim,
        d.status_slot,
        un.nome_unidade
    FROM "DISPONIBILIDADE" d
    JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
    WHERE d.id_medico = p_id_medico
        AND d.data >= v_hoje
        AND d.status_slot != 'booked'
    ORDER BY d.data, d.hora_inicio
    LIMIT p_limite;
END;
$$;

-- Função para verificar se médico existe
CREATE OR REPLACE FUNCTION verificar_medico_por_utilizador(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_medico INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    numero_ordem VARCHAR(50),
    especialidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id_medico,
        u.nome,
        u.email,
        m.numero_ordem,
        COALESCE(e.nome_especialidade, 'Sem especialidade') as especialidade_nome
    FROM "MEDICOS" m
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE m.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para verificar se disponibilidade pode ser excluída
CREATE OR REPLACE FUNCTION verificar_exclusao_disponibilidade(
    p_disponibilidade_id INTEGER,
    p_id_medico INTEGER
)
RETURNS TABLE (
    pode_excluir BOOLEAN,
    mensagem VARCHAR(500)
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_existe BOOLEAN;
    v_tem_consultas BOOLEAN;
BEGIN
    -- Verificar se disponibilidade existe e pertence ao médico
    SELECT EXISTS(
        SELECT 1 FROM "DISPONIBILIDADE" d
        WHERE d.id_disponibilidade = p_disponibilidade_id
        AND d.id_medico = p_id_medico
    ) INTO v_existe;
    
    IF NOT v_existe THEN
        pode_excluir := FALSE;
        mensagem := 'Disponibilidade não encontrada.';
        RETURN;
    END IF;
    
    -- Verificar se tem consultas associadas
    SELECT EXISTS(
        SELECT 1 FROM "CONSULTAS" c
        WHERE c.id_disponibilidade = p_disponibilidade_id
        AND c.estado NOT IN ('cancelada')
    ) INTO v_tem_consultas;
    
    IF v_tem_consultas THEN
        pode_excluir := FALSE;
        mensagem := 'Não é possível excluir uma disponibilidade que já tem consultas marcadas.';
    ELSE
        pode_excluir := TRUE;
        mensagem := 'Disponibilidade pode ser excluída.';
    END IF;
    
    RETURN NEXT;
END;
$$;

-- Função para obter médico por ID de utilizador
CREATE OR REPLACE FUNCTION obter_medico_por_utilizador(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_medico INTEGER,
    id_utilizador INTEGER,
    numero_ordem VARCHAR(50),
    id_especialidade INTEGER
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id_medico,
        m.id_utilizador,
        m.numero_ordem,
        m.id_especialidade
    FROM "MEDICOS" m
    WHERE m.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para verificar se consulta pertence ao médico
CREATE OR REPLACE FUNCTION verificar_consulta_medico(
    p_id_consulta INTEGER,
    p_id_medico INTEGER
)
RETURNS TABLE (
    existe BOOLEAN,
    estado VARCHAR(50),
    data_consulta DATE,
    hora_consulta TIME,
    id_disponibilidade INTEGER
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TRUE as existe,
        c.estado,
        c.data_consulta,
        c.hora_consulta,
        c.id_disponibilidade
    FROM "CONSULTAS" c
    WHERE c.id_consulta = p_id_consulta
    AND c.id_medico = p_id_medico
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::VARCHAR(50), NULL::DATE, NULL::TIME, NULL::INTEGER;
    END IF;
END;
$$;

-- Função para obter informações completas de consulta
CREATE OR REPLACE FUNCTION obter_consulta_completa(p_id_consulta INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo VARCHAR(255),
    medico_aceitou BOOLEAN,
    paciente_aceitou BOOLEAN,
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vc.id_consulta,
        vc.data_consulta,
        vc.hora_consulta,
        vc.estado,
        vc.motivo,
        vc.medico_aceitou,
        vc.paciente_aceitou,
        vc.paciente_nome,
        vc.paciente_email,
        vc.medico_nome,
        COALESCE(vc.nome_especialidade, 'Sem especialidade') as especialidade_nome
    FROM vw_consultas_completas vc
    WHERE vc.id_consulta = p_id_consulta
    LIMIT 1;
END;
$$;

-- Função para obter médico por ID de utilizador
CREATE OR REPLACE FUNCTION obter_medico_por_utilizador_id(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_medico INTEGER,
    id_utilizador INTEGER,
    numero_ordem VARCHAR(50),
    id_especialidade INTEGER
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id_medico,
        m.id_utilizador,
        m.numero_ordem,
        m.id_especialidade
    FROM "MEDICOS" m
    WHERE m.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para verificar se utilizador é médico
CREATE OR REPLACE FUNCTION verificar_utilizador_eh_medico(p_id_utilizador INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_eh_medico BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM "MEDICOS" m
        JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
        WHERE m.id_utilizador = p_id_utilizador
        AND u.ativo = TRUE
    ) INTO v_eh_medico;
    
    RETURN v_eh_medico;
END;
$$;

-- Função para obter todas as informações do médico
CREATE OR REPLACE FUNCTION obter_medico_completo(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_medico INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    numero_ordem VARCHAR(50),
    especialidade_nome VARCHAR(255),
    especialidade_descricao VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id_medico,
        u.nome,
        u.email,
        u.telefone,
        u.n_utente,
        m.numero_ordem,
        COALESCE(e.nome_especialidade, 'Sem especialidade') as especialidade_nome,
        e.descricao as especialidade_descricao
    FROM "MEDICOS" m
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE m.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para obter estatísticas do dashboard admin
CREATE OR REPLACE FUNCTION obter_dashboard_admin_stats(p_inicio_mes DATE)
RETURNS TABLE (
        total_pacientes BIGINT,
        total_medicos BIGINT,
        total_enfermeiros BIGINT,
        total_unidades BIGINT,
        consultas_hoje_confirmadas BIGINT,
        consultas_mes_confirmadas BIGINT,
        consultas_pendentes BIGINT,
        faturas_pendentes BIGINT,
        receita_mes NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
        v_hoje DATE := CURRENT_DATE;
BEGIN
        SELECT COUNT(*) INTO total_pacientes FROM "PACIENTES";
        SELECT COUNT(*) INTO total_medicos FROM "MEDICOS";
        SELECT COUNT(*) INTO total_enfermeiros FROM "ENFERMEIRO";
        SELECT COUNT(*) INTO total_unidades FROM "UNIDADE_DE_SAUDE";

        SELECT COUNT(*) INTO consultas_hoje_confirmadas
        FROM "CONSULTAS"
        WHERE data_consulta = v_hoje
            AND estado = 'confirmada';

        SELECT COUNT(*) INTO consultas_mes_confirmadas
        FROM "CONSULTAS"
        WHERE data_consulta >= p_inicio_mes
            AND estado = 'confirmada';

        SELECT COUNT(*) INTO consultas_pendentes
        FROM "CONSULTAS"
        WHERE estado = 'agendada';

        SELECT COUNT(*) INTO faturas_pendentes
        FROM "FATURAS"
        WHERE estado = 'pendente';

        SELECT COALESCE(SUM(valor), 0) INTO receita_mes
        FROM "FATURAS"
        WHERE estado = 'paga'
            AND data_pagamento >= p_inicio_mes;

        RETURN NEXT;
END;
$$;

    -- Função para listar regiões (admin)
    CREATE OR REPLACE FUNCTION listar_regioes_admin()
    RETURNS TABLE (
        id_regiao INTEGER,
        nome VARCHAR(50),
        tipo_regiao VARCHAR(50)
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT r.id_regiao, r.nome, r.tipo_regiao
        FROM "REGIAO" r
        ORDER BY r.nome;
    END;
    $$;

    -- Função para obter região por ID (admin)
    CREATE OR REPLACE FUNCTION obter_regiao_por_id(p_id_regiao INTEGER)
    RETURNS TABLE (
        id_regiao INTEGER,
        nome VARCHAR(50),
        tipo_regiao VARCHAR(50)
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT r.id_regiao, r.nome, r.tipo_regiao
        FROM "REGIAO" r
        WHERE r.id_regiao = p_id_regiao
        LIMIT 1;
    END;
    $$;

    -- ============================================================================
-- FUNÇÕES PARA SUBSTITUIR ORM
-- Estas funções são criadas para eliminar o uso do Django ORM
-- ============================================================================

-- Função para obter Medico pelo id_utilizador
CREATE OR REPLACE FUNCTION obter_medico_por_id_utilizador(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_medico INTEGER,
    id_utilizador INTEGER,
    numero_ordem VARCHAR(50),
    id_especialidade INTEGER,
    especialidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id_medico,
        m.id_utilizador,
        m.numero_ordem,
        m.id_especialidade,
        e.nome_especialidade
    FROM "MEDICOS" m
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE m.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para obter Consulta com informações relacionadas
CREATE OR REPLACE FUNCTION obter_consulta_com_relacoes(p_id_consulta INTEGER)
RETURNS TABLE (
    id_consulta INTEGER,
    id_paciente INTEGER,
    id_medico INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo TEXT,
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    paciente_telefone VARCHAR(20),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255),
    nome_unidade VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_consulta,
        c.id_paciente,
        c.id_medico,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.motivo,
        pac_u.nome as paciente_nome,
        pac_u.email as paciente_email,
        pac_u.telefone as paciente_telefone,
        med_u.nome as medico_nome,
        e.nome_especialidade as especialidade_nome,
        u.nome_unidade as unidade_nome
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" pac_u ON p.id_utilizador = pac_u.id_utilizador
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" med_u ON m.id_utilizador = med_u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
    LEFT JOIN "UNIDADE_DE_SAUDE" u ON d.id_unidade = u.id_unidade
    WHERE c.id_consulta = p_id_consulta
    LIMIT 1;
END;
$$;

-- Função para obter histórico de consultas de um paciente
CREATE OR REPLACE FUNCTION obter_historico_consultas_paciente(
    p_id_paciente INTEGER,
    p_id_medico INTEGER DEFAULT NULL,
    p_estado VARCHAR(50) DEFAULT 'realizada',
    p_limite INTEGER DEFAULT 10
)
RETURNS TABLE (
    id_consulta INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo TEXT,
    observacoes TEXT,
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_consulta,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.motivo,
        c.observacoes,
        u.nome as medico_nome,
        e.nome_especialidade as especialidade_nome
    FROM "CONSULTAS" c
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    WHERE c.id_paciente = p_id_paciente
    AND (p_id_medico IS NULL OR c.id_medico = p_id_medico)
    AND (p_estado IS NULL OR c.estado = p_estado)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC
    LIMIT p_limite;
END;
$$;

-- Função para obter utilizador por email
CREATE OR REPLACE FUNCTION obter_utilizador_completo_por_email(p_email VARCHAR)
RETURNS TABLE (
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    password VARCHAR(128),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    role VARCHAR(20),
    data_registo TIMESTAMPTZ,
    ativo BOOLEAN,
    email_verified BOOLEAN,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_utilizador,
        u.nome,
        u.email,
        u.password,
        u.telefone,
        u.n_utente,
        u.role,
        u.data_registo,
        u.ativo,
        u.email_verified,
        u.last_login,
        COALESCE(u.is_superuser, FALSE) as is_superuser
    FROM "core_utilizador" u
    WHERE u.email = p_email
    LIMIT 1;
END;
$$;

-- Função para obter utilizador por primary key
CREATE OR REPLACE FUNCTION obter_utilizador_completo_por_pk(p_id_utilizador INTEGER)
RETURNS TABLE (
    id_utilizador INTEGER,
    nome VARCHAR(255),
    email VARCHAR(255),
    password VARCHAR(128),
    telefone VARCHAR(20),
    n_utente VARCHAR(20),
    role VARCHAR(20),
    data_registo TIMESTAMPTZ,
    ativo BOOLEAN,
    email_verified BOOLEAN,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id_utilizador,
        u.nome,
        u.email,
        u.password,
        u.telefone,
        u.n_utente,
        u.role,
        u.data_registo,
        u.ativo,
        u.email_verified,
        u.last_login,
        COALESCE(u.is_superuser, FALSE) as is_superuser
    FROM "core_utilizador" u
    WHERE u.id_utilizador = p_id_utilizador
    LIMIT 1;
END;
$$;

-- Função para obter consultas com filtros de data
CREATE OR REPLACE FUNCTION obter_consultas_com_filtros(
    p_id_paciente INTEGER DEFAULT NULL,
    p_id_medico INTEGER DEFAULT NULL,
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL,
    p_estado VARCHAR(50) DEFAULT NULL,
    p_limite INTEGER DEFAULT 100
)
RETURNS TABLE (
    id_consulta INTEGER,
    id_paciente INTEGER,
    id_medico INTEGER,
    data_consulta DATE,
    hora_consulta TIME,
    estado VARCHAR(50),
    motivo TEXT,
    paciente_nome VARCHAR(255),
    paciente_email VARCHAR(255),
    medico_nome VARCHAR(255),
    especialidade_nome VARCHAR(255),
    unidade_nome VARCHAR(255)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id_consulta,
        c.id_paciente,
        c.id_medico,
        c.data_consulta,
        c.hora_consulta,
        c.estado,
        c.motivo,
        pac_u.nome as paciente_nome,
        pac_u.email as paciente_email,
        med_u.nome as medico_nome,
        e.nome_especialidade as especialidade_nome,
        u.nome_unidade as unidade_nome
    FROM "CONSULTAS" c
    JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
    JOIN "core_utilizador" pac_u ON p.id_utilizador = pac_u.id_utilizador
    JOIN "MEDICOS" m ON c.id_medico = m.id_medico
    JOIN "core_utilizador" med_u ON m.id_utilizador = med_u.id_utilizador
    LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
    LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
    LEFT JOIN "UNIDADE_DE_SAUDE" u ON d.id_unidade = u.id_unidade
    WHERE (p_id_paciente IS NULL OR c.id_paciente = p_id_paciente)
    AND (p_id_medico IS NULL OR c.id_medico = p_id_medico)
    AND (p_data_inicio IS NULL OR c.data_consulta >= p_data_inicio)
    AND (p_data_fim IS NULL OR c.data_consulta <= p_data_fim)
    AND (p_estado IS NULL OR c.estado = p_estado)
    ORDER BY c.data_consulta DESC, c.hora_consulta DESC
    LIMIT p_limite;
END;
$$;

-- Procedure para inserir receita
CREATE OR REPLACE PROCEDURE inserir_receita(
    p_id_consulta INTEGER,
    p_medicamento VARCHAR(255),
    p_dosagem VARCHAR(255),
    p_instrucoes TEXT,
    p_data_prescricao DATE,
    OUT p_id_receita INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
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
        p_data_prescricao
    )
    RETURNING id_receita INTO p_id_receita;
    
    COMMIT;
END;
$$;

-- Procedure para atualizar estado da consulta
CREATE OR REPLACE PROCEDURE atualizar_estado_consulta(
    p_id_consulta INTEGER,
    p_novo_estado VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE "CONSULTAS"
    SET estado = p_novo_estado,
        modificado_em = NOW()
    WHERE id_consulta = p_id_consulta;
    
    COMMIT;
END;
$$;