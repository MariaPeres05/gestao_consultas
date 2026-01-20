-- Materialized View para dashboard do médico
CREATE MATERIALIZED VIEW mv_dashboard_medico AS
SELECT 
    m.id_medico,
    u.nome as medico_nome,
    e.nome_especialidade as especialidade,
    
    -- Consultas hoje
    COUNT(CASE WHEN c.data_consulta = CURRENT_DATE THEN c.id_consulta END) as consultas_hoje,
    COUNT(DISTINCT CASE WHEN c.data_consulta = CURRENT_DATE THEN c.id_paciente END) as pacientes_hoje,
    
    -- Semana (últimos 7 dias)
    COUNT(CASE WHEN c.data_consulta >= CURRENT_DATE - INTERVAL '7 days' 
                AND c.data_consulta <= CURRENT_DATE THEN c.id_consulta END) as consultas_semana,
    
    -- Receita da semana
    SUM(CASE WHEN c.data_consulta >= CURRENT_DATE - INTERVAL '7 days' 
              AND c.data_consulta <= CURRENT_DATE 
              AND f.estado = 'paga' THEN f.valor ELSE 0 END) as receita_semana,
    
    -- Mês atual
    COUNT(CASE WHEN EXTRACT(MONTH FROM c.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE) 
                AND EXTRACT(YEAR FROM c.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE) 
                THEN c.id_consulta END) as consultas_mes,
    
    -- Receita do mês
    SUM(CASE WHEN EXTRACT(MONTH FROM c.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE) 
              AND EXTRACT(YEAR FROM c.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE) 
              AND f.estado = 'paga' THEN f.valor ELSE 0 END) as receita_mes,
    
    -- Pedidos pendentes
    COUNT(CASE WHEN c.estado = 'agendada' THEN c.id_consulta END) as pedidos_pendentes,
    
    -- Próximos 7 dias
    COUNT(CASE WHEN c.data_consulta BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' 
                AND c.estado IN ('agendada', 'confirmada') 
                THEN c.id_consulta END) as consultas_proximos_7_dias,
    
    -- Taxa de cancelamento
    CASE 
        WHEN COUNT(c.id_consulta) > 0 
        THEN ROUND((COUNT(CASE WHEN c.estado = 'cancelada' THEN 1 END)::DECIMAL / COUNT(c.id_consulta)::DECIMAL) * 100, 2)
        ELSE 0 
    END as taxa_cancelamento,
    
    CURRENT_TIMESTAMP as data_atualizacao
    
FROM "MEDICOS" m
JOIN "UTILIZADOR" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "CONSULTAS" c ON m.id_medico = c.id_medico
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta
GROUP BY m.id_medico, u.nome, e.nome_especialidade

WITH DATA;

-- Índices para melhor performance
CREATE UNIQUE INDEX idx_mv_dashboard_medico_id ON mv_dashboard_medico (id_medico);

