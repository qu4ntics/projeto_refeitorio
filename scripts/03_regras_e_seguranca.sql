-- =============================================
-- REGRAS ATIVAS (TRIGGERS) E SEGURANÇA (GRANTS)
-- =============================================

-- Trigger: Bloquear aluno ao inserir strike (2 strikes ativos)
CREATE OR REPLACE FUNCTION fn_bloquear_aluno_apos_strike()
RETURNS TRIGGER AS $$
DECLARE
    strikes_ativos INTEGER;
BEGIN
    SELECT COUNT(*) INTO strikes_ativos
    FROM administrativo_strike
    WHERE aluno_id = NEW.aluno_id AND expira_em > NOW();

    IF strikes_ativos >= 2 THEN
        UPDATE accounts_usuario
        SET bloqueado = TRUE
        WHERE id = NEW.aluno_id;
    END IF;

    -- Criar notificação para o aluno
    INSERT INTO administrativo_notificacao (id, usuario_id, titulo, mensagem)
    VALUES (
        uuid_generate_v4(),
        NEW.aluno_id,
        'Novo Strike Recebido',
        'Você recebeu um strike por falta. Lembre-se que 2 strikes ativos resultam em bloqueio.'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bloquear_aluno_apos_strike
AFTER INSERT ON administrativo_strike
FOR EACH ROW
EXECUTE FUNCTION fn_bloquear_aluno_apos_strike();

-- Trigger: Validar reserva (aluno bloqueado e vagas)
CREATE OR REPLACE FUNCTION fn_validar_reserva()
RETURNS TRIGGER AS $$
DECLARE
    vagas_ocupadas INTEGER;
    limite INTEGER;
    aluno_bloqueado BOOLEAN;
BEGIN
    SELECT bloqueado INTO aluno_bloqueado
    FROM accounts_usuario WHERE id = NEW.aluno_id;
    IF aluno_bloqueado THEN
        RAISE EXCEPTION 'Aluno bloqueado não pode fazer reservas.';
    END IF;

    SELECT COUNT(*) INTO vagas_ocupadas
    FROM reservas_reserva
    WHERE refeicao_id = NEW.refeicao_id AND status = 'ativa';

    SELECT limite_vagas INTO limite
    FROM refeicoes_refeicao WHERE id = NEW.refeicao_id;

    IF vagas_ocupadas >= limite THEN
        RAISE EXCEPTION 'Refeição lotada. Não é possível reservar.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_reserva
BEFORE INSERT ON reservas_reserva
FOR EACH ROW
EXECUTE FUNCTION fn_validar_reserva();

-- =============================================
-- SEGURANÇA – GRANTS E ROLES
-- =============================================

-- Criar roles (papéis)
CREATE ROLE aluno_role;
CREATE ROLE nutricionista_role;
CREATE ROLE refeitorio_role;

-- Aluno: leitura de cardápio, gestão de suas reservas
GRANT SELECT ON refeicoes_refeicao, refeicoes_prato, refeicoes_refeicao_prato TO aluno_role;
GRANT SELECT, INSERT, UPDATE (status) ON reservas_reserva TO aluno_role;

-- Nutricionista: controle total sobre dados operacionais
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nutricionista_role;

-- Refeitório: visualizar reservas e gerenciar presenças/strikes
GRANT SELECT ON reservas_reserva, accounts_usuario TO refeitorio_role;
GRANT INSERT, UPDATE ON administrativo_presenca, administrativo_strike TO refeitorio_role;

-- Revogar permissões indesejadas (exemplo)
REVOKE SELECT ON accounts_usuario FROM aluno_role;

-- Associar usuários às roles (substitua pelos nomes reais dos usuários)
-- GRANT aluno_role TO aluno1_user;
-- GRANT nutricionista_role TO nutri_user;
-- GRANT refeitorio_role TO refeitorio_user;