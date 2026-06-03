# Visão Geral

**Tema do Projeto**

O tema deste projeto concentra-se no desenvolvimento de um protótipo de aplicação web para a gestão de reservas de refeições escolares. O foco principal é democratizar o acesso à alimentação, substituindo o atual modelo de ordem de chegada, que inviabiliza o acesso dos alunos do turno da tarde, por um sistema de reserva antecipada. A solução visa garantir que todos os estudantes tenham as mesmas oportunidades de garantir sua refeição, operando por meio de uma interface simplificada que assegura uma distribuição justa das vagas sem a necessidade de processar dados sensíveis, mantendo-se em total conformidade com a LGPD.

**Problema que será resolvido**

O problema central a ser resolvido por este projeto é a desigualdade no acesso às refeições escolares, gerada pelo atual modelo de distribuição baseado exclusivamente em ordem de chegada. Como o limite diário de pratos é esgotado rapidamente pelos primeiros estudantes que acessam o refeitório, alunos de outros horários, especialmente os do turno da tarde, são sistematicamente prejudicados e, com frequência, ficam sem a oportunidade de almoçar. A ausência de um mecanismo de reserva antecipada cria um cenário de exclusão, transformando o acesso à alimentação em uma disputa desleal de horários e impedindo uma distribuição justa, democrática e planejada das vagas disponíveis para toda a comunidade estudantil. Além disso, visando aprimorar continuamente essa equidade, prevê-se que em versões futuras do sistema sejam estudadas e implementadas funcionalidades específicas para a priorização de alunos em regime de contraturno, garantindo que aqueles com maior permanência no campus tenham seu acesso à refeição assegurado.

**Público-alvo**

O público-alvo deste projeto é composto por dois grupos principais. O primeiro abrange os estudantes do campus, em especial aqueles prejudicados pelo atual modelo de ordem de chegada, como os alunos do turno da tarde que necessitam do acesso a refeições no campus, que utilizarão a plataforma para reservar sua refeição de forma justa e acessível. O segundo grupo é formado pela equipe de gestão e nutrição do refeitório, que utilizará a interface administrativa do sistema para cadastrar cardápios, controlar o limite diário de vagas e otimizar o planejamento da oferta de refeições.

**Funcionalidades principais**

**1. Acesso do Estudante**

Este módulo foca na acessibilidade e agilidade, permitindo que qualquer aluno reserve sua refeição sem barreiras tecnológicas.

- **Visualização do Cardápio:** Exibição clara das refeições disponíveis para o dia ou semana, incluindo o prato principal e o número de vagas ainda abertas.
- **Reserva:** Na interface do cardápio, o aluno visualizará um *card* com a refeição do dia contendo o botão 'Reservar', o que simplifica todo o processo.
- **Confirmação de Reserva:** Tela de sucesso imediata gerada após o envio do formulário, servindo como feedback visual para garantir ao estudante que sua vaga foi contabilizada.
- **Bloqueio Automático por Lotação:** Quando a refeição atinge o limite máximo estipulado pela gestão, o sistema impossibilita novas reservas automaticamente.

**2. Acesso Administrativo**

Este módulo é o painel de controle da equipe do refeitório, focado em planejamento e gestão de estoque.

- **Autenticação Segura:** Acesso restrito por meio de login (Ex: e-mail e senha) exclusivo para a equipe gestora.
- **Gestão de Cardápios e Ofertas:** Funcionalidade para criar, editar ou excluir refeições do sistema, definindo a data, a descrição do prato (principal, complemento, salada e etc.), tipo da refeição (café, lanche da manhã, almoço, lanche da tarde e jantar) e limite de reservas disponíveis.
- **Listagem de Reservados:** Tabela detalhada listando os nomes e turmas dos alunos que garantiram a refeição.

**Tecnologias pretendidas**

- HTML
- CSS
- Javascript
- Django
- PostgreSQL

---

# Arquitetura do Sistema

Sistema de Gestão de Reservas de Refeições Escolares

