from django.test import TestCase

from administrativo.models import TipoRefeicao

from .forms import RefeicaoForm


class RefeicaoFormTipoTests(TestCase):
    def test_form_mostra_apenas_tipos_habilitados(self):
        TipoRefeicao.objects.filter(nome='almoco').update(ativo=True)
        TipoRefeicao.objects.exclude(nome='almoco').update(ativo=False)

        form = RefeicaoForm()
        codigos = [c[0] for c in form.fields['tipo'].choices if c[0]]
        self.assertEqual(codigos, ['almoco'])

    def test_form_rejeita_tipo_nao_habilitado(self):
        TipoRefeicao.objects.update(ativo=False)

        form = RefeicaoForm(data={
            'data': '2099-01-15',
            'tipo': 'almoco',
            'limite_vagas': 50,
            'exige_reserva': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('tipo', form.errors)
