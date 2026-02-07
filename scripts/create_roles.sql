-- ============================================================================
-- Script de Criação de Roles e Permissões - Sistema de Gestão de Consultas
-- Formato conforme exemplo da aula (CREATE ROLE com todos os atributos)
-- ============================================================================

-- ============================================================================
-- 1. CRIAR ROLES (Papéis/Utilizadores)
-- ============================================================================
-- ATENÇÃO: Altere as passwords antes de executar em produção!

-- Role para Pacientes
CREATE ROLE app_paciente_user WITH
    LOGIN
    NOSUPERUSER
    INHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    ENCRYPTED PASSWORD 'w6b@AA5V#A4MhD!XtihLu!paER';

-- Role para Médicos
CREATE ROLE app_medico_user WITH
    LOGIN
    NOSUPERUSER
    INHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    ENCRYPTED PASSWORD 'D&VDBV4rae$L7R*wZ&ut72Jue&';

-- Role para Enfermeiros
CREATE ROLE app_enfermeiro_user WITH
    LOGIN
    NOSUPERUSER
    INHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    ENCRYPTED PASSWORD '5Pb3Qb&MN*J8U&cLckHu5ozsSC';

-- Role para Administradores (Manutenção)
CREATE ROLE app_admin_user WITH
    LOGIN
    NOSUPERUSER
    INHERIT
    CREATEDB
    CREATEROLE
    NOREPLICATION
    ENCRYPTED PASSWORD '7V4&RR^C9cRrg*Sk$ahk7kjGeC';

-- ============================================================================
-- 2. PERMISSÕES PARA PACIENTES
-- ============================================================================

-- Permitir conexão à base de dados
GRANT CONNECT ON DATABASE gestao_consultas TO app_paciente_user;
GRANT USAGE ON SCHEMA public TO app_paciente_user;

-- Leitura de dados de referência
GRANT SELECT ON "REGIAO" TO app_paciente_user;
GRANT SELECT ON "UNIDADE_DE_SAUDE" TO app_paciente_user;
GRANT SELECT ON "ESPECIALIDADES" TO app_paciente_user;

-- Leitura de dados relevantes
GRANT SELECT ON "core_utilizador" TO app_paciente_user;
GRANT SELECT ON "PACIENTES" TO app_paciente_user;
GRANT SELECT ON "MEDICOS" TO app_paciente_user;
GRANT SELECT ON "DISPONIBILIDADE" TO app_paciente_user;
GRANT SELECT ON "CONSULTAS" TO app_paciente_user;
GRANT SELECT ON "FATURAS" TO app_paciente_user;
GRANT SELECT ON "RECEITAS" TO app_paciente_user;

-- Inserção e atualização de consultas
GRANT INSERT ON "CONSULTAS" TO app_paciente_user;
GRANT UPDATE ON "CONSULTAS" TO app_paciente_user;

-- Atualização de seu próprio perfil
GRANT UPDATE ON "core_utilizador" TO app_paciente_user;
GRANT UPDATE ON "PACIENTES" TO app_paciente_user;

-- ============================================================================
-- 3. PERMISSÕES PARA MÉDICOS
-- ============================================================================

-- Permitir conexão à base de dados
GRANT CONNECT ON DATABASE gestao_consultas TO app_medico_user;
GRANT USAGE ON SCHEMA public TO app_medico_user;

-- Leitura de dados de referência
GRANT SELECT ON "REGIAO" TO app_medico_user;
GRANT SELECT ON "UNIDADE_DE_SAUDE" TO app_medico_user;
GRANT SELECT ON "ESPECIALIDADES" TO app_medico_user;

-- Leitura de dados
GRANT SELECT ON "core_utilizador" TO app_medico_user;
GRANT SELECT ON "PACIENTES" TO app_medico_user;
GRANT SELECT ON "MEDICOS" TO app_medico_user;
GRANT SELECT ON "ENFERMEIRO" TO app_medico_user;
GRANT SELECT ON "CONSULTAS" TO app_medico_user;
GRANT SELECT ON "RECEITAS" TO app_medico_user;
GRANT SELECT ON "FATURAS" TO app_medico_user;
GRANT SELECT ON "DISPONIBILIDADE" TO app_medico_user;

-- Gestão de disponibilidade
GRANT INSERT ON "DISPONIBILIDADE" TO app_medico_user;
GRANT UPDATE ON "DISPONIBILIDADE" TO app_medico_user;
GRANT DELETE ON "DISPONIBILIDADE" TO app_medico_user;