Versão 1.0 • 16/05/2026

## 1. Visão Geral

O sistema utiliza o padrão MTV (Model-Template-View) do Django com renderização server-side via Django Templates. Não há separação de frontend e backend como API REST — o servidor monta o HTML completo e entrega ao navegador a cada requisição.

Essa abordagem foi escolhida por adequar-se ao escopo do protótipo, ao stack declarado (HTML, CSS, JS e Django) e por reduzir a complexidade de configuração e depuração durante o desenvolvimento inicial.

## 2. Stack Tecnológica

- **Python 3 + Django:** framework principal, lógica de negócio, ORM e renderização de templates
- **PostgreSQL:** banco de dados relacional para persistência de todos os dados
- **HTML + CSS + JavaScript:** interface do usuário renderizada pelo servidor via Django Templates
- **Django Auth:** sistema de autenticação nativo do Django, customizado para suportar os três perfis de usuário

## 3. Fluxo de uma Requisição

1. O navegador envia uma requisição HTTP (GET ou POST) para o servidor Django.
2. O arquivo urls.py do app correspondente roteia a requisição para a view correta.
3. A view executa a lógica de negócio, consultando ou gravando dados via models.py (ORM do Django).
4. O ORM traduz as operações Python em queries SQL e se comunica com o PostgreSQL.
5. A view passa os dados para um template HTML que é renderizado e retornado ao navegador como resposta.

## 4. Apps Django

O projeto é dividido em 4 apps, cada um com responsabilidade única e bem delimitada. Essa separação facilita a manutenção, os testes e a evolução independente de cada módulo.

| **App** | **Responsabilidade** | **Principais arquivos** |
|---|---|---|
| accounts | Autenticação e gerenciamento de perfis de usuário | models.py, views.py, urls.py, forms.py, templates/ |
| refeicoes | Cardápio, listagem de refeições e controle de vagas | models.py, views.py, urls.py, templates/ |
| reservas | Fluxo de reserva, cancelamento, strikes e janela de horário | models.py, views.py, urls.py, forms.py, templates/ |
| administrativo | Painel da nutricionista, chamada do refeitório e configurações | models.py, views.py, urls.py, forms.py, templates/ |

**4.1 accounts**

Responsável por tudo relacionado a usuários. Contém o modelo Usuario customizado (estende AbstractUser do Django) que unifica aluno, nutricionista e refeitório em um único perfil identificado pelo campo perfil. Gerencia login, logout e cadastro de novos alunos.

**4.2 refeicoes**

Responsável pelo cardápio. Exibe as refeições disponíveis, o número de vagas restantes e o detalhe de cada prato. Contém o modelo Refeicao com os campos data, tipo, descrição, limite_vagas e exige_reserva.

**4.3 reservas**

Núcleo do sistema para o aluno. Gerencia a criação e o cancelamento de reservas, valida se a requisição está dentro da janela de horário configurada e controla o acúmulo e expiração de strikes. Contém os modelos Reserva e Strike.

**4.4 administrativo**

Painel de gestão com acesso restrito por perfil. A nutricionista acessa o CRUD de refeições e a configuração da janela de reservas. O perfil do refeitório acessa a tela de chamada para confirmar presenças e registrar faltas. Contém os modelos Presenca e ConfigReserva.

## 5. Principais Rotas

Abaixo estão as rotas principais do sistema organizadas por app e perfil de acesso.

