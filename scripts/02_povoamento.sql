-- =============================================
-- POVOAMENTO INICIAL (DML)
-- =============================================

-- Inserir tipos de refeição
INSERT INTO administrativo_tiporefeicao (id, nome, ativo) VALUES 
    (uuid_generate_v4(), 'cafe', TRUE),
    (uuid_generate_v4(), 'lanche_manha', TRUE),
    (uuid_generate_v4(), 'almoco', TRUE),
    (uuid_generate_v4(), 'lanche_tarde', TRUE),
    (uuid_generate_v4(), 'jantar', TRUE);

-- Inserir turmas (inclui coluna compatível `dias_contraturno_int`)
INSERT INTO administrativo_turma (id, nome, turno, dias_contraturno, dias_contraturno_int) VALUES 
    (uuid_generate_v4(), '1º Ano A', 'matutino', '[1,3]'::jsonb, ARRAY[1,3]),
    (uuid_generate_v4(), '2º Ano B', 'vespertino', '[2,4]'::jsonb, ARRAY[2,4]),
    (uuid_generate_v4(), '3º Ano C', 'noturno', '[]'::jsonb, '{}'::integer[]);

-- Inserir pratos
INSERT INTO refeicoes_prato (id, nome, descricao, categoria) VALUES 
    (uuid_generate_v4(), 'Arroz Integral', 'Arroz integral cozido', 'principal'),
    (uuid_generate_v4(), 'Feijão Carioca', 'Feijão preto temperado', 'principal'),
    (uuid_generate_v4(), 'Salada Verde', 'Alface e rúcula', 'salada'),
    (uuid_generate_v4(), 'Suco de Laranja', 'Suco natural', 'complemento'),
    (uuid_generate_v4(), 'Pudim', 'Pudim de leite', 'sobremesa');

-- Inserir refeição para amanhã (exemplo)
INSERT INTO refeicoes_refeicao (id, data, tipo, limite_vagas, exige_reserva) VALUES 
    (uuid_generate_v4(), CURRENT_DATE + 1, 'almoco', 50, TRUE);

-- Vincular pratos à refeição (usando subconsultas)
INSERT INTO refeicoes_refeicao_prato (id, refeicao_id, prato_id)
SELECT uuid_generate_v4(), 
    (SELECT id FROM refeicoes_refeicao WHERE data = CURRENT_DATE + 1 AND tipo = 'almoco'),
    (SELECT id FROM refeicoes_prato WHERE nome = 'Arroz Integral')
UNION
SELECT uuid_generate_v4(), 
    (SELECT id FROM refeicoes_refeicao WHERE data = CURRENT_DATE + 1 AND tipo = 'almoco'),
    (SELECT id FROM refeicoes_prato WHERE nome = 'Feijão Carioca');

-- Criar usuários (senhas: '123456' - substitua pelo hash real)
-- Para gerar hash, use: python -c "from django.contrib.auth.hashers import make_password; print(make_password('123456'))"
INSERT INTO accounts_usuario (id, username, email, password, perfil, is_superuser, is_staff) VALUES 
    (uuid_generate_v4(), 'nutri', 'nutri@escola.com', 'pbkdf2_sha256$...', 'nutricionista', TRUE, TRUE),
    (uuid_generate_v4(), 'refeitorio', 'refeitorio@escola.com', 'pbkdf2_sha256$...', 'refeitorio', FALSE, FALSE),
    (uuid_generate_v4(), 'aluno1', 'aluno1@escola.com', 'pbkdf2_sha256$...', 'aluno', FALSE, FALSE);

-- Associar aluno a uma turma
UPDATE accounts_usuario SET turma_id = (SELECT id FROM administrativo_turma WHERE nome = '1º Ano A' LIMIT 1) WHERE username = 'aluno1';

-- Configuração de janela para almoço
INSERT INTO administrativo_janelareserva (id, tipo_refeicao_id, horario_abertura, horario_fechamento)
SELECT uuid_generate_v4(), id, '15:30:00', '09:30:00'
FROM administrativo_tiporefeicao WHERE nome = 'almoco';

-- Configuração geral fallback
INSERT INTO administrativo_configreserva (id, abertura, encerramento, minutos_cancelamento, vigente_desde)
VALUES (uuid_generate_v4(), '15:30:00', '09:30:00', 60, NOW());