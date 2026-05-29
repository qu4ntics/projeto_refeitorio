from django.contrib.auth.views import LoginView
from django.urls import reverse

REDIRECT_POR_PERFIL = {
    'aluno': 'refeicoes:homepage',
    'nutricionista': 'administrativo:painel_nutricionista',
    'refeitorio': 'administrativo:painel_refeitorio',
}


class LoginPerfilView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        perfil = getattr(self.request.user, 'perfil', 'aluno')
        url_name = REDIRECT_POR_PERFIL.get(perfil, 'refeicoes:homepage')
        return reverse(url_name)