| **Método** | **Rota** | **View** | **Perfil** |
|---|---|---|---|
| GET | / | refeicoes.views.cardapio | Aluno |
| GET/POST | /reservas/criar/\<id\>/ | reservas.views.criar_reserva | Aluno |
| POST | /reservas/cancelar/\<id\>/ | reservas.views.cancelar_reserva | Aluno |
| GET | /accounts/login/ | accounts.views.login | Todos |
| GET/POST | /accounts/cadastro/ | accounts.views.cadastro | Público |
| GET | /admin/refeicoes/ | administrativo.views.listar_refeicoes | Nutricionista |
| GET/POST | /admin/refeicoes/nova/ | administrativo.views.criar_refeicao | Nutricionista |
| GET/POST | /admin/refeicoes/\<id\>/editar/ | administrativo.views.editar_refeicao | Nutricionista |
| GET/POST | /admin/config/ | administrativo.views.configurar_janela | Nutricionista |
| GET | /admin/chamada/\<id\>/ | administrativo.views.chamada | Refeitório |
| POST | /admin/presenca/confirmar/ | administrativo.views.confirmar_presenca | Refeitório |

## 6. Estrutura de Pastas

Estrutura recomendada para o projeto Django:

```
reservas_escolares/          <- pasta raiz do projeto
  manage.py
  reservas_escolares/        <- configurações do projeto
    settings.py
    urls.py
    wsgi.py
  accounts/                  <- app de autenticação
    models.py
    views.py
    urls.py
    forms.py
    templates/accounts/
  refeicoes/                 <- app de cardápio
    models.py
    views.py
    urls.py
    templates/refeicoes/
  reservas/                  <- app de reservas
    models.py
    views.py
    urls.py
    forms.py
    templates/reservas/
  administrativo/            <- app de gestão
    models.py
    views.py
    urls.py
    forms.py
    templates/administrativo/
  static/                    <- CSS, JS e imagens globais
  templates/                 <- base.html e layouts globais
```

*Documento gerado em 16/05/2026. Sujeito a revisões conforme o desenvolvimento do sistema.*

---

# Regras de Negócio

Sistema de Gestão de Reservas de Refeições Escolares

Versão 1.0 • 16/05/2026

## 1. Aluno

- **Cadastro:** O aluno cria conta com nome, e-mail e senha.
- **Identificação:** Nome e turma são exibidos como identificação pública no sistema (sem dados sensíveis, em conformidade com a LGPD).
- **Limite por refeição:** Um aluno pode fazer apenas uma reserva por refeição.
- **Múltiplas refeições:** Um aluno pode reservar mais de uma refeição no mesmo dia, desde que cada uma exija reserva.
- **Bloqueio:** Alunos com conta bloqueada não podem realizar novas reservas.

## 2. Refeição e Cardápio

- **Cadastro semanal:** A nutricionista cadastra as refeições da semana inteira toda segunda-feira.
- **Tipos:** Tipos de refeição disponíveis: café, lanche da manhã, almoço, lanche da tarde e jantar.
- **Exige Reserva:** Cada refeição possui um campo 'Exige Reserva' (sim/não). Refeições marcadas como não obrigatórias são exibidas apenas para fins informativos, sem gerar reservas.
- **Limite de vagas:** O limite de vagas por refeição é definido pela nutricionista no momento do cadastro.
- **Edição:** O cardápio pode ser editado mesmo após já existirem reservas.

> ⚠️ O limite de vagas só pode ser aumentado após existirem reservas. Reduções são permitidas apenas até o número de reservas já confirmadas. Exemplo: 30 vagas com 18 reservas → limite mínimo possível é 18.

## 3. Reserva

### 3.1 Janela de Reserva

- **Período:** O aluno pode reservar refeições do dia seguinte dentro de uma janela de tempo configurável pela nutricionista.
- **Exemplo:** Exemplo de configuração atual: a partir das 15h30 do dia anterior até as 9h30 do próprio dia da refeição.
- **Configuração:** Os horários de abertura e encerramento das reservas são definidos e ajustados pela nutricionista.

### 3.2 Cancelamento

- **Prazo para o aluno:** O aluno pode cancelar sua reserva até 1 hora antes do horário limite de reserva daquela refeição.
- **Cancelamento pelo admin:** Admins de qualquer perfil podem cancelar a reserva de um aluno sem restrição de horário.

### 3.3 Bloqueio por Lotação

- **Automático:** Quando uma refeição atinge o limite máximo de vagas, o sistema bloqueia automaticamente novas reservas.
- **Alerta:** A nutricionista recebe uma notificação sempre que as vagas de uma refeição são esgotadas.

