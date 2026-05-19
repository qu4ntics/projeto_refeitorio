# 🍽️ Reservaif — Sistema de Reservas de Refeições Escolares
 
Sistema web para gestão de reservas de refeições no refeitório escolar, desenvolvido com Django e PostgreSQL.
 
---
 
## 📋 Pré-requisitos
 
Antes de começar, certifique-se de ter instalado na sua máquina:
 
- [Python 3.12+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [PostgreSQL](https://www.postgresql.org/download/)
---
 
## 🚀 Configurando o projeto
 
### 1. Clonar o repositório
 
```bash
git clone https://github.com/reservaif/projeto_refeitorio.git
cd projeto_refeitorio
```
É recomendado clonar o repositório em um diretório fora do OneDrive, se ele for utilizado na sua máquina.
Deixar a aplicação dentro do OneDrive pode gerar problemas de conexão com o banco de dados.
 
### 2. Criar e ativar o ambiente virtual
 
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
 
**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```
 
> O terminal deve mostrar `(venv)` no início da linha após a ativação.
 
### 3. Instalar as dependências
 
```bash
pip install -r requirements.txt
```
 
### 4. Configurar as variáveis de ambiente
 
Copie o arquivo de exemplo e preencha com os seus dados:
 
**Windows:**
```bash
copy .env.example .env
```
 
**Linux/Mac:**
```bash
cp .env.example .env
```
 
Abra o arquivo `.env` e preencha os campos com a .env fornecida:
 
```env
SECRET_KEY=
DEBUG=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```
 
### 5. Criar o banco de dados no PostgreSQL
 
Abra o **pgAdmin** ou o terminal do PostgreSQL e execute o script para criar um banco local pré-definido.
 
> Inicialmente vamos trabalhar com bancos locais.
 
### 6. Aplicar as migrações
 
```bash
python manage.py migrate
```
 
### 7. Rodar o servidor
 
```bash
python manage.py runserver
```
 
Acesse no navegador: [http://localhost:8000](http://localhost:8000)
 
---
 
## 👤 Perfis de acesso
 
| Perfil | Descrição |
|---|---|
| `aluno` | Visualiza o cardápio e faz reservas |
| `nutricionista` | Gerencia refeições, vagas e configurações |
| `refeitorio` | Realiza a chamada e confirma presenças |
 
Para definir o perfil de um usuário, acesse o painel admin em [http://localhost:8000/django-admin](http://localhost:8000/django-admin).
 
---
 
## 🗂️ Estrutura do projeto
 
```
projeto_refeitorio/
├── accounts/          # Autenticação e perfis de usuário
├── refeicoes/         # Cardápio e controle de vagas
├── reservas/          # Fluxo de reserva e strikes
├── administrativo/    # Painel da nutricionista e refeitório
├── templates/         # Templates HTML globais
├── static/            # CSS, JS e imagens
├── .env.example       # Modelo de variáveis de ambiente
├── requirements.txt   # Dependências do projeto
└── manage.py
```
 
---
 
## 🔄 Fluxo de trabalho com Git
 
Nunca trabalhe direto na branch `main`. Crie uma branch para cada funcionalidade:
 
```bash
# Criar e entrar em uma nova branch
git checkout -b feat/nome-da-funcionalidade
 
# Após finalizar, adicionar e commitar
git add .
git commit -m "feat: descrição do que foi feito"
 
# Enviar para o GitHub
git push origin feat/nome-da-funcionalidade
```
 
Depois abra um **Pull Request** no GitHub para revisão antes de mergiar na `main`.
 
---
 
## 📝 Padrão de commits
 
Use prefixos para manter o histórico organizado:
 
| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `style:` | Alterações de CSS/HTML sem lógica |
| `refactor:` | Refatoração de código |
| `docs:` | Alterações em documentação |
| `chore:` | Configurações, dependências |
 
---
 
## ❓ Problemas comuns
 
**`Fatal error in launcher` ao usar pip:**
```bash
# Use python -m pip no lugar de pip diretamente
python -m pip install -r requirements.txt
```
 
**Erro de conexão com o banco:**
Verifique se o PostgreSQL está rodando e se os dados no `.env` estão corretos.
 
**`ModuleNotFoundError` ao rodar o servidor:**
Certifique-se de que o ambiente virtual está ativado (`(venv)` no terminal).
