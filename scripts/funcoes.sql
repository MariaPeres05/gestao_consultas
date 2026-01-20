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

SELECT gerar_n_utente();

SELECT validar_horario_disponibilidade(
    '2024-12-20',  -- data
    '10:00',       -- hora_inicio  
    '10:30',       -- hora_fim
    1              -- id_medico 
);