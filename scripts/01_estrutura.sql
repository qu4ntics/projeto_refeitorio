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
    dias_contraturno INTEGER[],
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela de Usuários (unificada)
CREATE TABLE IF NOT EXISTS accounts_usuario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    perfil VARCHAR(15) NOT NULL CHECK (perfil IN ('aluno', 'nutricionista', 'refeitorio')),
    bloqueado BOOLEAN NOT NULL DEFAULT FALSE,
    turma_id UUID,
    FOREIGN KEY (turma_id) REFERENCES administrativo_turma(id) ON DELETE SET NULL
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
    FOREIGN KEY (confirmado_por_id) REFERENCES accounts_usuario(id) ON DELETE SET NULL
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