-- Materialized View para dashboard administrativo
CREATE MATERIALIZED VIEW mv_dashboard_admin AS
SELECT 
    -- Totais
    (SELECT COUNT(*) FROM "PACIENTES") as total_pacientes,
    (SELECT COUNT(*) FROM "MEDICOS") as total_medicos,
    (SELECT COUNT(*) FROM "ENFERMEIRO") as total_enfermeiros,
    (SELECT COUNT(*) FROM "UNIDADE_DE_SAUDE") as total_unidades,
    
    -- Consultas
    COUNT(CASE WHEN c.data_consulta = CURRENT_DATE THEN c.id_consulta END) as consultas_hoje,
    COUNT(CASE WHEN EXTRACT(MONTH FROM c.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE) 
                AND EXTRACT(YEAR FROM c.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE) 
                THEN c.id_consulta END) as consultas_mes,
    COUNT(CASE WHEN c.estado = 'agendada' THEN c.id_consulta END) as consultas_pendentes,
    
    -- Faturamento
    COUNT(CASE WHEN f.estado = 'pendente' THEN f.id_fatura END) as faturas_pendentes,
    SUM(CASE WHEN EXTRACT(MONTH FROM f.data_pagamento) = EXTRACT(MONTH FROM CURRENT_DATE) 
              AND EXTRACT(YEAR FROM f.data_pagamento) = EXTRACT(YEAR FROM CURRENT_DATE) 
              AND f.estado = 'paga' THEN f.valor ELSE 0 END) as receita_mes,
    SUM(CASE WHEN EXTRACT(YEAR FROM f.data_pagamento) = EXTRACT(YEAR FROM CURRENT_DATE) 
              AND f.estado = 'paga' THEN f.valor ELSE 0 END) as receita_anual,
    
    -- Região mais ativa
    (SELECT r.nome 
     FROM "REGIAO" r
     JOIN "UNIDADE_DE_SAUDE" us ON r.id_regiao = us.id_regiao
     JOIN "CONSULTAS" c2 ON c2.id_disponibilidade IN (
         SELECT d2.id_disponibilidade 
         FROM "DISPONIBILIDADE" d2 
         WHERE d2.id_unidade = us.id_unidade
     )
     GROUP BY r.nome 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) as regiao_mais_ativa,
    
    -- Unidade mais ativa
    (SELECT us.nome_unidade 
     FROM "UNIDADE_DE_SAUDE" us
     JOIN "CONSULTAS" c2 ON c2.id_disponibilidade IN (
         SELECT d2.id_disponibilidade 
         FROM "DISPONIBILIDADE" d2 
         WHERE d2.id_unidade = us.id_unidade
     )
     GROUP BY us.nome_unidade 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) as unidade_mais_ativa,
    
    -- Tendências
    -- Crescimento de pacientes (mês atual vs mês anterior)
    ((SELECT COUNT(*) 
      FROM "PACIENTES" p2 
      JOIN "UTILIZADOR" u2 ON p2.id_utilizador = u2.id_utilizador
      WHERE EXTRACT(MONTH FROM u2.data_registo) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM u2.data_registo) = EXTRACT(YEAR FROM CURRENT_DATE)) * 100.0 /
     NULLIF((SELECT COUNT(*) 
             FROM "PACIENTES" p2 
             JOIN "UTILIZADOR" u2 ON p2.id_utilizador = u2.id_utilizador
             WHERE EXTRACT(MONTH FROM u2.data_registo) = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
               AND EXTRACT(YEAR FROM u2.data_registo) = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')), 0)) as crescimento_pacientes_mes,
    
    -- Crescimento de consultas
    ((SELECT COUNT(*) 
      FROM "CONSULTAS" c2 
      WHERE EXTRACT(MONTH FROM c2.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM c2.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE)) * 100.0 /
     NULLIF((SELECT COUNT(*) 
             FROM "CONSULTAS" c2 
             WHERE EXTRACT(MONTH FROM c2.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
               AND EXTRACT(YEAR FROM c2.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')), 0)) as crescimento_consultas_mes,
    
    CURRENT_TIMESTAMP as data_atualizacao
    
FROM "CONSULTAS" c
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta

WITH DATA;

-- Materialized View dos médicos mais solicitados
CREATE MATERIALIZED VIEW mv_top_medicos AS
SELECT 
    m.id_medico,
    u.nome as medico_nome,
    e.nome_especialidade as especialidade,
    
    -- Estatísticas totais
    COUNT(c.id_consulta) as total_consultas,
    
    -- Este mês
    COUNT(CASE WHEN EXTRACT(MONTH FROM c.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE) 
                AND EXTRACT(YEAR FROM c.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE) 
                THEN c.id_consulta END) as consultas_mes,
    
    -- Taxa de ocupação
    CASE 
        WHEN COUNT(DISTINCT d.id_disponibilidade) > 0 
        THEN ROUND((COUNT(DISTINCT c.id_consulta)::DECIMAL / COUNT(DISTINCT d.id_disponibilidade)::DECIMAL) * 100, 2)
        ELSE 0 
    END as taxa_ocupacao,
    
    -- Avaliação (exemplo - se implementar sistema de avaliação)
    4.5 as avaliacao_media,  -- Placeholder
    10 as total_avaliacoes,  -- Placeholder
    
    -- Faturamento
    SUM(COALESCE(f.valor, 0)) as receita_total,
    SUM(CASE WHEN EXTRACT(MONTH FROM c.data_consulta) = EXTRACT(MONTH FROM CURRENT_DATE) 
              AND EXTRACT(YEAR FROM c.data_consulta) = EXTRACT(YEAR FROM CURRENT_DATE) 
              THEN COALESCE(f.valor, 0) ELSE 0 END) as receita_mes,
    
    -- Ranking
    ROW_NUMBER() OVER (ORDER BY COUNT(c.id_consulta) DESC) as ranking,
    
    -- Período
    EXTRACT(MONTH FROM CURRENT_DATE) as mes,
    EXTRACT(YEAR FROM CURRENT_DATE) as ano
    
FROM "MEDICOS" m
JOIN "UTILIZADOR" u ON m.id_utilizador = u.id_utilizador
LEFT JOIN "ESPECIALIDADES" e ON m.id_especialidade = e.id_especialidade
LEFT JOIN "CONSULTAS" c ON m.id_medico = c.id_medico AND c.estado != 'cancelada'
LEFT JOIN "FATURAS" f ON c.id_consulta = f.id_consulta
LEFT JOIN "DISPONIBILIDADE" d ON m.id_medico = d.id_medico
GROUP BY m.id_medico, u.nome, e.nome_especialidade
HAVING COUNT(c.id_consulta) > 0

WITH DATA;

CREATE UNIQUE INDEX idx_mv_top_medicos_id ON mv_top_medicos (id_medico);