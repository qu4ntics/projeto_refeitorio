from django.apps import AppConfig


class RefeicoesConfig(AppConfig):
    name = 'refeicoes'

    def ready(self):
        import refeicoes.signals  # noqa: F401
