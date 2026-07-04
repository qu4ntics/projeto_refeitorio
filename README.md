# ReservaIF — Sistema de Reservas de Refeições Escolares

Sistema web para gestão de reservas de refeições no refeitório escolar. Desenvolvido com **Django 6** e **PostgreSQL**, o ReservaIF conecta alunos, nutricionistas e equipe do refeitório em um fluxo único: visualizar cardápio, reservar vagas, realizar chamada e aplicar strikes por faltas.

---

## Funcionalidades

### Aluno
- Visualizar cardápio da semana com pratos, horários e vagas disponíveis
- Reservar e cancelar refeições dentro das janelas configuradas
- Acompanhar reservas ativas, histórico e strikes recebidos
- Receber notificações sobre strikes e bloqueios

### Nutricionista
- Gerenciar refeições, pratos e cardápio semanal
- Configurar janelas de reserva e prazos de cancelamento por tipo de refeição
- Visualizar alunos, turmas e lista de bloqueados
- Desbloquear alunos manualmente

### Refeitório
- Realizar chamada e confirmar presença dos alunos
- Encerrar e reabrir chamadas conforme horário da refeição
- Aplicar strikes automaticamente quando há falta

---

## Tecnologias

| Camada        | Tecnologia                          |
|---------------|-------------------------------------|
| Backend       | Python 3.12+, Django 6.0            |
| Banco de dados| PostgreSQL                          |
| Frontend      | Django Templates, HTML, CSS, JS     |
| Deploy        | Gunicorn, WhiteNoise, Render        |

---

## Estrutura do repositório

```
projeto_refeitorio/
├── docs/              # Documentação, diagramas e requisitos
├── scripts/           # Scripts SQL (DDL, DML, triggers)
└── src/               # Aplicação Django
    ├── accounts/      # Autenticação e perfis de usuário
    ├── refeicoes/     # Cardápio e controle de vagas
    ├── reservas/      # Fluxo de reserva
    ├── administrativo/# Painéis da nutricionista e refeitório
    ├── reservaif/     # Configurações do projeto Django
    ├── templates/     # Templates HTML
    ├── static/        # CSS, JS e imagens
    ├── manage.py
    ├── requirements.txt
    └── build.sh       # Script de build para deploy
```

---

## Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [PostgreSQL](https://www.postgresql.org/download/)

> Evite clonar o projeto dentro de pastas sincronizadas pelo OneDrive — isso pode causar problemas de conexão com o banco de dados.

---

## Como executar localmente

Todos os comandos abaixo assumem que você está na pasta `src/` do projeto.

### 1. Clonar o repositório

```bash
git clone https://github.com/reservaif/projeto_refeitorio.git
cd projeto_refeitorio/src
```

### 2. Criar e ativar o ambiente virtual

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

O terminal deve exibir `(venv)` no início da linha.

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na pasta `src/` com as variáveis abaixo:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True

DB_NAME=reservaif
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=ReservaIF <no-reply@reservaif.local>
```

### 5. Criar o banco de dados

Crie um banco PostgreSQL com o nome definido em `DB_NAME`. Opcionalmente, os scripts em `scripts/` podem ser usados para referência da estrutura SQL.

### 6. Aplicar migrações

```bash
python manage.py migrate
```

### 7. (Opcional) Criar usuários de teste

Cria um usuário de cada perfil (aluno, nutricionista e refeitório) com senha padrão `teste12345`:

```bash
python manage.py criar_usuarios_teste
```

| Perfil        | E-mail                  |
|---------------|-------------------------|
| Aluno         | aluno@teste.local       |
| Nutricionista | nutri@teste.local       |
| Refeitório    | refeitorio@teste.local  |

O login é feito pelo **e-mail**, não pelo username.

### 8. Iniciar o servidor

```bash
python manage.py runserver
```

Acesse: [http://localhost:8000](http://localhost:8000)

O painel administrativo Django fica em [http://localhost:8000/django-admin](http://localhost:8000/django-admin).

---

## Perfis de acesso

| Perfil          | Descrição                                              |
|-----------------|--------------------------------------------------------|
| `aluno`         | Visualiza cardápio, faz reservas e acompanha strikes   |
| `nutricionista` | Gerencia refeições, pratos, turmas e configurações     |
| `refeitorio`    | Realiza chamada e confirma presenças                   |

---

## Deploy (Render)

O código da aplicação está em `src/`. No painel do Render, configure:

| Campo            | Valor                              |
|------------------|------------------------------------|
| **Root Directory** | `src`                            |
| **Build Command**  | `./build.sh`                     |
| **Start Command**  | `gunicorn reservaif.wsgi:application` |

---

## Documentação adicional

- [Requisitos funcionais](docs/requisitos.md)
- [Diagrama de casos de uso](docs/diagrama_casos_de_uso.md)
- [Diagrama de classes](docs/diagrama_classes.md)
- [Modelo lógico do banco](docs/modelo_logico.md)

---

## Problemas comuns

**`Fatal error in launcher` ao usar pip:**

```bash
python -m pip install -r requirements.txt
```

**Erro de conexão com o banco:**

Verifique se o PostgreSQL está em execução e se os valores do `.env` estão corretos.

**`ModuleNotFoundError` ao rodar o servidor:**

Confirme que o ambiente virtual está ativado (`(venv)` visível no terminal) e que você está na pasta `src/`.

---

## Licença

Projeto acadêmico — Instituto Federal.