## 4. Presença e Strike

- **Chamada:** A confirmação de presença é feita pelo perfil do Refeitório na porta, como uma 'chamada' no momento da refeição.
- **Aplicação:** Se o aluno não comparecer à refeição reservada, recebe 1 strike.
- **Bloqueio:** Com 2 strikes acumulados, a conta do aluno é bloqueada permanentemente.
- **Desbloqueio:** O bloqueio só é removido manualmente pela nutricionista.
- **Expiração:** Cada strike expira automaticamente após 1 mês da data em que foi aplicado.

> ⚠️ Strikes expirados não contam para o limite de 2. Exemplo: aluno leva 1 strike em maio → expira em junho → pode levar mais 1 strike sem ser bloqueado.

## 5. Perfis Administrativos

O sistema possui dois perfis administrativos com permissões distintas:

- **Nutricionista:** Responsável pelo planejamento e configuração do sistema.
- **Refeitório (Cozinheiras):** Responsável pela operação no refeitório, confirmação de presença e aplicação de strikes.

| **Permissão** | **Nutricionista** | **Refeitório** |
|---|---|---|
| Cadastrar/editar refeições | ✅ | ❌ |
| Definir limite de vagas | ✅ | ❌ |
| Configurar janela de reserva | ✅ | ❌ |
| Cancelar reserva de aluno | ✅ | ✅ |
| Realizar chamada / confirmar presença | ❌ | ✅ |
| Aplicar strike | ❌ | ✅ |
| Desbloquear aluno | ✅ | ❌ |
| Receber alertas de vagas esgotadas | ✅ | ❌ |

*Documento gerado em 16/05/2026. Sujeito a revisões conforme o desenvolvimento do sistema.*

---

# Modelagem de Dados

Sistema de Gestão de Reservas de Refeições Escolares

Versão 1.0 • 16/05/2026

## Visão Geral

O sistema é composto por 6 entidades principais que cobrem os fluxos de reserva, presença e configuração. Todas as entidades utilizam UUID como chave primária para garantir unicidade e facilitar integração futura.

Relações principais: USUARIO faz RESERVA em REFEICAO. RESERVA gera PRESENCA. PRESENCA origina STRIKE. USUARIO do perfil nutricionista cria CONFIG_RESERVA.

## USUARIO

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único do usuário |
| nome | string | Nome completo do usuário |
| email | string | Email de acesso, único por usuário |
| senha_hash | string | Senha armazenada com hash seguro |
| turma | string | Turma do aluno (apenas para perfil aluno) |
| perfil | string | Tipo do usuário: aluno, nutricionista ou refeitorio |
| bloqueado | boolean | Indica se o aluno está bloqueado por 2 strikes |
| criado_em | timestamp | Data e hora de criação da conta |

Centraliza todos os perfis do sistema em uma única tabela. O campo perfil diferencia aluno, nutricionista e refeitório. O campo bloqueado controla se o aluno pode fazer reservas. A turma é exibida na listagem de reservados para o admin, sem armazenar dados sensíveis além do necessário pela LGPD.

## REFEICAO

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único da refeição |
| data | date | Data em que a refeição será servida |
| tipo | string | Tipo da refeição: cafe, lanche_manha, almoco, lanche_tarde, jantar |
| limite_vagas | integer | Número máximo de reservas permitidas |
| exige_reserva | boolean | Se falso, a refeição é apenas informativa, sem gerar reservas |
| criado_em | timestamp | Data e hora de cadastro da refeição |

Representa cada refeição cadastrada pela nutricionista. O campo tipo armazena café, lanche da manhã, almoço, lanche da tarde ou jantar. O campo exige_reserva distingue refeições que geram reservas das que são apenas informativas. O limite_vagas segue a regra de não poder ser reduzido abaixo do número de reservas já existentes.

