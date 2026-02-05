-- ============================================================================
-- PROCEDURES ADMIN
-- ============================================================================

-- Criar região (admin)
CREATE OR REPLACE PROCEDURE admin_criar_regiao(
	p_nome VARCHAR(50),
	p_tipo_regiao VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
	INSERT INTO "REGIAO" (nome, tipo_regiao)
	VALUES (p_nome, p_tipo_regiao);
	COMMIT;
END;
$$;

-- Editar região (admin)
CREATE OR REPLACE PROCEDURE admin_editar_regiao(
	p_id_regiao INTEGER,
	p_nome VARCHAR(50),
	p_tipo_regiao VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
	UPDATE "REGIAO"
	SET nome = p_nome,
		tipo_regiao = p_tipo_regiao
	WHERE id_regiao = p_id_regiao;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Região não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Eliminar região (admin)
CREATE OR REPLACE PROCEDURE admin_eliminar_regiao(
	p_id_regiao INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	-- Remover dependências em cascata (consultas -> faturas/receitas -> disponibilidades -> unidades)
	DELETE FROM "RECEITAS"
	WHERE id_consulta IN (
		SELECT c.id_consulta
		FROM "CONSULTAS" c
		JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
		JOIN "UNIDADE_DE_SAUDE" u ON d.id_unidade = u.id_unidade
		WHERE u.id_regiao = p_id_regiao
	);

	DELETE FROM "FATURAS"
	WHERE id_consulta IN (
		SELECT c.id_consulta
		FROM "CONSULTAS" c
		JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
		JOIN "UNIDADE_DE_SAUDE" u ON d.id_unidade = u.id_unidade
		WHERE u.id_regiao = p_id_regiao
	);

	DELETE FROM "CONSULTAS"
	WHERE id_disponibilidade IN (
		SELECT d.id_disponibilidade
		FROM "DISPONIBILIDADE" d
		JOIN "UNIDADE_DE_SAUDE" u ON d.id_unidade = u.id_unidade
		WHERE u.id_regiao = p_id_regiao
	);

	DELETE FROM "DISPONIBILIDADE"
	WHERE id_unidade IN (
		SELECT u.id_unidade
		FROM "UNIDADE_DE_SAUDE" u
		WHERE u.id_regiao = p_id_regiao
	);

	DELETE FROM "UNIDADE_DE_SAUDE"
	WHERE id_regiao = p_id_regiao;

	DELETE FROM "REGIAO"
	WHERE id_regiao = p_id_regiao;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Região não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Criar especialidade (admin)
CREATE OR REPLACE PROCEDURE admin_criar_especialidade(
	p_nome VARCHAR(255),
	p_descricao VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
	INSERT INTO "ESPECIALIDADES" (nome_especialidade, descricao)
	VALUES (p_nome, p_descricao);
	COMMIT;
END;
$$;

-- Editar especialidade (admin)
CREATE OR REPLACE PROCEDURE admin_editar_especialidade(
	p_id_especialidade INTEGER,
	p_nome VARCHAR(255),
	p_descricao VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
	UPDATE "ESPECIALIDADES"
	SET nome_especialidade = p_nome,
		descricao = p_descricao
	WHERE id_especialidade = p_id_especialidade;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Especialidade não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Eliminar especialidade (admin)
CREATE OR REPLACE PROCEDURE admin_eliminar_especialidade(
	p_id_especialidade INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	-- Desassociar médicos antes de eliminar
	UPDATE "MEDICOS"
	SET id_especialidade = NULL
	WHERE id_especialidade = p_id_especialidade;

	DELETE FROM "ESPECIALIDADES"
	WHERE id_especialidade = p_id_especialidade;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Especialidade não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Criar unidade (admin)
CREATE OR REPLACE PROCEDURE admin_criar_unidade(
	p_nome VARCHAR(255),
	p_morada VARCHAR(255),
	p_tipo VARCHAR(255),
	p_id_regiao INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	INSERT INTO "UNIDADE_DE_SAUDE" (nome_unidade, morada_unidade, tipo_unidade, id_regiao)
	VALUES (p_nome, p_morada, p_tipo, p_id_regiao);
	COMMIT;
END;
$$;

-- Editar unidade (admin)
CREATE OR REPLACE PROCEDURE admin_editar_unidade(
	p_id_unidade INTEGER,
	p_nome VARCHAR(255),
	p_morada VARCHAR(255),
	p_tipo VARCHAR(255),
	p_id_regiao INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	UPDATE "UNIDADE_DE_SAUDE"
	SET nome_unidade = p_nome,
		morada_unidade = p_morada,
		tipo_unidade = p_tipo,
		id_regiao = p_id_regiao
	WHERE id_unidade = p_id_unidade;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Unidade não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Eliminar unidade (admin)
CREATE OR REPLACE PROCEDURE admin_eliminar_unidade(
	p_id_unidade INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	-- Remover dependências em cascata (consultas -> faturas/receitas -> disponibilidades)
	DELETE FROM "RECEITAS"
	WHERE id_consulta IN (
		SELECT c.id_consulta
		FROM "CONSULTAS" c
		JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
		WHERE d.id_unidade = p_id_unidade
	);

	DELETE FROM "FATURAS"
	WHERE id_consulta IN (
		SELECT c.id_consulta
		FROM "CONSULTAS" c
		JOIN "DISPONIBILIDADE" d ON c.id_disponibilidade = d.id_disponibilidade
		WHERE d.id_unidade = p_id_unidade
	);

	DELETE FROM "CONSULTAS"
	WHERE id_disponibilidade IN (
		SELECT d.id_disponibilidade
		FROM "DISPONIBILIDADE" d
		WHERE d.id_unidade = p_id_unidade
	);

	DELETE FROM "DISPONIBILIDADE"
	WHERE id_unidade = p_id_unidade;

	DELETE FROM "UNIDADE_DE_SAUDE"
	WHERE id_unidade = p_id_unidade;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Unidade não encontrada';
	END IF;
	COMMIT;
END;
$$;

-- Criar utilizador (admin)
CREATE OR REPLACE PROCEDURE admin_criar_utilizador(
	p_nome VARCHAR(255),
	p_email VARCHAR(255),
	p_telefone VARCHAR(20),
	p_role VARCHAR(20),
	p_password_hash VARCHAR(255),
	p_numero_ordem VARCHAR(50) DEFAULT NULL,
	p_id_especialidade INTEGER DEFAULT NULL,
	p_n_ordem_enf VARCHAR(50) DEFAULT NULL,
	p_data_nasc DATE DEFAULT NULL,
	p_genero VARCHAR(50) DEFAULT NULL,
	p_morada VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
	v_id_utilizador INTEGER;
	v_n_utente VARCHAR(20);
BEGIN
	IF EXISTS (SELECT 1 FROM "core_utilizador" WHERE email = p_email) THEN
		RAISE EXCEPTION 'Já existe um utilizador com este email';
	END IF;

	SELECT gerar_n_utente() INTO v_n_utente;

	INSERT INTO "core_utilizador" (
		nome, email, telefone, n_utente, password, role,
		data_registo, ativo, is_superuser,
		email_verified, verification_token, reset_token, reset_token_expires
	) VALUES (
		p_nome,
		p_email,
		NULLIF(p_telefone, ''),
		v_n_utente,
		p_password_hash,
		p_role,
		NOW(),
		TRUE,
		FALSE,
		FALSE,
		NULL,
		NULL,
		NULL
	)
	RETURNING id_utilizador INTO v_id_utilizador;

	IF p_role = 'medico' THEN
		INSERT INTO "MEDICOS" (id_utilizador, numero_ordem, id_especialidade)
		VALUES (v_id_utilizador, COALESCE(p_numero_ordem, ''), p_id_especialidade);
	ELSIF p_role = 'enfermeiro' THEN
		INSERT INTO "ENFERMEIRO" (id_utilizador, n_ordem_enf)
		VALUES (v_id_utilizador, COALESCE(p_n_ordem_enf, ''));
	ELSIF p_role = 'paciente' THEN
		IF p_data_nasc IS NULL OR p_genero IS NULL OR p_genero = '' THEN
			RAISE EXCEPTION 'Dados do paciente incompletos';
		END IF;
		INSERT INTO "PACIENTES" (id_utilizador, data_nasc, genero, morada, alergias, observacoes)
		VALUES (v_id_utilizador, p_data_nasc, p_genero, COALESCE(p_morada, ''), '', '');
	END IF;

	COMMIT;
END;
$$;

-- Editar utilizador (admin)
CREATE OR REPLACE PROCEDURE admin_editar_utilizador(
	p_id_utilizador INTEGER,
	p_nome VARCHAR(255),
	p_email VARCHAR(255),
	p_telefone VARCHAR(20),
	p_ativo BOOLEAN,
	p_password_hash VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
	IF EXISTS (
		SELECT 1 FROM "core_utilizador"
		WHERE email = p_email AND id_utilizador <> p_id_utilizador
	) THEN
		RAISE EXCEPTION 'Já existe um utilizador com este email';
	END IF;

	IF p_password_hash IS NULL OR p_password_hash = '' THEN
		UPDATE "core_utilizador"
		SET nome = p_nome,
			email = p_email,
			telefone = NULLIF(p_telefone, ''),
			ativo = p_ativo
		WHERE id_utilizador = p_id_utilizador;
	ELSE
		UPDATE "core_utilizador"
		SET nome = p_nome,
			email = p_email,
			telefone = NULLIF(p_telefone, ''),
			ativo = p_ativo,
			password = p_password_hash
		WHERE id_utilizador = p_id_utilizador;
	END IF;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Utilizador não encontrado';
	END IF;

	COMMIT;
END;
$$;

-- Ativar/Desativar utilizador (admin)
CREATE OR REPLACE PROCEDURE admin_toggle_utilizador_ativo(
	p_id_utilizador INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
	UPDATE "core_utilizador"
	SET ativo = NOT ativo
	WHERE id_utilizador = p_id_utilizador;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Utilizador não encontrado';
	END IF;

	COMMIT;
END;
$$;

-- Criar fatura (admin)
CREATE OR REPLACE PROCEDURE admin_criar_fatura(
	p_id_consulta INTEGER,
	p_valor NUMERIC,
	p_metodo_pagamento VARCHAR(50) DEFAULT 'pendente'
)
LANGUAGE plpgsql
AS $$
BEGIN
	IF EXISTS (SELECT 1 FROM "FATURAS" WHERE id_consulta = p_id_consulta) THEN
		RAISE EXCEPTION 'Esta consulta já tem uma fatura associada';
	END IF;

	INSERT INTO "FATURAS" (id_consulta, valor, metodo_pagamento, estado, data_pagamento)
	VALUES (p_id_consulta, p_valor, p_metodo_pagamento, 'pendente', NULL);

	COMMIT;
END;
$$;

-- Editar fatura (admin)
CREATE OR REPLACE PROCEDURE admin_editar_fatura(
	p_id_fatura INTEGER,
	p_valor NUMERIC,
	p_metodo_pagamento VARCHAR(50),
	p_estado VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
	UPDATE "FATURAS"
	SET valor = p_valor,
		metodo_pagamento = p_metodo_pagamento,
		estado = p_estado,
		data_pagamento = CASE
			WHEN p_estado = 'paga' AND data_pagamento IS NULL THEN CURRENT_DATE
			ELSE data_pagamento
		END
	WHERE id_fatura = p_id_fatura;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'Fatura não encontrada';
	END IF;

	COMMIT;
END;
$$;
