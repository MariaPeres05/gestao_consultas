-- ============================================================================
-- DDL TABLES (Schema base sem ORM)
-- ============================================================================

-- Utilizador (core_utilizador)
CREATE TABLE IF NOT EXISTS "core_utilizador" (
    id_utilizador SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    telefone VARCHAR(20) NULL,
    n_utente VARCHAR(20) NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'paciente',
    data_registo TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    foto_perfil TEXT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token VARCHAR(100) NULL,
    reset_token VARCHAR(100) NULL,
    reset_token_expires TIMESTAMPTZ NULL,
    CONSTRAINT chk_role_utilizador CHECK (role IN ('paciente','medico','enfermeiro','admin'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_core_utilizador_n_utente
    ON "core_utilizador"(n_utente)
    WHERE n_utente IS NOT NULL;

-- Regiao
CREATE TABLE IF NOT EXISTS "REGIAO" (
    id_regiao SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    tipo_regiao VARCHAR(50) NOT NULL
);

-- Unidade de Saude
CREATE TABLE IF NOT EXISTS "UNIDADE_DE_SAUDE" (
    id_unidade SERIAL PRIMARY KEY,
    id_regiao INTEGER NOT NULL,
    nome_unidade VARCHAR(255) NOT NULL,
    morada_unidade VARCHAR(255) NOT NULL,
    tipo_unidade VARCHAR(255) NOT NULL,
    CONSTRAINT fk_unidade_regiao
        FOREIGN KEY (id_regiao) REFERENCES "REGIAO"(id_regiao)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Especialidades
CREATE TABLE IF NOT EXISTS "ESPECIALIDADES" (
    id_especialidade SERIAL PRIMARY KEY,
    nome_especialidade VARCHAR(255) NOT NULL UNIQUE,
    descricao VARCHAR(255) NULL
);

-- Medicos
CREATE TABLE IF NOT EXISTS "MEDICOS" (
    id_medico SERIAL PRIMARY KEY,
    id_utilizador INTEGER NOT NULL UNIQUE,
    numero_ordem VARCHAR(50) NOT NULL,
    id_especialidade INTEGER NULL,
    CONSTRAINT fk_medico_utilizador
        FOREIGN KEY (id_utilizador) REFERENCES "core_utilizador"(id_utilizador)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_medico_especialidade
        FOREIGN KEY (id_especialidade) REFERENCES "ESPECIALIDADES"(id_especialidade)
        ON UPDATE CASCADE ON DELETE SET NULL
);

-- Enfermeiro
CREATE TABLE IF NOT EXISTS "ENFERMEIRO" (
    id_enfermeiro SERIAL PRIMARY KEY,
    id_utilizador INTEGER NOT NULL UNIQUE,
    n_ordem_enf VARCHAR(50) NOT NULL,
    CONSTRAINT fk_enfermeiro_utilizador
        FOREIGN KEY (id_utilizador) REFERENCES "core_utilizador"(id_utilizador)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Pacientes
CREATE TABLE IF NOT EXISTS "PACIENTES" (
    id_paciente SERIAL PRIMARY KEY,
    id_utilizador INTEGER NOT NULL UNIQUE,
    data_nasc DATE NOT NULL,
    genero VARCHAR(50) NOT NULL,
    morada VARCHAR(255) NULL,
    alergias VARCHAR(255) NULL,
    observacoes VARCHAR(255) NULL,
    CONSTRAINT fk_paciente_utilizador
        FOREIGN KEY (id_utilizador) REFERENCES "core_utilizador"(id_utilizador)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Disponibilidade
CREATE TABLE IF NOT EXISTS "DISPONIBILIDADE" (
    id_disponibilidade SERIAL PRIMARY KEY,
    id_medico INTEGER NOT NULL,
    id_unidade INTEGER NOT NULL,
    data DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    duracao_slot INTEGER NOT NULL,
    status_slot VARCHAR(20) NOT NULL,
    CONSTRAINT fk_disp_medico
        FOREIGN KEY (id_medico) REFERENCES "MEDICOS"(id_medico)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_disp_unidade
        FOREIGN KEY (id_unidade) REFERENCES "UNIDADE_DE_SAUDE"(id_unidade)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Consultas
CREATE TABLE IF NOT EXISTS "CONSULTAS" (
    id_consulta SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NULL,
    id_disponibilidade INTEGER NULL,
    data_consulta DATE NOT NULL,
    hora_consulta TIME NOT NULL,
    estado VARCHAR(50) NOT NULL,
    motivo VARCHAR(255) NULL,
    medico_aceitou BOOLEAN NOT NULL DEFAULT FALSE,
    paciente_aceitou BOOLEAN NOT NULL DEFAULT FALSE,
    notas_clinicas TEXT NULL,
    observacoes TEXT NULL,
    paciente_presente BOOLEAN NOT NULL DEFAULT FALSE,
    hora_checkin TIMESTAMPTZ NULL,
    hora_inicio_real TIMESTAMPTZ NULL,
    hora_fim_real TIMESTAMPTZ NULL,
    criado_por INTEGER NULL,
    criado_em TIMESTAMPTZ NULL DEFAULT NOW(),
    modificado_por INTEGER NULL,
    modificado_em TIMESTAMPTZ NULL,
    CONSTRAINT fk_consulta_paciente
        FOREIGN KEY (id_paciente) REFERENCES "PACIENTES"(id_paciente)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_consulta_medico
        FOREIGN KEY (id_medico) REFERENCES "MEDICOS"(id_medico)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_consulta_disponibilidade
        FOREIGN KEY (id_disponibilidade) REFERENCES "DISPONIBILIDADE"(id_disponibilidade)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_consulta_criado_por
        FOREIGN KEY (criado_por) REFERENCES "core_utilizador"(id_utilizador)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_consulta_modificado_por
        FOREIGN KEY (modificado_por) REFERENCES "core_utilizador"(id_utilizador)
        ON UPDATE CASCADE ON DELETE SET NULL
);

-- Faturas
CREATE TABLE IF NOT EXISTS "FATURAS" (
    id_fatura SERIAL PRIMARY KEY,
    id_consulta INTEGER NOT NULL UNIQUE,
    valor NUMERIC(10,2) NOT NULL,
    metodo_pagamento VARCHAR(50) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    data_pagamento DATE NULL,
    CONSTRAINT fk_fatura_consulta
        FOREIGN KEY (id_consulta) REFERENCES "CONSULTAS"(id_consulta)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Receitas
CREATE TABLE IF NOT EXISTS "RECEITAS" (
    id_receita SERIAL PRIMARY KEY,
    id_consulta INTEGER NOT NULL,
    medicamento VARCHAR(255) NOT NULL,
    dosagem VARCHAR(255) NOT NULL,
    instrucoes VARCHAR(255) NULL,
    data_prescricao DATE NOT NULL,
    CONSTRAINT fk_receita_consulta
        FOREIGN KEY (id_consulta) REFERENCES "CONSULTAS"(id_consulta)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_consultas_data_estado ON "CONSULTAS"(data_consulta, estado);
CREATE INDEX IF NOT EXISTS idx_disponibilidade_data ON "DISPONIBILIDADE"(data);
CREATE INDEX IF NOT EXISTS idx_faturas_estado ON "FATURAS"(estado);