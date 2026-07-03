-- =============================================
-- 01_estrutura.sql
-- Script de criação da estrutura do banco (DDL)
-- =============================================

-- Habilitar a extensão para gerar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela de Turmas
CREATE TABLE IF NOT EXISTS administrativo_turma (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(100) NOT NULL UNIQUE,
    turno VARCHAR(10) NOT NULL CHECK (turno IN ('matutino', 'vespertino', 'noturno')),
    dias_contraturno JSONB NOT NULL DEFAULT '[]'::jsonb,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela de Usuários (unificada)
CREATE TABLE IF NOT EXISTS accounts_usuario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL UNIQUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    perfil VARCHAR(20) NOT NULL CHECK (perfil IN ('aluno', 'nutricionista', 'refeitorio')),
    bloqueado BOOLEAN NOT NULL DEFAULT FALSE,
    turma_id UUID,
    FOREIGN KEY (turma_id) REFERENCES administrativo_turma(id) ON DELETE RESTRICT
);

-- Tabela de Tipos de Refeição
CREATE TABLE IF NOT EXISTS administrativo_tiporefeicao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(20) NOT NULL UNIQUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela de Janelas de Reserva (por tipo de refeição)
CREATE TABLE IF NOT EXISTS administrativo_janelareserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo_refeicao_id UUID NOT NULL UNIQUE,
    horario_abertura TIME NOT NULL,
    horario_fechamento TIME NOT NULL,
    FOREIGN KEY (tipo_refeicao_id) REFERENCES administrativo_tiporefeicao(id) ON DELETE CASCADE
);

-- Tabela de Refeições
CREATE TABLE IF NOT EXISTS refeicoes_refeicao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data DATE NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    limite_vagas INTEGER NOT NULL,
    exige_reserva BOOLEAN NOT NULL DEFAULT TRUE,
    chamada_finalizada BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de Reservas
CREATE TABLE IF NOT EXISTS reservas_reserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aluno_id UUID NOT NULL,
    refeicao_id UUID NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada', 'concluida')),
    reservado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelado_em TIMESTAMPTZ,
    FOREIGN KEY (aluno_id) REFERENCES accounts_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (refeicao_id) REFERENCES refeicoes_refeicao(id) ON DELETE CASCADE,
    UNIQUE (aluno_id, refeicao_id)
);

-- Tabela de Presença (gerada na chamada)
CREATE TABLE IF NOT EXISTS administrativo_presenca (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reserva_id UUID NOT NULL UNIQUE,
    confirmado_por_id UUID,
    compareceu BOOLEAN NOT NULL,
    confirmado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (reserva_id) REFERENCES reservas_reserva(id) ON DELETE CASCADE,
    FOREIGN KEY (confirmado_por_id) REFERENCES accounts_usuario(id) ON DELETE CASCADE
);

-- Tabela de Configuração de Reserva (refletindo `administrativo.ConfigReserva`)
CREATE TABLE IF NOT EXISTS administrativo_configreserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    abertura TIME NOT NULL,
    encerramento TIME NOT NULL,
    minutos_cancelamento INTEGER NOT NULL DEFAULT 60,
    vigente_desde TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criado_por UUID,
    FOREIGN KEY (criado_por) REFERENCES accounts_usuario(id) ON DELETE SET NULL
);

-- Tabela de Notificações (refletindo `administrativo.Notificacao`)
CREATE TABLE IF NOT EXISTS administrativo_notificacao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mensagem VARCHAR(255) NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refeicao_id UUID NOT NULL,
    FOREIGN KEY (refeicao_id) REFERENCES refeicoes_refeicao(id) ON DELETE CASCADE
);

-- Tabela de Strikes
CREATE TABLE IF NOT EXISTS administrativo_strike (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aluno_id UUID NOT NULL,
    presenca_id UUID NOT NULL,
    aplicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expira_em TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (aluno_id) REFERENCES accounts_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (presenca_id) REFERENCES administrativo_presenca(id) ON DELETE CASCADE
);

