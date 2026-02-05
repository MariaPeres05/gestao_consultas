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
