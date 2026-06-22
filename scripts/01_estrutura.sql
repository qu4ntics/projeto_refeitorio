-- =============================================
-- ESTRUTURA DO BANCO DE DADOS (DDL)
-- Baseado nos modelos Django do projeto
-- =============================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela accounts_usuario (Usuário customizado)
CREATE TABLE accounts_usuario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    email VARCHAR(254) NOT NULL UNIQUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP NOT NULL DEFAULT NOW(),
    perfil VARCHAR(20) NOT NULL DEFAULT 'aluno',
    bloqueado BOOLEAN NOT NULL DEFAULT FALSE,
    turma_id UUID
);

-- Tabela administrativo_turma
CREATE TABLE administrativo_turma (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(100) NOT NULL,
    turno VARCHAR(20) NOT NULL DEFAULT 'matutino',
    dias_contraturno JSONB NOT NULL DEFAULT '[]',
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela refeicoes_prato
CREATE TABLE refeicoes_prato (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(200) NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    categoria VARCHAR(20) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabela refeicoes_refeicao
CREATE TABLE refeicoes_refeicao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data DATE NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    limite_vagas INTEGER NOT NULL CHECK (limite_vagas >= 0),
    exige_reserva BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    chamada_finalizada BOOLEAN NOT NULL DEFAULT FALSE
);

-- Tabela refeicoes_refeicao_prato (many-to-many)
CREATE TABLE refeicoes_refeicao_prato (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    refeicao_id UUID NOT NULL REFERENCES refeicoes_refeicao(id) ON DELETE CASCADE,
    prato_id UUID NOT NULL REFERENCES refeicoes_prato(id) ON DELETE CASCADE,
    CONSTRAINT unique_refeicao_prato UNIQUE (refeicao_id, prato_id)
);

-- Tabela reservas_reserva
CREATE TABLE reservas_reserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aluno_id UUID NOT NULL REFERENCES accounts_usuario(id) ON DELETE PROTECT,
    refeicao_id UUID NOT NULL REFERENCES refeicoes_refeicao(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada', 'concluida')),
    reservado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    cancelado_em TIMESTAMP,
    CONSTRAINT unique_reserva_ativa_aluno_refeicao UNIQUE (aluno_id, refeicao_id) WHERE (status = 'ativa')
);

-- Tabela administrativo_presenca
CREATE TABLE administrativo_presenca (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reserva_id UUID NOT NULL UNIQUE REFERENCES reservas_reserva(id) ON DELETE CASCADE,
    confirmado_por_id UUID NOT NULL REFERENCES accounts_usuario(id) ON DELETE CASCADE,
    compareceu BOOLEAN NOT NULL,
    confirmado_em TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabela administrativo_strike
CREATE TABLE administrativo_strike (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aluno_id UUID NOT NULL REFERENCES accounts_usuario(id) ON DELETE PROTECT,
    presenca_id UUID NOT NULL UNIQUE REFERENCES administrativo_presenca(id) ON DELETE CASCADE,
    aplicado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    expira_em TIMESTAMP NOT NULL
);

-- Tabela administrativo_notificacao
CREATE TABLE administrativo_notificacao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES accounts_usuario(id) ON DELETE CASCADE,
    titulo VARCHAR(100) NOT NULL,
    mensagem TEXT NOT NULL,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    criada_em TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabela administrativo_tiporefeicao
CREATE TABLE administrativo_tiporefeicao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(50) NOT NULL UNIQUE,
    ativo BOOLEAN NOT NULL DEFAULT FALSE
);

-- Tabela administrativo_janelareserva
CREATE TABLE administrativo_janelareserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo_refeicao_id UUID NOT NULL UNIQUE REFERENCES administrativo_tiporefeicao(id) ON DELETE PROTECT,
    horario_abertura TIME NOT NULL,
    horario_fechamento TIME NOT NULL
);

-- Tabela administrativo_configreserva (fallback)
CREATE TABLE administrativo_configreserva (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    abertura TIME NOT NULL,
    encerramento TIME NOT NULL,
    minutos_cancelamento INTEGER NOT NULL DEFAULT 60,
    vigente_desde TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id UUID REFERENCES accounts_usuario(id) ON DELETE SET NULL
);

-- Chaves estrangeiras adicionais
ALTER TABLE accounts_usuario ADD CONSTRAINT fk_usuario_turma FOREIGN KEY (turma_id) REFERENCES administrativo_turma(id) ON DELETE PROTECT;