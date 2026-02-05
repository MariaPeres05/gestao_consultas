-- ============================================================================
-- VIEWS DO SISTEMA 
-- ============================================================================

-- View para consultas completas com informações relacionadas 
CREATE OR REPLACE VIEW vw_consultas_completas AS
SELECT 
    c.id_consulta,
    c.data_consulta,
    c.hora_consulta,
    c.estado,
    c.motivo,
    c.medico_aceitou,
    c.paciente_aceitou,
    c.paciente_presente,
    c.notas_clinicas,
    c.observacoes,
    c.hora_checkin,
    c.hora_inicio_real,
    c.hora_fim_real,
    c.criado_em,
    c.modificado_em,
    
    -- Dados do paciente
    p.id_paciente,
    u_p.nome as paciente_nome,
    u_p.email as paciente_email,
    u_p.telefone as paciente_telefone,
    u_p.n_utente,
    p.data_nasc,
    p.genero,
    p.alergias,
    p.observacoes as observacoes_paciente,
    
    -- Dados do médico
    m.id_medico,
    u_m.nome as medico_nome,
    u_m.email as medico_email,
    u_m.telefone as medico_telefone,
    m.numero_ordem as medico_numero_ordem,
    
    -- Especialidade do médico
    e.id_especialidade,
    e.nome_especialidade,
    e.descricao as especialidade_descricao,
    
    -- Unidade de saúde
    d.id_disponibilidade,
    un.id_unidade,
    un.nome_unidade,
    un.morada_unidade,
    un.tipo_unidade,
    
    -- Criador e modificador
    u_c.nome as criado_por_nome,
    u_mf.nome as modificado_por_nome,
    
    -- Cálculos úteis
    CASE 
        WHEN (c.data_consulta || ' ' || c.hora_consulta)::timestamp - INTERVAL '24 hours' > CURRENT_TIMESTAMP 
        THEN TRUE 
        ELSE FALSE 
    END as pode_cancelar_24h,
    
    EXTRACT(EPOCH FROM (c.data_consulta || ' ' || c.hora_consulta)::timestamp - CURRENT_TIMESTAMP) / 3600 as horas_restantes

FROM "CONSULTAS" c
JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
JOIN "MEDICOS" m ON c.id_medico = m.id_medico
JOIN "core_utilizador" u_m ON m.id_utilizador = u_m.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
LEFT JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
LEFT JOIN "core_utilizador" u_c ON c.criado_por = u_c.id_utilizador
LEFT JOIN "core_utilizador" u_mf ON c.modificado_por = u_mf.id_utilizador;

-- View para faturas com informações completas
CREATE OR REPLACE VIEW vw_faturas_completas AS
SELECT 
    f.id_fatura,
    f.valor,
    f.metodo_pagamento,
    f.estado as estado_fatura,
    f.data_pagamento,
    
    -- Dados da consulta
    c.id_consulta,
    c.data_consulta,
    c.hora_consulta,
    c.estado as estado_consulta,
    
    -- Dados do paciente
    p.id_paciente,
    u_p.nome as paciente_nome,
    u_p.email as paciente_email,
    u_p.n_utente,
    
    -- Dados do médico
    m.id_medico,
    u_m.nome as medico_nome,
    u_m.email as medico_email,
    
    -- Especialidade
    e.nome_especialidade,
    
    -- Dias em atraso (se aplicável)
    CASE 
        WHEN f.estado = 'pendente' AND f.data_pagamento IS NULL 
        THEN (CURRENT_DATE - c.data_consulta)
        ELSE 0
    END as dias_atraso,
    
    -- Valor com possível multa por atraso
    CASE 
        WHEN f.estado = 'pendente' AND f.data_pagamento IS NULL 
             AND (CURRENT_DATE - c.data_consulta) > 30
        THEN f.valor * 1.10  -- 10% de multa após 30 dias
        ELSE f.valor
    END as valor_com_multa
    
FROM "FATURAS" f
JOIN "CONSULTAS" c ON f.id_consulta = c.id_consulta
JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
JOIN "MEDICOS" m ON c.id_medico = m.id_medico
JOIN "core_utilizador" u_m ON m.id_utilizador = u_m.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade;

