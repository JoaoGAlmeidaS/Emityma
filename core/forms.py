"""Formulários de validação dos dados enviados pelos templates.

Os templates mantêm o HTML próprio; os formulários são usados apenas para
validar e converter `request.POST` antes de gravar no banco.
"""

from django import forms

from .access import NIVEIS_ACESSO
from .models import Cultura, Fazenda, Plantio, Talhao, Tarefa

UFS = (
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'), ('BA', 'Bahia'),
    ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'),
    ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
    ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'),
    ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'),
    ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'),
    ('SE', 'Sergipe'), ('TO', 'Tocantins'),
)


class FazendaForm(forms.ModelForm):
    uf = forms.ChoiceField(choices=UFS, label='UF')
    tamanho = forms.FloatField(min_value=0.01)

    class Meta:
        model = Fazenda
        fields = ['nome', 'proprietario', 'uf', 'cidade', 'email', 'telefone', 'tamanho']


class TalhaoForm(forms.ModelForm):
    area = forms.DecimalField(max_digits=9, decimal_places=2, min_value=0.01)

    class Meta:
        model = Talhao
        fields = ['nome', 'area']


class CulturaForm(forms.ModelForm):
    produtividade_media = forms.FloatField(min_value=0)

    class Meta:
        model = Cultura
        fields = ['nome', 'tp_cultura', 'descricao', 'produtividade_media']


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = ['titulo', 'descricao', 'prioridade']


class PlantioForm(forms.ModelForm):
    class Meta:
        model = Plantio
        fields = ['cultura', 'talhao', 'dt_plantio', 'dt_colheitaPrevista']

    def __init__(self, *args, fazenda, **kwargs):
        super().__init__(*args, **kwargs)
        # Só permite culturas e talhões da própria fazenda.
        self.fields['cultura'].queryset = Cultura.objects.filter(fazenda=fazenda)
        self.fields['talhao'].queryset = Talhao.objects.filter(fazenda=fazenda)

    def clean(self):
        dados = super().clean()
        plantio, colheita = dados.get('dt_plantio'), dados.get('dt_colheitaPrevista')
        if plantio and colheita and colheita < plantio:
            self.add_error('dt_colheitaPrevista', 'A colheita prevista não pode ser anterior ao plantio.')
        return dados


class NivelAcessoForm(forms.Form):
    nivel_acesso = forms.ChoiceField(choices=[(n, n) for n in NIVEIS_ACESSO])


def resumo_erros(form):
    """Junta os erros de um formulário em uma frase para `messages.error`."""
    partes = []
    for campo, erros in form.errors.items():
        rotulo = form.fields[campo].label if campo in form.fields else ''
        texto = ' '.join(erros)
        partes.append(f'{rotulo}: {texto}' if rotulo else texto)
    return 'Não foi possível salvar. ' + ' '.join(partes)