-- Gestão de consultas
GRANT UPDATE ON "CONSULTAS" TO app_medico_user;

-- Gestão de receitas
GRANT INSERT ON "RECEITAS" TO app_medico_user;
GRANT UPDATE ON "RECEITAS" TO app_medico_user;
GRANT DELETE ON "RECEITAS" TO app_medico_user;

-- Gestão de faturas
GRANT INSERT ON "FATURAS" TO app_medico_user;
GRANT UPDATE ON "FATURAS" TO app_medico_user;

-- Atualização de perfil
GRANT UPDATE ON "core_utilizador" TO app_medico_user;
GRANT UPDATE ON "MEDICOS" TO app_medico_user;

-- ============================================================================
-- 4. PERMISSÕES PARA ENFERMEIROS
-- ============================================================================

-- Permitir conexão à base de dados
GRANT CONNECT ON DATABASE gestao_consultas TO app_enfermeiro_user;
GRANT USAGE ON SCHEMA public TO app_enfermeiro_user;

-- Leitura de dados de referência
GRANT SELECT ON "REGIAO" TO app_enfermeiro_user;
GRANT SELECT ON "UNIDADE_DE_SAUDE" TO app_enfermeiro_user;
GRANT SELECT ON "ESPECIALIDADES" TO app_enfermeiro_user;

-- Leitura de dados
GRANT SELECT ON "core_utilizador" TO app_enfermeiro_user;
GRANT SELECT ON "PACIENTES" TO app_enfermeiro_user;
GRANT SELECT ON "MEDICOS" TO app_enfermeiro_user;
GRANT SELECT ON "ENFERMEIRO" TO app_enfermeiro_user;
GRANT SELECT ON "CONSULTAS" TO app_enfermeiro_user;
GRANT SELECT ON "DISPONIBILIDADE" TO app_enfermeiro_user;

-- Atualização de consultas (check-in e triagem)
GRANT UPDATE ON "CONSULTAS" TO app_enfermeiro_user;

-- Atualização de pacientes (observações de triagem)
GRANT UPDATE ON "PACIENTES" TO app_enfermeiro_user;

-- Atualização de perfil
GRANT UPDATE ON "core_utilizador" TO app_enfermeiro_user;
GRANT UPDATE ON "ENFERMEIRO" TO app_enfermeiro_user;

-- ============================================================================
-- 5. PERMISSÕES PARA ADMINISTRADORES (Manutenção da BD)
-- ============================================================================

-- Permitir conexão à base de dados
GRANT CONNECT ON DATABASE gestao_consultas TO app_admin_user;
GRANT USAGE ON SCHEMA public TO app_admin_user;

-- Acesso completo a todas as tabelas
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_admin_user;

-- ============================================================================
-- 5. PERMISSÕES PARA TABELAS DJANGO (NECESSÁRIAS PARA TODOS OS ROLES)
-- ============================================================================

-- Todas as roles precisam acessar tabelas de sessão, migrations, etc
-- para que o Django funcione corretamente
DO $$
DECLARE
    role_name TEXT;
BEGIN
    FOR role_name IN SELECT unnest(ARRAY['app_paciente_user', 'app_medico_user', 'app_enfermeiro_user', 'app_admin_user'])
    LOOP
        -- Tabelas de sessão (necessário para login)
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON django_session TO %I', role_name);
        
        -- Tabelas de migrations (necessário para verificações do Django)
        EXECUTE format('GRANT SELECT ON django_migrations TO %I', role_name);
        
        -- Tabelas de content types (necessário para generic relations)
        EXECUTE format('GRANT SELECT ON django_content_type TO %I', role_name);
        
        -- Tabelas de admin log (opcional, mas útil)
        EXECUTE format('GRANT SELECT, INSERT ON django_admin_log TO %I', role_name);
    END LOOP;
END $$;

-- ============================================================================
-- 6. PERMISSÕES PARA VIEWS (NECESSÁRIAS PARA TODOS OS ROLES)
-- ============================================================================

-- Paciente: acesso a views relevantes
GRANT SELECT ON vw_consultas_completas TO app_paciente_user;
GRANT SELECT ON vw_faturas_completas TO app_paciente_user;
GRANT SELECT ON vw_disponibilidades TO app_paciente_user;
GRANT SELECT ON vw_disponibilidades_com_slots TO app_paciente_user;
GRANT SELECT ON vw_consultas_com_fatura TO app_paciente_user;

