# Requisitos do Sistema – Reserva de Refeições Escolares

## Requisitos Funcionais (RF)

### Módulo Aluno
| Código | Descrição |
|--------|-----------|
| RF01   | O aluno deve visualizar o cardápio da semana com pratos, horários e vagas disponíveis. |
| RF02   | O aluno deve reservar uma refeição dentro da janela configurada. |
| RF03   | O aluno só pode ter uma reserva ativa por refeição. |
| RF04   | O aluno deve poder cancelar sua reserva até o prazo definido (minutos_cancelamento). |
| RF05   | O aluno com conta bloqueada (2 strikes ativos) não pode reservar. |
| RF06   | O aluno recebe notificações sobre strikes e bloqueios. |
| RF07   | O aluno visualiza suas reservas ativas e histórico. |

### Módulo Nutricionista
| Código | Descrição |
|--------|-----------|
| RF08   | Cadastrar, editar e excluir refeições (data, tipo, limite, pratos). |
| RF09   | Gerenciar pratos (criar, editar, excluir logicamente). |
| RF10   | Configurar janela de reserva por tipo de refeição (horários). |
| RF11   | Visualizar lista de alunos com reservas ativas. |
| RF12   | Desbloquear alunos manualmente. |
| RF13   | Receber notificação quando vagas se esgotarem. |
| RF14   | Cancelar reservas de qualquer aluno a qualquer momento. |

### Módulo Refeitório
| Código | Descrição |
|--------|-----------|
| RF15   | Realizar chamada (confirmar presença) para cada reserva. |
| RF16   | Ao marcar falta, gerar strike automaticamente. |
| RF17   | Finalizar/reabrir chamada do dia. |

### Módulo Geral
| Código | Descrição |
|--------|-----------|
| RF18   | Autenticação com login (e-mail) e senha, diferenciação por perfil. |
| RF19   | Controle de acesso via decorators (@perfil_required). |
| RF20   | Registro de data/hora em todas as ações (reserva, cancelamento, presença, strike). |
| RF21   | Impedir reserva se refeição lotada ou aluno bloqueado. |

## Requisitos Não Funcionais (RNF)

| Código | Descrição |
|--------|-----------|
| RNF01  | Desenvolvido com Django 6.0+ e Python 3.12. |
| RNF02  | Banco de dados PostgreSQL (ou SQLite para desenvolvimento). |
| RNF03  | Interface responsiva com HTML/CSS/JS (Django Templates). |
| RNF04  | Tempo de resposta < 2s para operações comuns. |
| RNF05  | Código segue PEP8, com docstrings e comentários. |
| RNF06  | Transações ACID em operações críticas (reserva, presença, strike). |
| RNF07  | Senhas com hash (PBKDF2). |
| RNF08  | Versionamento no GitHub com histórico de commits. |
| RNF09  | Documentação inclui diagramas UML e scripts SQL. |
| RNF10  | Configurações sensíveis via variáveis de ambiente (.env). |