-- View para disponibilidades com informações úteis
CREATE OR REPLACE VIEW vw_disponibilidades AS
SELECT 
    d.id_disponibilidade,
    d.data,
    d.hora_inicio,
    d.hora_fim,
    d.duracao_slot,
    d.status_slot,
    
    -- Médico
    m.id_medico,
    u.nome as medico_nome,
    u.email as medico_email,
    m.numero_ordem,
    
    -- Especialidade
    e.id_especialidade,
    e.nome_especialidade,
    
    -- Unidade
    un.id_unidade,
    un.nome_unidade,
    un.morada_unidade,
    un.tipo_unidade,
    
    -- Região
    r.id_regiao,
    r.nome as regiao_nome,
    r.tipo_regiao,
    
    -- Slots ocupados
    (SELECT COUNT(*) 
     FROM "CONSULTAS" c 
     WHERE c.id_disponibilidade = d.id_disponibilidade 
     AND c.estado NOT IN ('cancelada')) as slots_ocupados,
    
    -- Slots disponíveis
    ((EXTRACT(EPOCH FROM (d.hora_fim - d.hora_inicio)) / 60) / d.duracao_slot) 
    - (SELECT COUNT(*) 
       FROM "CONSULTAS" c 
       WHERE c.id_disponibilidade = d.id_disponibilidade 
       AND c.estado NOT IN ('cancelada')) as slots_disponiveis

FROM "DISPONIBILIDADE" d
JOIN "MEDICOS" m ON d.id_medico = m.id_medico
JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade
JOIN "REGIAO" r ON un.id_regiao = r.id_regiao;

-- View para estatísticas de médicos (USANDO TABELAS BASE)
CREATE OR REPLACE VIEW vw_estatisticas_medicos AS
SELECT 
    m.id_medico,
    u.nome as medico_nome,
    u.email as medico_email,
    e.nome_especialidade,
    
    -- Consultas
    COUNT(DISTINCT c.id_consulta) as total_consultas,
    COUNT(DISTINCT CASE WHEN c.estado = 'realizada' THEN c.id_consulta END) as consultas_realizadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'agendada' THEN c.id_consulta END) as consultas_agendadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'confirmada' THEN c.id_consulta END) as consultas_confirmadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'cancelada' THEN c.id_consulta END) as consultas_canceladas,
    
    -- Disponibilidades
    COUNT(DISTINCT d.id_disponibilidade) as total_disponibilidades,
    COUNT(DISTINCT CASE WHEN d.status_slot IN ('available', 'disponivel') THEN d.id_disponibilidade END) as disponibilidades_disponiveis,
    COUNT(DISTINCT CASE WHEN d.status_slot = 'booked' THEN d.id_disponibilidade END) as disponibilidades_ocupadas,
    
    -- Receitas
    COUNT(DISTINCT re.id_receita) as total_receitas,
    
    -- Taxa de ocupação
    CASE 
        WHEN COUNT(DISTINCT d.id_disponibilidade) > 0 
        THEN ROUND(
            COUNT(DISTINCT CASE WHEN d.status_slot = 'booked' THEN d.id_disponibilidade END)::DECIMAL / 
            COUNT(DISTINCT d.id_disponibilidade)::DECIMAL * 100, 2
        )
        ELSE 0
    END as taxa_ocupacao_percent,
    
    -- Pacientes atendidos
    COUNT(DISTINCT c.id_paciente) as pacientes_atendidos
    
FROM "MEDICOS" m
JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "CONSULTAS" c ON m.id_medico = c.id_medico
LEFT JOIN "DISPONIBILIDADE" d ON m.id_medico = d.id_medico
LEFT JOIN "RECEITAS" re ON c.id_consulta = re.id_consulta
GROUP BY m.id_medico, u.nome, u.email, e.nome_especialidade;

