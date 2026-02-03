-- ============================================================================
-- MATERIALIZED VIEWS DO SISTEMA 
-- ============================================================================

-- Materialized View para estatísticas mensais (atualizada diariamente)
CREATE MATERIALIZED VIEW mv_estatisticas_mensais AS
SELECT 
    DATE_TRUNC('month', c.data_consulta) as mes,
    EXTRACT(YEAR FROM c.data_consulta) as ano,
    EXTRACT(MONTH FROM c.data_consulta) as mes_numero,
    
    -- Consultas
    COUNT(DISTINCT c.id_consulta) as total_consultas,
    COUNT(DISTINCT CASE WHEN c.estado = 'realizada' THEN c.id_consulta END) as consultas_realizadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'agendada' THEN c.id_consulta END) as consultas_agendadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'cancelada' THEN c.id_consulta END) as consultas_canceladas,
    
    -- Faturas
    COUNT(DISTINCT f.id_fatura) as total_faturas,
    SUM(CASE WHEN f.estado = 'paga' THEN f.valor ELSE 0 END) as valor_total_pago,
    SUM(CASE WHEN f.estado = 'pendente' THEN f.valor ELSE 0 END) as valor_total_pendente,
    
    -- Médicos
    COUNT(DISTINCT c.id_medico) as medicos_ativos,
    
    -- Pacientes
    COUNT(DISTINCT c.id_paciente) as pacientes_atendidos,
    
    -- Especialidades mais requisitadas
    MODE() WITHIN GROUP (ORDER BY e.nome_especialidade) as especialidade_mais_requisitada
    
FROM "CONSULTAS" c
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta
LEFT JOIN "MEDICOS" m ON c.id_medico = m.id_medico
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
WHERE c.data_consulta >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', c.data_consulta), 
         EXTRACT(YEAR FROM c.data_consulta), 
         EXTRACT(MONTH FROM c.data_consulta)
ORDER BY mes DESC;

-- Índice para performance
CREATE UNIQUE INDEX idx_mv_estatisticas_mensais_mes ON mv_estatisticas_mensais(mes);

-- Materialized View para ranking de médicos (atualizada semanalmente)
CREATE MATERIALIZED VIEW mv_ranking_medicos AS
SELECT 
    m.id_medico,
    u.nome as medico_nome,
    e.nome_especialidade,
    
    -- Estatísticas
    COUNT(DISTINCT c.id_consulta) as total_consultas,
    COUNT(DISTINCT CASE WHEN c.estado = 'realizada' THEN c.id_consulta END) as consultas_realizadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'cancelada' THEN c.id_consulta END) as consultas_canceladas,
    
    -- Taxa de cancelamento
    CASE 
        WHEN COUNT(DISTINCT c.id_consulta) > 0 
        THEN ROUND(
            COUNT(DISTINCT CASE WHEN c.estado = 'cancelada' THEN c.id_consulta END)::DECIMAL / 
            COUNT(DISTINCT c.id_consulta)::DECIMAL * 100, 2
        )
        ELSE 0
    END as taxa_cancelamento_percent,
    
    -- Disponibilidade
    COUNT(DISTINCT d.id_disponibilidade) as total_disponibilidades,
    COUNT(DISTINCT CASE WHEN d.status_slot = 'available' THEN d.id_disponibilidade END) as disponibilidades_disponiveis,
    
    -- Avaliação (temporariamente zero)
    0 as media_avaliacao,
    
    -- Total receitas prescritas
    COUNT(DISTINCT r.id_receita) as total_receitas_prescritas

FROM "MEDICOS" m
JOIN "core_utilizador" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "CONSULTAS" c ON m.id_medico = c.id_medico
LEFT JOIN "DISPONIBILIDADE" d ON m.id_medico = d.id_medico
LEFT JOIN "RECEITAS" r ON c.id_consulta = r.id_consulta
WHERE (c.data_consulta >= CURRENT_DATE - INTERVAL '6 months' OR c.data_consulta IS NULL)
   OR (d.data >= CURRENT_DATE - INTERVAL '6 months' OR d.data IS NULL)
GROUP BY m.id_medico, u.nome, e.nome_especialidade
ORDER BY consultas_realizadas DESC NULLS LAST, media_avaliacao DESC;

-- Índices para performance
CREATE UNIQUE INDEX idx_mv_ranking_medicos_id ON mv_ranking_medicos(id_medico);
CREATE INDEX idx_mv_ranking_medicos_consultas ON mv_ranking_medicos(consultas_realizadas);

-- Função para atualizar materialized views
CREATE OR REPLACE FUNCTION atualizar_matviews()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_estatisticas_mensais;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ranking_medicos;
END;
$$ LANGUAGE plpgsql;