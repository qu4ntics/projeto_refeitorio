-- =============================================
-- 03_regras_e_seguranca.sql
-- Implementação de regras de segurança e lógicas ativas (Triggers)
-- =============================================

-- Parte 1: Segurança e Controle de Acesso (GRANT/REVOKE)

-- Cria uma role (grupo) para a aplicação web com permissão de login.
-- A aplicação se conectará ao banco usando um usuário que pertence a esta role.
CREATE ROLE role_aplicacao WITH LOGIN;

-- Cria uma role apenas para leitura, sem permissão de login.
-- Útil para auditoria ou relatórios, garantindo que não possam alterar dados.
CREATE ROLE role_leitura;

-- Concede permissões específicas para a role da aplicação.
-- A aplicação pode selecionar, inserir, atualizar e deletar dados nas tabelas principais.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO role_aplicacao;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO role_aplicacao;

-- Concede permissões para a role de leitura.
-- Pode apenas executar SELECT nas tabelas.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO role_leitura;

-- Revoga todas as permissões do public (padrão do PostgreSQL).
-- Garante que apenas roles com permissões explícitas possam acessar os objetos.
REVOKE ALL ON DATABASE postgres FROM PUBLIC;


-- Parte 2: Regras Ativas (Trigger para Strikes)
-- Move a lógica de aplicação de strike (RF16) para o SGBD.

-- Função de Trigger: será executada sempre que a trigger for disparada.
CREATE OR REPLACE FUNCTION fn_aplicar_strike_por_falta()
RETURNS TRIGGER AS $$
DECLARE
    v_aluno_id UUID;
BEGIN
    -- Verifica se o campo 'compareceu' foi alterado para FALSE.
    -- A trigger só age na transição para "não compareceu".
    IF NEW.compareceu = FALSE AND OLD.compareceu = TRUE THEN
        
        -- 1. Busca o ID do aluno a partir da reserva associada.
        SELECT r.aluno_id INTO v_aluno_id
        FROM reservas_reserva r
        WHERE r.id = NEW.reserva_id;

        -- 2. Insere um novo registro na tabela de strikes.
        INSERT INTO administrativo_strike (id, aluno_id, presenca_id, aplicado_em, expira_em)
        VALUES (
            uuid_generate_v4(),
            v_aluno_id,
            NEW.id,
            NOW(),
            NOW() + INTERVAL '30 days' -- Strike expira em 30 dias.
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: vincula a função de trigger à tabela 'administrativo_presenca'.
-- A função será executada DEPOIS de cada UPDATE na tabela.
CREATE TRIGGER trg_aplicar_strike_apos_update_presenca
AFTER UPDATE ON administrativo_presenca
FOR EACH ROW
EXECUTE FUNCTION fn_aplicar_strike_por_falta();