## RESERVA

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único da reserva |
| aluno_id | uuid (FK) | Referência ao usuário com perfil aluno |
| refeicao_id | uuid (FK) | Referência à refeição reservada |
| status | string | Estado da reserva: ativa, cancelada ou concluida |
| reservado_em | timestamp | Data e hora em que a reserva foi feita |
| cancelado_em | timestamp | Data e hora do cancelamento (nulo se não cancelada) |

Liga um aluno a uma refeição. O campo status pode assumir os valores ativa, cancelada ou concluída. O campo cancelado_em é preenchido apenas quando a reserva é cancelada, seja pelo aluno dentro do prazo ou pelo admin.

## PRESENCA

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único do registro de presença |
| reserva_id | uuid (FK) | Referência à reserva correspondente |
| confirmado_por | uuid (FK) | Usuário do perfil refeitório que fez a chamada |
| compareceu | boolean | Verdadeiro se o aluno compareceu, falso se faltou |
| confirmado_em | timestamp | Data e hora da confirmação de presença |

Gerada no momento da chamada feita pelo perfil do refeitório na porta. O campo compareceu recebe verdadeiro se o aluno foi confirmado ou falso se não compareceu, o que dispara a criação de um strike. O campo confirmado_por referencia o usuário do perfil refeitório que realizou a chamada.

## STRIKE

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único do strike |
| aluno_id | uuid (FK) | Referência ao aluno que recebeu o strike |
| presenca_id | uuid (FK) | Referência ao registro de presença que originou o strike |
| aplicado_em | timestamp | Data e hora em que o strike foi aplicado |
| expira_em | timestamp | Data de expiração do strike (aplicado_em + 30 dias) |

Vinculado ao aluno que o recebeu e à presença que o originou, permitindo rastrear exatamente qual falta gerou o strike. O campo expira_em é calculado automaticamente como aplicado_em mais 30 dias. O sistema deve considerar apenas strikes não expirados ao verificar se o aluno deve ser bloqueado.

## PRATO

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único do prato |
| nome | string | Nome do prato (Ex: frango grelhado) |
| descricao | string | Descrição opcional do prato |
| categoria | string | Papel do prato: principal, complemento, salada, sobremesa |
| criado_em | timestamp | Data de cadastro |

Armazena os pratos cadastrados pela nutricionista. O campo categoria define o papel do prato no cardápio — principal, complemento, salada ou sobremesa — e é utilizado para agrupar os pratos na montagem de uma refeição. O campo descrição é opcional e pode ser usado para detalhar o modo de preparo ou ingredientes.

## REFEICAO_PRATO

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único |
| refeicao_id | uuid (FK) | Refeição à qual o prato pertence |
| prato_id | uuid (FK) | Prato selecionado |

Liga uma refeição aos pratos que a compõem. Cada registro associa um prato a uma refeição, permitindo que o mesmo prato apareça em múltiplas refeições sem precisar ser recadastrado. A descrição da refeição é montada a partir da combinação dos pratos vinculados, agrupados pela categoria definida em cada prato.

## CONFIG_RESERVA

| **Campo** | **Tipo** | **Descrição** |
|---|---|---|
| id | uuid (PK) | Identificador único da configuração |
| criado_por | uuid (FK) | Referência à nutricionista que definiu a configuração |
| abertura | time | Horário de início do período de reservas (ex: 15:30) |
| encerramento | time | Horário de encerramento das reservas (ex: 09:30) |
| minutos_cancelamento | integer | Minutos antes do encerramento em que o cancelamento é permitido |
| vigente_desde | timestamp | Data e hora a partir da qual esta configuração está ativa |

Guarda a configuração da janela de reservas definida pela nutricionista. Os campos abertura e encerramento são os horários limite. O campo minutos_cancelamento define com quantos minutos de antecedência ao encerramento o aluno ainda pode cancelar. O campo vigente_desde permite manter um histórico de configurações.

*Documento modificado em 26/05/2026. Sujeito a revisões conforme o desenvolvimento do sistema.*