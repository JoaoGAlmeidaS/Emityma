import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.access import NIVEL_ADMIN, SESSION_KEY
from core.management.commands.build_pages import normalizar_base

from .models import Fazenda, UsuarioFazenda
from usuario.models import Usuario


class FazendaTests(TestCase):
    def dados(self, nome):
        return dict(nome=nome, proprietario='Fulano', uf='MT', cidade='Cuiabá',
                    email='contato@exemplo.com', telefone='0000', tamanho=10)

    def test_slug_unico_para_nomes_iguais(self):
        primeira = Fazenda.objects.create(**self.dados('Boa Vista'))
        segunda = Fazenda.objects.create(**self.dados('Boa Vista'))
        self.assertEqual(primeira.slug, 'boa-vista')
        self.assertEqual(segunda.slug, 'boa-vista-2')

    def test_criar_fazenda_vincula_usuario_como_administrador(self):
        usuario = Usuario(usuario_nome='Ana', usuario_email='ana@exemplo.com')
        usuario.definir_senha('colheita-segura-2025')
        usuario.save()
        sessao = self.client.session
        sessao[SESSION_KEY] = usuario.usuario_id
        sessao.save()

        resposta = self.client.post(reverse('cadastrar_fazenda'), self.dados('Santa Luzia'))

        fazenda = Fazenda.objects.get(nome='Santa Luzia')
        self.assertRedirects(resposta, reverse('dashboard_home', kwargs={'slug': fazenda.slug}))
        vinculo = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
        self.assertEqual(vinculo.nivel_acesso, NIVEL_ADMIN)

    def test_criar_fazenda_com_dados_invalidos_mostra_erros(self):
        usuario = Usuario(usuario_nome='Ana', usuario_email='ana@exemplo.com')
        usuario.definir_senha('colheita-segura-2025')
        usuario.save()
        sessao = self.client.session
        sessao[SESSION_KEY] = usuario.usuario_id
        sessao.save()

        resposta = self.client.post(reverse('cadastrar_fazenda'), {**self.dados('X'), 'tamanho': '-5', 'uf': 'ZZ'})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Corrija os campos')
        self.assertFalse(Fazenda.objects.exists())


class SeedDemoTests(TestCase):
    def test_seed_e_idempotente_e_gera_dados_consistentes(self):
        from core.management.commands.seed_demo import DEMO_EMAIL, DEMO_SENHA, FAZENDAS, USUARIOS
        from core.models import Plantio, Tarefa

        call_command('seed_demo', stdout=io.StringIO())
        call_command('seed_demo', stdout=io.StringIO())

        self.assertEqual(Usuario.objects.count(), len(USUARIOS))
        self.assertEqual(Fazenda.objects.count(), len(FAZENDAS))
        self.assertTrue(Usuario.objects.get(usuario_email=DEMO_EMAIL).verificar_senha(DEMO_SENHA))
        self.assertEqual(
            Plantio.objects.count(), sum(len(f['plantios']) for f in FAZENDAS))
        self.assertEqual(Tarefa.objects.count(), sum(len(f['tarefas']) for f in FAZENDAS))
        # Todo plantio usa talhão e cultura da mesma fazenda.
        for plantio in Plantio.objects.select_related('talhao', 'cultura'):
            self.assertEqual(plantio.talhao.fazenda_id, plantio.cultura.fazenda_id)
        # Usuário demo tem um nível diferente em cada fazenda.
        niveis = set(UsuarioFazenda.objects.filter(usuario__usuario_email=DEMO_EMAIL).values_list('nivel_acesso', flat=True))
        self.assertEqual(len(niveis), 3)


class BuildPagesTests(TestCase):
    def test_normalizar_base(self):
        self.assertEqual(normalizar_base(''), '/')
        self.assertEqual(normalizar_base('/'), '/')
        self.assertEqual(normalizar_base('/Emityma'), '/Emityma/')
        self.assertEqual(normalizar_base('Emityma/'), '/Emityma/')

    def test_gera_site_estatico_com_caminho_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / '_site'
            call_command('build_pages', output=str(saida), base_path='/Emityma/', stdout=io.StringIO())

            for arquivo in (
                'index.html', '404.html', '.nojekyll', 'entrar/index.html', 'dashboard/index.html',
                'dashboard/fazenda-demonstracao/index.html',
                'dashboard/fazenda/fazenda-demonstracao/tarefas/index.html',
                'static/css/dashboard.css', 'static/js/demo.js',
            ):
                self.assertTrue((saida / arquivo).is_file(), arquivo)

            self.assertFalse((saida / 'static' / 'admin').exists())

            # Demais fazendas do usuário demo: só as páginas permitidas pelo nível de acesso.
            gerente = saida / 'dashboard/fazenda/sitio-boa-esperanca'
            self.assertTrue((gerente / 'usuarios/index.html').is_file())
            self.assertFalse((gerente / 'gerenciar').exists())
            operador = saida / 'dashboard/fazenda/fazenda-santa-clara'
            self.assertTrue((operador / 'tarefas/index.html').is_file())
            self.assertFalse((operador / 'usuarios').exists())

            painel = (saida / 'dashboard/fazenda-demonstracao/index.html').read_text(encoding='utf-8')
            self.assertIn('href="/Emityma/static/css/dashboard.css"', painel)
            self.assertIn('Demonstração somente leitura', painel)
            self.assertIn('/Emityma/static/js/demo.js', painel)
            self.assertNotIn('href="/dashboard/', painel)

            login = (saida / 'entrar/index.html').read_text(encoding='utf-8')
            self.assertNotIn('csrfmiddlewaretoken', login)
            self.assertIn('Abrir demonstração do painel', login)
