-- ============================================================================
-- ROLES E PRIVILÉGIOS (PostgreSQL)
--
-- Substituir:
--   <DB_NAME>              nome da base de dados
--   <APP_PACIENTE_USER>    utilizador de login para pacientes
--   <APP_MEDICO_USER>      utilizador de login para médicos
--   <APP_ENFERMEIRO_USER>  utilizador de login para enfermeiros
--   <APP_ADMIN_USER>       utilizador de login para admin
--   <PASSWORD_*>           passwords
-- ============================================================================

-- Recomendações:
-- 1) Executar com um superuser.
-- 2) Depois ajustar no Django o user/password de cada ambiente.

-- Segurança: remover privilégios públicos
REVOKE ALL ON DATABASE "<DB_NAME>" FROM PUBLIC;
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
GRANT CONNECT ON DATABASE "<DB_NAME>" TO app_base, app_paciente, app_medico, app_enfermeiro, app_admin;

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

-- Users de login (exemplo)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '<APP_PACIENTE_USER>') THEN
        CREATE ROLE "<APP_PACIENTE_USER>" LOGIN PASSWORD '<PASSWORD_PACIENTE>' IN ROLE app_paciente;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '<APP_MEDICO_USER>') THEN
        CREATE ROLE "<APP_MEDICO_USER>" LOGIN PASSWORD '<PASSWORD_MEDICO>' IN ROLE app_medico;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '<APP_ENFERMEIRO_USER>') THEN
        CREATE ROLE "<APP_ENFERMEIRO_USER>" LOGIN PASSWORD '<PASSWORD_ENFERMEIRO>' IN ROLE app_enfermeiro;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '<APP_ADMIN_USER>') THEN
        CREATE ROLE "<APP_ADMIN_USER>" LOGIN PASSWORD '<PASSWORD_ADMIN>' IN ROLE app_admin;
    END IF;
END $$;


