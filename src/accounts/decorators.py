from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from accounts.views import REDIRECT_POR_PERFIL


def perfil_required(*perfis_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.perfil not in perfis_permitidos:
                url_name = REDIRECT_POR_PERFIL.get(
                    request.user.perfil, 'refeicoes:homepage'
                )
                return render(
                    request,
                    'accounts/403.html',
                    {
                        'mensagem': 'Você não tem permissão para acessar esta página.',
                        'url_inicio': reverse(url_name),
                    },
                    status=403,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