-- Tabela de Pratos
CREATE TABLE IF NOT EXISTS refeicoes_prato (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('principal', 'complemento', 'salada', 'sobremesa')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela de Associação Refeição-Prato (N-para-N)
CREATE TABLE IF NOT EXISTS refeicoes_refeicao_prato (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    refeicao_id UUID NOT NULL,
    prato_id UUID NOT NULL,
    FOREIGN KEY (refeicao_id) REFERENCES refeicoes_refeicao(id) ON DELETE CASCADE,
    FOREIGN KEY (prato_id) REFERENCES refeicoes_prato(id) ON DELETE CASCADE,
    UNIQUE (refeicao_id, prato_id)
);

-- =============================================
-- Funções de compatibilidade (retornam inteiros)
-- =============================================

-- Retorna o primeiro dia de `dias_contraturno` como INTEGER (ou NULL)
CREATE OR REPLACE FUNCTION administrativo_get_dia_contraturno(turma_uuid UUID)
RETURNS INTEGER AS $$
    SELECT (dias_contraturno->>0)::INTEGER
    FROM administrativo_turma
    WHERE id = turma_uuid;
$$ LANGUAGE SQL STABLE;

-- Retorna todos os dias de `dias_contraturno` como um array de INTEGER
CREATE OR REPLACE FUNCTION administrativo_get_dias_contraturno_ints(turma_uuid UUID)
RETURNS INTEGER[] AS $$
    SELECT array_agg((elem)::INTEGER)
    FROM administrativo_turma,
         jsonb_array_elements_text(administrativo_turma.dias_contraturno) AS elem
    WHERE administrativo_turma.id = turma_uuid;
$$ LANGUAGE SQL STABLE;

-- View de compatibilidade (leitura): expõe `dias_contraturno` como INTEGER[]
CREATE OR REPLACE VIEW administrativo_turma_compat AS
SELECT
    id,
    nome,
    turno,
    (
        SELECT array_agg((e)::INTEGER)
        FROM jsonb_array_elements_text(dias_contraturno) AS e
    ) AS dias_contraturno_int,
    dias_contraturno AS dias_contraturno_json,
    ativo
FROM administrativo_turma;

-- Coluna compatível para código legado: INTEGER[]
ALTER TABLE administrativo_turma
    ADD COLUMN IF NOT EXISTS dias_contraturno_int INTEGER[] DEFAULT '{}'::integer[];

-- Função trigger para manter JSONB <-> INTEGER[] sincronizados
CREATE OR REPLACE FUNCTION administrativo_sync_dias_contraturno()
RETURNS TRIGGER AS $$
BEGIN
    -- Prioriza o valor explícito em dias_contraturno_int quando presente
    IF NEW.dias_contraturno_int IS NOT NULL AND array_length(NEW.dias_contraturno_int, 1) IS NOT NULL THEN
        NEW.dias_contraturno = to_jsonb(NEW.dias_contraturno_int);
    ELSIF NEW.dias_contraturno IS NOT NULL THEN
        NEW.dias_contraturno_int = ARRAY(
            SELECT (e)::INTEGER
            FROM jsonb_array_elements_text(NEW.dias_contraturno) AS e
        );
    ELSE
        NEW.dias_contraturno = '[]'::jsonb;
        NEW.dias_contraturno_int = '{}'::integer[];
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql STABLE;

-- Trigger que executa antes de INSERT ou UPDATE
DROP TRIGGER IF EXISTS administrativo_sync_dias_contraturno_trg ON administrativo_turma;
CREATE TRIGGER administrativo_sync_dias_contraturno_trg
BEFORE INSERT OR UPDATE ON administrativo_turma
FOR EACH ROW EXECUTE FUNCTION administrativo_sync_dias_contraturno();