-- Médico: acesso a views relevantes
GRANT SELECT ON vw_consultas_completas TO app_medico_user;
GRANT SELECT ON vw_faturas_completas TO app_medico_user;
GRANT SELECT ON vw_disponibilidades TO app_medico_user;
GRANT SELECT ON vw_estatisticas_medicos TO app_medico_user;
GRANT SELECT ON vw_disponibilidades_com_slots TO app_medico_user;
GRANT SELECT ON vw_consultas_com_fatura TO app_medico_user;

-- Enfermeiro: acesso a views relevantes
GRANT SELECT ON vw_consultas_completas TO app_enfermeiro_user;
GRANT SELECT ON vw_faturas_completas TO app_enfermeiro_user;
GRANT SELECT ON vw_disponibilidades TO app_enfermeiro_user;
GRANT SELECT ON vw_disponibilidades_com_slots TO app_enfermeiro_user;
GRANT SELECT ON vw_consultas_com_fatura TO app_enfermeiro_user;

-- Admin: acesso a todas as views
GRANT SELECT ON vw_consultas_completas TO app_admin_user;
GRANT SELECT ON vw_faturas_completas TO app_admin_user;
GRANT SELECT ON vw_disponibilidades TO app_admin_user;
GRANT SELECT ON vw_estatisticas_medicos TO app_admin_user;
GRANT SELECT ON vw_dashboard_admin TO app_admin_user;
GRANT SELECT ON vw_disponibilidades_com_slots TO app_admin_user;
GRANT SELECT ON vw_admin_ultimas_consultas TO app_admin_user;
GRANT SELECT ON vw_consultas_com_fatura TO app_admin_user;

-- ============================================================================
-- 7. PERMISSÕES PARA FUNÇÕES E PROCEDIMENTOS
-- ============================================================================

-- Paciente: funções relacionadas aos seus dados e consultas
GRANT EXECUTE ON FUNCTION obter_estatisticas_paciente(INTEGER) TO app_paciente_user;
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador(INTEGER) TO app_paciente_user;
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador_id(INTEGER) TO app_paciente_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_email(VARCHAR) TO app_paciente_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_id(INTEGER) TO app_paciente_user;
GRANT EXECUTE ON FUNCTION validar_horario_disponibilidade(INTEGER, DATE, TIME) TO app_paciente_user;

-- Médico: funções relacionadas a consultas, pacientes e receitas
GRANT EXECUTE ON FUNCTION obter_consultas_hoje_medico(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_consultas_semana_medico(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_dashboard_medico(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador_id(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_email(VARCHAR) TO app_medico_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_id(INTEGER) TO app_medico_user;
GRANT EXECUTE ON FUNCTION validar_horario_disponibilidade(INTEGER, DATE, TIME) TO app_medico_user;
GRANT EXECUTE ON PROCEDURE inserir_receita(INTEGER, INTEGER, TEXT, TEXT) TO app_medico_user;

-- Enfermeiro: funções relacionadas a consultas e disponibilidade
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador(INTEGER) TO app_enfermeiro_user;
GRANT EXECUTE ON FUNCTION obter_paciente_por_utilizador_id(INTEGER) TO app_enfermeiro_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_email(VARCHAR) TO app_enfermeiro_user;
GRANT EXECUTE ON FUNCTION obter_utilizador_por_id(INTEGER) TO app_enfermeiro_user;
GRANT EXECUTE ON FUNCTION validar_horario_disponibilidade(INTEGER, DATE, TIME) TO app_enfermeiro_user;

-- Admin: acesso a todas as funções e procedimentos
DO $$
DECLARE
    func_record RECORD;
BEGIN
    FOR func_record IN 
        SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
          AND p.prokind IN ('f', 'p')
    LOOP
        BEGIN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %I(%s) TO app_admin_user', 
                func_record.proname, 
                func_record.args);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END LOOP;
END $$;

-- ============================================================================
-- 8. VERIFICAÇÃO
-- ============================================================================

-- Verificar roles criados
SELECT rolname FROM pg_roles WHERE rolname LIKE 'app_%';

-- Verificar permissões (exemplo)
SELECT grantee, table_name, privilege_type 
FROM information_schema.table_privileges 
WHERE grantee LIKE 'app_%'
ORDER BY grantee, table_name, privilege_type;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

SELECT 'Roles e permissões configurados com sucesso!' AS resultado;