-- View para dashboard administrativo
CREATE OR REPLACE VIEW vw_dashboard_admin AS
SELECT 
    -- Totais gerais
    (SELECT COUNT(*) FROM "core_utilizador") as total_utilizadores,
    (SELECT COUNT(*) FROM "core_utilizador" WHERE role = 'paciente') as total_pacientes,
    (SELECT COUNT(*) FROM "core_utilizador" WHERE role = 'medico') as total_medicos,
    (SELECT COUNT(*) FROM "core_utilizador" WHERE role = 'enfermeiro') as total_enfermeiros,
    (SELECT COUNT(*) FROM "CONSULTAS") as total_consultas,
    (SELECT COUNT(*) FROM "FATURAS") as total_faturas,
    (SELECT COUNT(*) FROM "RECEITAS") as total_receitas,
    
    -- Consultas por estado
    (SELECT COUNT(*) FROM "CONSULTAS" WHERE estado = 'agendada') as consultas_agendadas,
    (SELECT COUNT(*) FROM "CONSULTAS" WHERE estado = 'confirmada') as consultas_confirmadas,
    (SELECT COUNT(*) FROM "CONSULTAS" WHERE estado = 'realizada') as consultas_realizadas,
    (SELECT COUNT(*) FROM "CONSULTAS" WHERE estado = 'cancelada') as consultas_canceladas,
    
    -- Faturas por estado
    (SELECT COUNT(*) FROM "FATURAS" WHERE estado = 'pendente') as faturas_pendentes,
    (SELECT COUNT(*) FROM "FATURAS" WHERE estado = 'paga') as faturas_pagas,
    (SELECT COUNT(*) FROM "FATURAS" WHERE estado = 'cancelada') as faturas_canceladas,
    
    -- Valor total em faturas
    (SELECT COALESCE(SUM(valor), 0) FROM "FATURAS" WHERE estado = 'paga') as valor_total_pago,
    (SELECT COALESCE(SUM(valor), 0) FROM "FATURAS" WHERE estado = 'pendente') as valor_total_pendente,
    
    -- Consultas hoje
    (SELECT COUNT(*) FROM "CONSULTAS" WHERE data_consulta = CURRENT_DATE) as consultas_hoje,
    
    -- Consultas desta semana
    (SELECT COUNT(*) FROM "CONSULTAS" 
     WHERE data_consulta >= DATE_TRUNC('week', CURRENT_DATE) 
     AND data_consulta < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week') as consultas_semana,
    
    -- Consultas deste mês
    (SELECT COUNT(*) FROM "CONSULTAS" 
     WHERE data_consulta >= DATE_TRUNC('month', CURRENT_DATE) 
     AND data_consulta < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month') as consultas_mes;


-- View para disponibilidades com slots livres
CREATE OR REPLACE VIEW vw_disponibilidades_com_slots AS
SELECT 
    d.id_disponibilidade,
    d.id_medico,
    d.data,
    d.hora_inicio,
    d.hora_fim,
    d.duracao_slot,
    d.status_slot,
    un.nome_unidade,
    un.morada_unidade,
    -- Slots ocupados
    (SELECT COUNT(*) 
     FROM "CONSULTAS" c 
     WHERE c.id_disponibilidade = d.id_disponibilidade 
     AND c.estado NOT IN ('cancelada')) as slots_ocupados,
    -- Slots disponíveis
    ((EXTRACT(EPOCH FROM (d.hora_fim - d.hora_inicio)) / 60) / d.duracao_slot) 
    - (SELECT COUNT(*) 
       FROM "CONSULTAS" c 
       WHERE c.id_disponibilidade = d.id_disponibilidade 
       AND c.estado NOT IN ('cancelada')) as slots_disponiveis
FROM "DISPONIBILIDADE" d
JOIN "UNIDADE_DE_SAUDE" un ON d.id_unidade = un.id_unidade;

-- View para últimas consultas no dashboard admin
CREATE OR REPLACE VIEW vw_admin_ultimas_consultas AS
SELECT
    c.id_consulta,
    c.data_consulta,
    c.hora_consulta,
    c.estado,
    u_p.nome as paciente_nome,
    u_m.nome as medico_nome
FROM "CONSULTAS" c
JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
JOIN "core_utilizador" u_p ON p.id_utilizador = u_p.id_utilizador
JOIN "MEDICOS" m ON c.id_medico = m.id_medico
JOIN "core_utilizador" u_m ON m.id_utilizador = u_m.id_utilizador;

-- View para consultas com informação de fatura
CREATE OR REPLACE VIEW vw_consultas_com_fatura AS
SELECT
    c.*,
    f.id_fatura,
    f.valor AS fatura_valor,
    f.estado AS fatura_estado
FROM vw_consultas_completas c
LEFT JOIN "FATURAS" f ON f.id_consulta = c.id_consulta;