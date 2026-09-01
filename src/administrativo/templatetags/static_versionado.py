"""
`{% static_v %}`: como `{% static %}`, mas com cache-busting em desenvolvimento.

Em produção o CompressedManifestStaticFilesStorage já põe hash no nome do
arquivo. Em desenvolvimento não há manifesto, e o navegador continuava servindo
CSS/JS antigos depois de cada alteração — dando a impressão de que a mudança
não tinha funcionado.
"""

import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(caminho):
    url = static(caminho)
    if not settings.DEBUG:
        return url

    absoluto = finders.find(caminho)
    if not absoluto:
        return url

    try:
        mtime = int(os.path.getmtime(absoluto))
    except OSError:
        # Arquivo sumiu entre o find e o stat: devolve a URL sem versão em vez
        # de derrubar a página.
        return url

    separador = '&' if '?' in url else '?'
    return f'{url}{separador}v={mtime}'
