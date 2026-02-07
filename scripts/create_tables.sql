-- ============================================================================
-- Script de Criação de Tabelas - Sistema de Gestão de Consultas
-- Gerado em: 2026-02-06
-- Base de Dados: PostgreSQL
-- ============================================================================

-- Limpar tabelas existentes
-- DROP TABLE IF EXISTS "RECEITAS" CASCADE;
-- DROP TABLE IF EXISTS "FATURAS" CASCADE;
-- DROP TABLE IF EXISTS "CONSULTAS" CASCADE;
-- DROP TABLE IF EXISTS "DISPONIBILIDADE" CASCADE;
-- DROP TABLE IF EXISTS "PACIENTES" CASCADE;
-- DROP TABLE IF EXISTS "ENFERMEIRO" CASCADE;
-- DROP TABLE IF EXISTS "MEDICOS" CASCADE;
-- DROP TABLE IF EXISTS "ESPECIALIDADES" CASCADE;
-- DROP TABLE IF EXISTS "UNIDADE_DE_SAUDE" CASCADE;
-- DROP TABLE IF EXISTS "REGIAO" CASCADE;
-- DROP TABLE IF EXISTS "core_utilizador" CASCADE;
-- DROP TABLE IF EXISTS "core_utilizador_groups" CASCADE;
-- DROP TABLE IF EXISTS "core_utilizador_user_permissions" CASCADE;

-- ============================================================================
-- TABELA: core_utilizador (Utilizadores do Sistema)
-- ============================================================================
CREATE TABLE IF NOT EXISTS "core_utilizador" (
    "id_utilizador" SERIAL PRIMARY KEY,
    "password" VARCHAR(128) NOT NULL,
    "last_login" TIMESTAMP WITH TIME ZONE NULL,
    "is_superuser" BOOLEAN NOT NULL DEFAULT FALSE,
    "nome" VARCHAR(255) NOT NULL,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "telefone" VARCHAR(20) NULL,
    "n_utente" VARCHAR(20) NULL,
    "role" VARCHAR(20) NOT NULL DEFAULT 'paciente',
    "data_registo" TIMESTAMP WITH TIME ZONE NOT NULL,
    "ativo" BOOLEAN NOT NULL DEFAULT TRUE,
    "foto_perfil" TEXT NULL,
    "email_verified" BOOLEAN NOT NULL DEFAULT FALSE,
    "verification_token" VARCHAR(100) NULL,
    "reset_token" VARCHAR(100) NULL,
    "reset_token_expires" TIMESTAMP WITH TIME ZONE NULL,
    
    CONSTRAINT "core_utilizador_role_check" CHECK (
        "role" IN ('paciente', 'medico', 'enfermeiro', 'admin')
    )
);

CREATE INDEX IF NOT EXISTS "core_utilizador_email_idx" ON "core_utilizador" ("email");
CREATE INDEX IF NOT EXISTS "core_utilizador_role_idx" ON "core_utilizador" ("role");
CREATE INDEX IF NOT EXISTS "core_utilizador_n_utente_idx" ON "core_utilizador" ("n_utente");

-- ============================================================================
-- TABELAS: Grupos e Permissões (Django)
-- ============================================================================
CREATE TABLE IF NOT EXISTS "core_utilizador_groups" (
    "id" SERIAL PRIMARY KEY,
    "utilizador_id" INTEGER NOT NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE CASCADE,
    "group_id" INTEGER NOT NULL,
    UNIQUE ("utilizador_id", "group_id")
);

CREATE TABLE IF NOT EXISTS "core_utilizador_user_permissions" (
    "id" SERIAL PRIMARY KEY,
    "utilizador_id" INTEGER NOT NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE CASCADE,
    "permission_id" INTEGER NOT NULL,
    UNIQUE ("utilizador_id", "permission_id")
);

