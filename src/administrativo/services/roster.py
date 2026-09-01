"""Importação da lista de alunos autorizados a partir de um CSV.

A nutricionista envia uma planilha com os e-mails institucionais e as turmas dos
alunos. Apenas e-mails presentes nessa lista conseguem criar conta, e a turma da
conta passa a vir daqui.
"""

import csv
import io
import unicodedata
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from accounts.models import Usuario

from ..models import AlunoAutorizado, Turma

COLUNAS_EMAIL = {'email', 'e-mail', 'e mail', 'email institucional'}
COLUNAS_TURMA = {'turma', 'classe'}
COLUNAS_NOME = {'nome', 'nome completo', 'aluno'}


@dataclass
class ResultadoImport:
    criados: int = 0
    atualizados: int = 0
    removidos: int = 0
    contas_sincronizadas: int = 0
    turmas_criadas: int = 0
    total_linhas: int = 0
    erros: list = field(default_factory=list)  # list[tuple[int, str]]

    @property
    def tem_erros(self):
        return bool(self.erros)

    @property
    def processados(self):
        return self.criados + self.atualizados


def _sem_acento(texto):
    return unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()


def _normalizar_chave(texto):
    return _sem_acento(texto).strip().lower()


def _decodificar(arquivo):
    bruto = arquivo.read()
    if isinstance(bruto, str):
        return bruto
    for codificacao in ('utf-8-sig', 'latin-1'):
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return bruto.decode('utf-8', errors='replace')


def _detectar_separador(amostra):
    try:
        return csv.Sniffer().sniff(amostra, delimiters=';,').delimiter
    except csv.Error:
        return ';'


def _mapear_colunas(fieldnames):
    """Retorna (chave_email, chave_turma, chave_nome) conforme o cabeçalho real."""
    mapa = {}
    for original in fieldnames or []:
        chave = _normalizar_chave(original)
        if chave in COLUNAS_EMAIL:
            mapa['email'] = original
        elif chave in COLUNAS_TURMA:
            mapa['turma'] = original
        elif chave in COLUNAS_NOME:
            mapa['nome'] = original
    return mapa.get('email'), mapa.get('turma'), mapa.get('nome')


def _dominio_permitido(email):
    dominios = settings.ALUNO_EMAIL_DOMINIOS
    if not dominios:
        return True
    return email.rsplit('@', 1)[-1].lower() in dominios


def importar_roster(arquivo, *, substituir=False, atualizar_contas=True, criar_turmas=True):
    """Processa o CSV e aplica as mudanças. Linhas válidas entram mesmo que
    outras linhas contenham erros (importação parcial).

    Com ``criar_turmas=True`` (padrão), turmas citadas na planilha que ainda não
    existem são cadastradas automaticamente (turno matutino) antes de vincular os
    alunos.
    """
    resultado = ResultadoImport()

    conteudo = _decodificar(arquivo)
    if not conteudo.strip():
        resultado.erros.append((0, 'Arquivo vazio.'))
        return resultado

    separador = _detectar_separador(conteudo[:4096])
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=separador)
    col_email, col_turma, col_nome = _mapear_colunas(leitor.fieldnames)
    if not col_email or not col_turma:
        resultado.erros.append(
            (0, 'Cabeçalho inválido. Use as colunas "email" e "turma" (opcional: "nome").')
        )
        return resultado

    turmas_por_nome = {
        _normalizar_chave(t.nome): t for t in Turma.objects.all()
    }

    coletados = {}  # email -> (chave_turma, nome)
    turmas_a_criar = {}  # chave_turma -> nome exibido (1ª ocorrência na planilha)
    for indice, linha in enumerate(leitor, start=2):
        resultado.total_linhas += 1

        email = (linha.get(col_email) or '').strip().lower()
        nome_turma = (linha.get(col_turma) or '').strip()
        nome = (linha.get(col_nome) or '').strip() if col_nome else ''

        if not email and not nome_turma:
            continue  # linha em branco

        try:
            validate_email(email)
        except ValidationError:
            resultado.erros.append((indice, f'E-mail inválido: "{email}".'))
            continue

        if not _dominio_permitido(email):
            resultado.erros.append(
                (indice, f'E-mail fora do domínio institucional: "{email}".')
            )
            continue

        if not nome_turma:
            resultado.erros.append((indice, 'Turma não informada.'))
            continue
        if len(nome_turma) > 100:
            resultado.erros.append(
                (indice, f'Nome de turma muito longo: "{nome_turma[:40]}…".')
            )
            continue

        chave_turma = _normalizar_chave(nome_turma)
        if chave_turma not in turmas_por_nome:
            if not criar_turmas:
                resultado.erros.append(
                    (indice, f'Turma não encontrada: "{nome_turma}".')
                )
                continue
            turmas_a_criar.setdefault(chave_turma, nome_turma)

        if email in coletados:
            resultado.erros.append((indice, f'E-mail repetido na planilha: "{email}".'))
            continue

        coletados[email] = (chave_turma, nome)

    if not coletados:
        if not resultado.tem_erros:
            resultado.erros.append((0, 'Nenhuma linha válida encontrada.'))
        return resultado

    # Só cria turmas que sobraram vinculadas a alguma linha válida.
    chaves_usadas = {chave for chave, _ in coletados.values()}
    turmas_a_criar = {k: v for k, v in turmas_a_criar.items() if k in chaves_usadas}

    with transaction.atomic():
        for chave, nome_exibido in turmas_a_criar.items():
            turmas_por_nome[chave] = Turma.objects.create(nome=nome_exibido)
            resultado.turmas_criadas += 1

        for email, (chave_turma, nome) in coletados.items():
            _, criado = AlunoAutorizado.objects.update_or_create(
                email=email,
                defaults={'turma': turmas_por_nome[chave_turma], 'nome': nome},
            )
            if criado:
                resultado.criados += 1
            else:
                resultado.atualizados += 1

        if substituir:
            removidos, _ = (
                AlunoAutorizado.objects.exclude(email__in=coletados.keys()).delete()
            )
            resultado.removidos = removidos

        if atualizar_contas:
            contas = Usuario.objects.filter(
                perfil='aluno', email__in=coletados.keys()
            )
            for conta in contas:
                nova_turma = turmas_por_nome[coletados[conta.email.lower()][0]]
                if conta.turma_id != nova_turma.id:
                    conta.turma = nova_turma
                    conta.save(update_fields=['turma'])
                    resultado.contas_sincronizadas += 1

    return resultado
