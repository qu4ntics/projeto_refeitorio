from datetime import date

from django.test import TestCase

from administrativo.models import TipoRefeicao

from .forms import RefeicaoForm
from .models import Refeicao


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

    def test_form_preenche_data_na_edicao(self):
        TipoRefeicao.objects.filter(nome='almoco').update(ativo=True)
        refeicao = Refeicao.objects.create(
            data=date(2099, 3, 15),
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )
        form = RefeicaoForm(instance=refeicao)
        self.assertEqual(form['data'].value(), date(2099, 3, 15))
        self.assertIn('2099-03-15', str(form['data']))
