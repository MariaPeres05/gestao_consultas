-- View detalhada de consultas
CREATE OR REPLACE VIEW vw_consultas_detalhadas AS
SELECT 
    c.id_consulta,
    c.data_consulta,
    c.hora_consulta,
    c.estado,
    c.motivo,
    
    -- Paciente
    p.id_paciente,
    u_p.nome as paciente_nome,
    u_p.email as paciente_email,
    u_p.telefone as paciente_telefone,
    u_p.n_utente as paciente_n_utente,
    p.data_nasc as paciente_data_nasc,
    p.genero as paciente_genero,
    
    -- Médico
    m.id_medico,
    u_m.nome as medico_nome,
    u_m.email as medico_email,
    m.numero_ordem as medico_numero_ordem,
    e.nome_especialidade as especialidade,
    
    -- Unidade
    d.id_unidade,
    us.nome_unidade as unidade_nome,
    us.tipo_unidade,
    
    -- Fatura
    f.valor as fatura_valor,
    f.estado as fatura_estado,
    f.data_pagamento as fatura_data_pagamento,
    
    -- Check-in
    c.paciente_presente,
    c.hora_checkin,
    
    -- Audit trail
    c.criado_em,
    c.modificado_em
    
FROM "CONSULTAS" c
LEFT JOIN "PACIENTES" p ON c.id_paciente = p.id_paciente
LEFT JOIN "UTILIZADOR" u_p ON p.id_utilizador = u_p.id_utilizador
LEFT JOIN "MEDICOS" m ON c.id_medico = m.id_medico
LEFT JOIN "UTILIZADOR" u_m ON m.id_utilizador = u_m.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
LEFT JOIN "UNIDADE_DE_SAUDE" us ON d.id_unidade = us.id_unidade
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta;

-- View de disponibilidade dos médicos
CREATE OR REPLACE VIEW vw_medico_disponibilidade AS
SELECT 
    m.id_medico,
    u.nome as medico_nome,
    e.nome_especialidade as especialidade,
    
    -- Total de horas disponíveis (últimos 30 dias)
    COALESCE(SUM(EXTRACT(EPOCH FROM (d.hora_fim - d.hora_inicio))/3600), 0)::INTEGER as total_horas_disponiveis,
    
    -- Slots disponíveis
    COUNT(DISTINCT d.id_disponibilidade) as total_slots_disponiveis,
    
    -- Slots ocupados
    COUNT(DISTINCT c.id_consulta) as slots_ocupados,
    
    -- Taxa de ocupação
    CASE 
        WHEN COUNT(DISTINCT d.id_disponibilidade) > 0 
        THEN ROUND((COUNT(DISTINCT c.id_consulta)::DECIMAL / COUNT(DISTINCT d.id_disponibilidade)::DECIMAL) * 100, 2)
        ELSE 0 
    END as taxa_ocupacao,
    
    -- Próxima disponibilidade
    MIN(d.data) as proxima_disponibilidade
    
FROM "MEDICOS" m
JOIN "UTILIZADOR" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "DISPONIBILIDADE" d ON m.id_medico = d.id_medico 
    AND d.data >= CURRENT_DATE 
    AND d.status_slot = 'disponivel'
LEFT JOIN "CONSULTAS" c ON d.id_disponibilidade = c.id_disponibilidade 
    AND c.estado IN ('agendada', 'confirmada')
GROUP BY m.id_medico, u.nome, e.nome_especialidade;

-- View de histórico do paciente
CREATE OR REPLACE VIEW vw_paciente_historico AS
SELECT 
    p.id_paciente,
    u.nome as paciente_nome,
    u.email,
    u.telefone,
    u.n_utente,
    p.data_nasc,
    p.genero,
    p.morada,
    
    -- Estatísticas de consultas
    COUNT(c.id_consulta) as total_consultas,
    SUM(CASE WHEN c.estado = 'realizada' THEN 1 ELSE 0 END) as consultas_realizadas,
    SUM(CASE WHEN c.estado IN ('agendada', 'confirmada') THEN 1 ELSE 0 END) as consultas_agendadas,
    SUM(CASE WHEN c.estado = 'cancelada' THEN 1 ELSE 0 END) as consultas_canceladas,
    
    -- Datas importantes
    MAX(c.data_consulta) as ultima_consulta,
    MIN(CASE WHEN c.estado IN ('agendada', 'confirmada') AND c.data_consulta >= CURRENT_DATE THEN c.data_consulta END) as proxima_consulta,
    
    -- Valor gasto
    SUM(COALESCE(f.valor, 0)) as valor_total_gasto,
    
    -- Diversidade
    COUNT(DISTINCT c.id_medico) as medicos_diferentes,
    COUNT(DISTINCT m.id_especialidade) as especialidades_diferentes
    
FROM "PACIENTES" p
JOIN "UTILIZADOR" u ON p.id_utilizador = u.id_utilizador
LEFT JOIN "CONSULTAS" c ON p.id_paciente = c.id_paciente
LEFT JOIN "MEDICOS" m ON c.id_medico = m.id_medico
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta AND f.estado = 'paga'
GROUP BY p.id_paciente, u.nome, u.email, u.telefone, u.n_utente, p.data_nasc, p.genero, p.morada;

