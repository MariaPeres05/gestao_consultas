-- ============================================================================
-- ROLES E PRIVILÉGIOS (PostgreSQL)
-- ============================================================================

-- Segurança: remover privilégios públicos
REVOKE ALL ON DATABASE gestao_consultas_test FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Roles base (sem login)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_base') THEN
        CREATE ROLE app_base;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_paciente') THEN
        CREATE ROLE app_paciente;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_medico') THEN
        CREATE ROLE app_medico;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_enfermeiro') THEN
        CREATE ROLE app_enfermeiro;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
        CREATE ROLE app_admin;
    END IF;
END $$;

-- Permitir ligação à BD
GRANT CONNECT ON DATABASE gestao_consultas_test TO app_base, app_paciente, app_medico, app_enfermeiro, app_admin;

-- Uso do schema
GRANT USAGE ON SCHEMA public TO app_base, app_paciente, app_medico, app_enfermeiro, app_admin;

-- Base: leitura de views e execução de funções/procedures
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_base;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_base;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO app_base;

-- Aplicar o base às roles específicas
GRANT app_base TO app_paciente, app_medico, app_enfermeiro, app_admin;

-- Paciente: operações necessárias na app
GRANT SELECT, INSERT, UPDATE ON TABLE
    "CONSULTAS",
    "FATURAS",
    "RECEITAS",
    "DISPONIBILIDADE"
TO app_paciente;

-- Médico: gestão de consultas e disponibilidades
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    "CONSULTAS",
    "DISPONIBILIDADE",
    "RECEITAS"
TO app_medico;

-- Enfermeiro: leitura operacional
GRANT SELECT, UPDATE ON TABLE
    "CONSULTAS",
    "DISPONIBILIDADE"
TO app_enfermeiro;

GRANT SELECT ON TABLE
    "RECEITAS",
    "PACIENTES",
    "MEDICOS",
    "ENFERMEIROS",
    "core_utilizador",
    "ESPECIALIDADES",
    "UNIDADE_DE_SAUDE"
TO app_enfermeiro;

-- Admin: acesso total às tabelas do sistema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app_admin;

-- Privilegios futuros (novas tabelas/funcs/seqs)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO app_base;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT EXECUTE ON FUNCTIONS TO app_base;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT EXECUTE ON PROCEDURES TO app_base;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_admin;

-- Users de login
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_paciente_user') THEN
        CREATE ROLE app_paciente_user LOGIN PASSWORD 'w6b@AA5V#A4MhD!XtihLu!paER' IN ROLE app_paciente;
    ELSE
        GRANT app_paciente TO app_paciente_user;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_medico_user') THEN
        CREATE ROLE app_medico_user LOGIN PASSWORD 'D&VDBV4rae$L7R*wZ&ut72Jue&' IN ROLE app_medico;
    ELSE
        GRANT app_medico TO app_medico_user;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_enfermeiro_user') THEN
        CREATE ROLE app_enfermeiro_user LOGIN PASSWORD '5Pb3Qb&MN*J8U&cLckHu5ozsSC' IN ROLE app_enfermeiro;
    ELSE
        GRANT app_enfermeiro TO app_enfermeiro_user;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin_user') THEN
        CREATE ROLE app_admin_user LOGIN PASSWORD '7V4&RR^C9cRrg*Sk$ahk7kjGeC' IN ROLE app_admin;
    ELSE
        GRANT app_admin TO app_admin_user;
    END IF;
END $$;


