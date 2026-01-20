-- Utilizador table
CREATE TABLE "UTILIZADOR" (
    "id_utilizador" serial PRIMARY KEY,
    "password" varchar(128) NOT NULL,
    "last_login" timestamp NULL,
    "is_superuser" boolean NOT NULL,
    "nome" varchar(255) NOT NULL,
    "email" varchar(254) NOT NULL UNIQUE,
    "telefone" varchar(20) NULL,
    "n_utente" varchar(20) NULL,
    "role" varchar(20) NOT NULL,
    "data_registo" timestamp NOT NULL,
    "ativo" boolean NOT NULL DEFAULT true,
    "foto_perfil" text NULL,
    "email_verified" boolean NOT NULL DEFAULT false,
    "verification_token" varchar(100) NULL,
    "reset_token" varchar(100) NULL,
    "reset_token_expires" timestamp NULL
);

-- Regiao table
CREATE TABLE "REGIAO" (
    "id_regiao" serial PRIMARY KEY,
    "nome" varchar(50) NOT NULL,
    "tipo_regiao" varchar(50) NOT NULL
);

-- Unidade de Saude table
CREATE TABLE "UNIDADE_DE_SAUDE" (
    "id_unidade" serial PRIMARY KEY,
    "id_regiao" integer NOT NULL,
    "nome_unidade" varchar(255) NOT NULL,
    "morada_unidade" varchar(255) NOT NULL,
    "tipo_unidade" varchar(255) NOT NULL,
    FOREIGN KEY ("id_regiao") REFERENCES "REGIAO"("id_regiao")
);

-- Especialidades table
CREATE TABLE "ESPECIALIDADES" (
    "id_especialidade" serial PRIMARY KEY,
    "nome_especialidade" varchar(255) NOT NULL,
    "descricao" varchar(255) NULL
);

-- Medicos table
CREATE TABLE "MEDICOS" (
    "id_medico" serial PRIMARY KEY,
    "id_utilizador" integer NOT NULL,
    "numero_ordem" varchar(50) NOT NULL,
    "id_especialidade" integer NULL,
    FOREIGN KEY ("id_utilizador") REFERENCES "UTILIZADOR"("id_utilizador"),
    FOREIGN KEY ("id_especialidade") REFERENCES "ESPECIALIDADES"("id_especialidade")
);

-- Enfermeiro table
CREATE TABLE "ENFERMEIRO" (
    "id_enfermeiro" serial PRIMARY KEY,
    "id_utilizador" integer NOT NULL,
    "n_ordem_enf" varchar(50) NOT NULL,
    FOREIGN KEY ("id_utilizador") REFERENCES "UTILIZADOR"("id_utilizador")
);

-- Pacientes table
CREATE TABLE "PACIENTES" (
    "id_paciente" serial PRIMARY KEY,
    "id_utilizador" integer NOT NULL,
    "data_nasc" date NOT NULL,
    "genero" varchar(50) NOT NULL,
    "morada" varchar(255) NULL,
    "alergias" varchar(255) NULL,
    "observacoes" varchar(255) NULL,
    FOREIGN KEY ("id_utilizador") REFERENCES "UTILIZADOR"("id_utilizador")
);

-- Disponibilidade table
CREATE TABLE "DISPONIBILIDADE" (
    "id_disponibilidade" serial PRIMARY KEY,
    "id_medico" integer NOT NULL,
    "id_unidade" integer NOT NULL,
    "data" date NOT NULL,
    "hora_inicio" time NOT NULL,
    "hora_fim" time NOT NULL,
    "duracao_slot" integer NOT NULL,
    "status_slot" varchar(20) NOT NULL,
    FOREIGN KEY ("id_medico") REFERENCES "MEDICOS"("id_medico"),
    FOREIGN KEY ("id_unidade") REFERENCES "UNIDADE_DE_SAUDE"("id_unidade")
);

-- Consultas table
CREATE TABLE "CONSULTAS" (
    "id_consulta" serial PRIMARY KEY,
    "id_paciente" integer NOT NULL,
    "id_medico" integer NULL,
    "id_disponibilidade" integer NULL,
    "data_consulta" date NOT NULL,
    "hora_consulta" time NOT NULL,
    "estado" varchar(50) NOT NULL,
    "motivo" varchar(255) NULL,
    "medico_aceitou" boolean NOT NULL DEFAULT false,
    "paciente_aceitou" boolean NOT NULL DEFAULT false,
    "notas_clinicas" text NULL,
    "observacoes" text NULL,
    "paciente_presente" boolean NOT NULL DEFAULT false,
    "hora_checkin" timestamp NULL,
    "hora_inicio_real" timestamp NULL,
    "hora_fim_real" timestamp NULL,
    "criado_por" integer NULL,
    "criado_em" timestamp NULL,
    "modificado_por" integer NULL,
    "modificado_em" timestamp NULL,
    FOREIGN KEY ("id_paciente") REFERENCES "PACIENTES"("id_paciente"),
    FOREIGN KEY ("id_medico") REFERENCES "MEDICOS"("id_medico"),
    FOREIGN KEY ("id_disponibilidade") REFERENCES "DISPONIBILIDADE"("id_disponibilidade"),
    FOREIGN KEY ("criado_por") REFERENCES "UTILIZADOR"("id_utilizador"),
    FOREIGN KEY ("modificado_por") REFERENCES "UTILIZADOR"("id_utilizador")
);

-- Faturas table
CREATE TABLE "FATURAS" (
    "id_fatura" serial PRIMARY KEY,
    "id_consulta" integer NOT NULL,
    "valor" decimal(10,2) NOT NULL,
    "metodo_pagamento" varchar(50) NOT NULL,
    "estado" varchar(50) NOT NULL,
    "data_pagamento" date NULL,
    FOREIGN KEY ("id_consulta") REFERENCES "CONSULTAS"("id_consulta")
);

-- Receitas table
CREATE TABLE "RECEITAS" (
    "id_receita" serial PRIMARY KEY,
    "id_consulta" integer NOT NULL,
    "medicamento" varchar(255) NOT NULL,
    "dosagem" varchar(255) NOT NULL,
    "instrucoes" varchar(255) NULL,
    "data_prescricao" date NOT NULL,
    FOREIGN KEY ("id_consulta") REFERENCES "CONSULTAS"("id_consulta")
);