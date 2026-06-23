-- =============================================
-- 04_consultas_principais.sql
-- Principais consultas (queries) utilizadas pela aplicação no dia a dia
-- Baseado no código-fonte (views.py e models.py)
-- =============================================

-- 1. Cardápio da semana (usado em refeicoes/views.py - homepage e cardapio_semana)
-- Busca refeições com vagas disponíveis e reservas ativas
SELECT 
    r.id,
    r.data,
    r.tipo,
    r.limite_vagas,
    r.exige_reserva,
    COUNT(res.id) FILTER (WHERE res.status = 'ativa') AS reservas_ativas,
    (r.limite_vagas - COUNT(res.id) FILTER (WHERE res.status = 'ativa')) AS vagas_disponiveis
FROM refeicoes_refeicao r
LEFT JOIN reservas_reserva res ON r.id = res.refeicao_id
WHERE r.data BETWEEN '2026-06-22' AND '2026-06-28'  -- semana atual
GROUP BY r.id
ORDER BY r.data, r.tipo;

-- 2. Reservas do dia para chamada (usado em refeicoes/views.py - lista_presenca)
-- Lista todas as reservas de uma data específica com dados do aluno e turma
SELECT 
    res.id AS reserva_id,
    res.status,
    u.first_name || ' ' || u.last_name AS nome_aluno,
    u.email,
    t.nome AS turma,
    r.tipo AS tipo_refeicao,
    r.data,
    pres.compareceu,
    pres.confirmado_em
FROM reservas_reserva res
JOIN accounts_usuario u ON res.aluno_id = u.id
LEFT JOIN administrativo_turma t ON u.turma_id = t.id
JOIN refeicoes_refeicao r ON res.refeicao_id = r.id
LEFT JOIN administrativo_presenca pres ON res.id = pres.reserva_id
WHERE r.data = CURRENT_DATE
ORDER BY u.first_name;

-- 3. Verificar strikes ativos de um aluno (usado em administrativo/models.py - Strike.save)
-- Conta strikes que ainda não expiraram para decidir bloqueio
SELECT COUNT(*)
FROM administrativo_strike
WHERE aluno_id = 'uuid-do-aluno'
  AND expira_em > NOW();

-- 4. Alunos bloqueados com strikes (usado em administrativo/views.py - lista_alunos)
-- Lista alunos bloqueados com seus strikes ativos
SELECT 
    u.id,
    u.first_name || ' ' || u.last_name AS nome,
    u.email,
    t.nome AS turma,
    COUNT(s.id) AS strikes_ativos
FROM accounts_usuario u
LEFT JOIN administrativo_turma t ON u.turma_id = t.id
LEFT JOIN administrativo_strike s ON u.id = s.aluno_id AND s.expira_em > NOW()
WHERE u.perfil = 'aluno'
  AND u.bloqueado = TRUE
GROUP BY u.id, t.nome
ORDER BY strikes_ativos DESC;

-- 5. Verificar se aluno já tem reserva ativa para uma refeição (usado em reservas/views.py - criar_reserva)
-- Impede duplicidade de reserva
SELECT EXISTS (
    SELECT 1
    FROM reservas_reserva
    WHERE aluno_id = 'uuid-do-aluno'
      AND refeicao_id = 'uuid-da-refeicao'
      AND status = 'ativa'
);

-- 6. Resumo do painel do refeitório (usado em administrativo/views.py - painel_refeitorio)
-- Métricas do dia: totais, confirmados e pendentes
SELECT 
    COUNT(*) AS total_reservas,
    COUNT(*) FILTER (WHERE status = 'concluida') AS confirmadas,
    COUNT(*) FILTER (WHERE status = 'ativa') AS pendentes
FROM reservas_reserva
WHERE refeicao_id IN (SELECT id FROM refeicoes_refeicao WHERE data = CURRENT_DATE);

-- 7. Pratos de uma refeição (usado em refeicoes/models.py - descricao_exibicao)
-- Busca pratos agrupados por categoria para exibir no cardápio
SELECT 
    p.categoria,
    p.nome,
    p.descricao
FROM refeicoes_refeicao_prato rp
JOIN refeicoes_prato p ON rp.prato_id = p.id
WHERE rp.refeicao_id = 'uuid-da-refeicao'
  AND p.ativo = TRUE
ORDER BY p.categoria, p.nome;