-- ============================================================================
-- TABELA: REGIAO
-- ============================================================================
CREATE TABLE IF NOT EXISTS "REGIAO" (
    "id_regiao" SERIAL PRIMARY KEY,
    "nome" VARCHAR(50) NOT NULL,
    "tipo_regiao" VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS "regiao_nome_idx" ON "REGIAO" ("nome");

-- ============================================================================
-- TABELA: UNIDADE_DE_SAUDE
-- ============================================================================
CREATE TABLE IF NOT EXISTS "UNIDADE_DE_SAUDE" (
    "id_unidade" SERIAL PRIMARY KEY,
    "id_regiao" INTEGER NOT NULL REFERENCES "REGIAO"("id_regiao") ON DELETE CASCADE,
    "nome_unidade" VARCHAR(255) NOT NULL,
    "morada_unidade" VARCHAR(255) NOT NULL,
    "tipo_unidade" VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS "unidade_saude_regiao_idx" ON "UNIDADE_DE_SAUDE" ("id_regiao");
CREATE INDEX IF NOT EXISTS "unidade_saude_nome_idx" ON "UNIDADE_DE_SAUDE" ("nome_unidade");

-- ============================================================================
-- TABELA: ESPECIALIDADES
-- ============================================================================
CREATE TABLE IF NOT EXISTS "ESPECIALIDADES" (
    "id_especialidade" SERIAL PRIMARY KEY,
    "nome_especialidade" VARCHAR(255) NOT NULL,
    "descricao" VARCHAR(255) NULL
);

CREATE INDEX IF NOT EXISTS "especialidades_nome_idx" ON "ESPECIALIDADES" ("nome_especialidade");

-- ============================================================================
-- TABELA: MEDICOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS "MEDICOS" (
    "id_medico" SERIAL PRIMARY KEY,
    "id_utilizador" INTEGER NOT NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE CASCADE,
    "numero_ordem" VARCHAR(50) NOT NULL,
    "id_especialidade" INTEGER NULL REFERENCES "ESPECIALIDADES"("id_especialidade") ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "medicos_utilizador_idx" ON "MEDICOS" ("id_utilizador");
CREATE INDEX IF NOT EXISTS "medicos_especialidade_idx" ON "MEDICOS" ("id_especialidade");
CREATE INDEX IF NOT EXISTS "medicos_numero_ordem_idx" ON "MEDICOS" ("numero_ordem");


-- ============================================================================
-- TABELA: ENFERMEIRO
-- ============================================================================
CREATE TABLE IF NOT EXISTS "ENFERMEIRO" (
    "id_enfermeiro" SERIAL PRIMARY KEY,
    "id_utilizador" INTEGER NOT NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE CASCADE,
    "n_ordem_enf" VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS "enfermeiro_utilizador_idx" ON "ENFERMEIRO" ("id_utilizador");
CREATE INDEX IF NOT EXISTS "enfermeiro_n_ordem_idx" ON "ENFERMEIRO" ("n_ordem_enf");

-- ============================================================================
-- TABELA: PACIENTES
-- ============================================================================
CREATE TABLE IF NOT EXISTS "PACIENTES" (
    "id_paciente" SERIAL PRIMARY KEY,
    "id_utilizador" INTEGER NOT NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE CASCADE,
    "data_nasc" DATE NOT NULL,
    "genero" VARCHAR(50) NOT NULL,
    "morada" VARCHAR(255) NULL,
    "alergias" VARCHAR(255) NULL,
    "observacoes" VARCHAR(255) NULL
);

CREATE INDEX IF NOT EXISTS "pacientes_utilizador_idx" ON "PACIENTES" ("id_utilizador");
CREATE INDEX IF NOT EXISTS "pacientes_data_nasc_idx" ON "PACIENTES" ("data_nasc");


-- ============================================================================
-- TABELA: DISPONIBILIDADE
-- ============================================================================
CREATE TABLE IF NOT EXISTS "DISPONIBILIDADE" (
    "id_disponibilidade" SERIAL PRIMARY KEY,
    "id_medico" INTEGER NOT NULL REFERENCES "MEDICOS"("id_medico") ON DELETE CASCADE,
    "id_unidade" INTEGER NOT NULL REFERENCES "UNIDADE_DE_SAUDE"("id_unidade") ON DELETE CASCADE,
    "data" DATE NOT NULL,
    "hora_inicio" TIME NOT NULL,
    "hora_fim" TIME NOT NULL,
    "duracao_slot" INTEGER NOT NULL,
    "status_slot" VARCHAR(20) NOT NULL
);

CREATE INDEX IF NOT EXISTS "disponibilidade_medico_idx" ON "DISPONIBILIDADE" ("id_medico");
CREATE INDEX IF NOT EXISTS "disponibilidade_unidade_idx" ON "DISPONIBILIDADE" ("id_unidade");
CREATE INDEX IF NOT EXISTS "disponibilidade_data_idx" ON "DISPONIBILIDADE" ("data");
CREATE INDEX IF NOT EXISTS "disponibilidade_status_idx" ON "DISPONIBILIDADE" ("status_slot");

-- ============================================================================
-- TABELA: CONSULTAS
-- ============================================================================
CREATE TABLE IF NOT EXISTS "CONSULTAS" (
    "id_consulta" SERIAL PRIMARY KEY,
    "id_paciente" INTEGER NOT NULL REFERENCES "PACIENTES"("id_paciente") ON DELETE CASCADE,
    "id_medico" INTEGER NULL REFERENCES "MEDICOS"("id_medico") ON DELETE CASCADE,
    "id_disponibilidade" INTEGER NULL REFERENCES "DISPONIBILIDADE"("id_disponibilidade") ON DELETE CASCADE,
    "data_consulta" DATE NOT NULL,
    "hora_consulta" TIME NOT NULL,
    "estado" VARCHAR(50) NOT NULL,
    "motivo" VARCHAR(255) NULL,
    "medico_aceitou" BOOLEAN NOT NULL DEFAULT FALSE,
    "paciente_aceitou" BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- RF-22: Notas clínicas e observações (nota: dados completos armazenados no MongoDB)
    "notas_clinicas" TEXT NULL,
    "observacoes" TEXT NULL,
    
    -- RF-21: Check-in workflow
    "paciente_presente" BOOLEAN NOT NULL DEFAULT FALSE,
    "hora_checkin" TIMESTAMP WITH TIME ZONE NULL,
    "hora_inicio_real" TIMESTAMP WITH TIME ZONE NULL,
    "hora_fim_real" TIMESTAMP WITH TIME ZONE NULL,
    
    -- RF-33: Audit trail
    "criado_por" INTEGER NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE SET NULL,
    "criado_em" TIMESTAMP WITH TIME ZONE NULL DEFAULT CURRENT_TIMESTAMP,
    "modificado_por" INTEGER NULL REFERENCES "core_utilizador"("id_utilizador") ON DELETE SET NULL,
    "modificado_em" TIMESTAMP WITH TIME ZONE NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "consultas_paciente_idx" ON "CONSULTAS" ("id_paciente");
CREATE INDEX IF NOT EXISTS "consultas_medico_idx" ON "CONSULTAS" ("id_medico");
CREATE INDEX IF NOT EXISTS "consultas_disponibilidade_idx" ON "CONSULTAS" ("id_disponibilidade");
CREATE INDEX IF NOT EXISTS "consultas_data_idx" ON "CONSULTAS" ("data_consulta");
CREATE INDEX IF NOT EXISTS "consultas_estado_idx" ON "CONSULTAS" ("estado");
CREATE INDEX IF NOT EXISTS "consultas_criado_em_idx" ON "CONSULTAS" ("criado_em");

-- ============================================================================
-- TABELA: FATURAS
-- ============================================================================
CREATE TABLE IF NOT EXISTS "FATURAS" (
    "id_fatura" SERIAL PRIMARY KEY,
    "id_consulta" INTEGER NOT NULL REFERENCES "CONSULTAS"("id_consulta") ON DELETE CASCADE,
    "valor" NUMERIC(10, 2) NOT NULL,
    "metodo_pagamento" VARCHAR(50) NOT NULL,
    "estado" VARCHAR(50) NOT NULL,
    "data_pagamento" DATE NULL
);

CREATE INDEX IF NOT EXISTS "faturas_consulta_idx" ON "FATURAS" ("id_consulta");
CREATE INDEX IF NOT EXISTS "faturas_estado_idx" ON "FATURAS" ("estado");
CREATE INDEX IF NOT EXISTS "faturas_data_pagamento_idx" ON "FATURAS" ("data_pagamento");

-- ============================================================================
-- TABELA: RECEITAS
-- ============================================================================
CREATE TABLE IF NOT EXISTS "RECEITAS" (
    "id_receita" SERIAL PRIMARY KEY,
    "id_consulta" INTEGER NOT NULL REFERENCES "CONSULTAS"("id_consulta") ON DELETE CASCADE,
    "medicamento" VARCHAR(255) NOT NULL,
    "dosagem" VARCHAR(255) NOT NULL,
    "instrucoes" VARCHAR(255) NULL,
    "data_prescricao" DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS "receitas_consulta_idx" ON "RECEITAS" ("id_consulta");
CREATE INDEX IF NOT EXISTS "receitas_data_prescricao_idx" ON "RECEITAS" ("data_prescricao");

SELECT 'Todas as tabelas foram criadas com sucesso!' AS resultado;
