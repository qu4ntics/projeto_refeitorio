# Documentação do Código

## Estrutura Geral
O projeto segue a arquitetura MTV (Model-Template-View) do Django, organizado em 4 apps:

- **accounts**: autenticação e gerenciamento de perfis.
- **refeicoes**: cardápio e pratos.
- **reservas**: lógica de reserva e cancelamento.
- **administrativo**: painéis da nutricionista e refeitório, presenças, strikes, notificações.

## Padrões e Boas Práticas
- **Nomenclatura**: snake_case para funções/variáveis, CamelCase para classes, nomes descritivos.
- **Comentários**: Docstrings em todas as funções e classes principais (ex: `Strike.save()`).
- **Validação**: Uso de `clean()` nos models e validações específicas nas views.
- **Segurança**: Decorator `@perfil_required` para controle de acesso; autenticação por e-mail via `EmailBackend`.
- **Transações**: Uso de `@transaction.atomic` em operações críticas (criar_reserva, cancelar_reserva, atualizar_status_reserva).
- **Otimização**: Uso de `select_related`, `prefetch_related` e `select_for_update` para evitar race conditions.
- **Mensagens**: Feedback ao usuário via `messages` do Django.

## Exemplo de Trecho Comentado (extraído de `reservas/views.py`)
```python
@login_required
@perfil_required('aluno')
@require_POST
@transaction.atomic
def criar_reserva(request, refeicao_id):
    """
    Cria uma reserva para o aluno autenticado após todas as validações:
    - aluno não bloqueado
    - refeição exige reserva
    - dentro da janela de reserva
    - vagas disponíveis
    - não há reserva ativa duplicada
    """
    refeicao = get_object_or_404(Refeicao.objects.select_for_update(), pk=refeicao_id)
    ...