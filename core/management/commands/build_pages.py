"""Gera a versão estática (somente leitura) do Emityma para o GitHub Pages.

Uso:
    python manage.py build_pages --settings=emityma.settings_pages --output _site --base-path /Emityma/

O comando:
1. cria os dados de demonstração num banco em memória;
2. renderiza as páginas com o cliente de testes do Django, com o caminho-base
   aplicado a todos os links (`{% url %}`) e arquivos estáticos (`{% static %}`);
3. grava cada rota como `<rota>/index.html`, além de `404.html` e `.nojekyll`;
4. copia os arquivos estáticos do projeto;
5. verifica se todos os links e recursos locais apontam para arquivos gerados.
"""

import io
import posixpath
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse, set_script_prefix

from core.access import NIVEIS_GESTAO, NIVEL_ADMIN, SESSION_KEY
from core.management.commands.seed_demo import DEMO_EMAIL
from core.models import UsuarioFazenda
from usuario.models import Usuario

ROTAS_PUBLICAS = ['home', 'entrar', 'cadastrar']
ROTAS_LOGADO = ['cadastrar_fazenda', 'dashboard']
# Páginas de cada fazenda, conforme o nível de acesso do usuário demo (o mesmo que o menu lateral exibe).
ROTAS_DA_FAZENDA = ['dashboard_home', 'tarefas', 'culturas', 'plantios']
ROTAS_DE_GESTAO = ['usuarios_fazenda']
ROTAS_DE_ADMIN = ['gerenciar_fazenda']
IGNORAR_ESTATICOS = ('admin/',)
PADROES_IGNORADOS = ['.DS_Store', 'Thumbs.db', '*.map', '*.scss', '*.less']
MARCADOR = '.nojekyll'

CSS_URL = re.compile(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)')


def normalizar_base(base):
    base = '/' + (base or '').strip().strip('/')
    return base if base == '/' else base + '/'


class _ColetorDeLinks(HTMLParser):
    ATRIBUTOS = {'href', 'src'}

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for nome, valor in attrs:
            if not valor:
                continue
            if nome in self.ATRIBUTOS:
                self.links.append(valor)
            elif nome == 'style':
                self.links.extend(m.group(2) for m in CSS_URL.finditer(valor))


class Command(BaseCommand):
    help = 'Gera o site estático (demonstração somente leitura) para o GitHub Pages.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='_site', help='Diretório de saída (padrão: _site).')
        parser.add_argument('--base-path', default='/', help='Caminho-base da publicação, ex.: /Emityma/ (padrão: /).')

    def handle(self, *args, **options):
        if connection.vendor != 'sqlite' or not connection.is_in_memory_db():
            raise CommandError(
                'Este comando grava dados de demonstração e deve usar um banco em memória. '
                'Execute com --settings=emityma.settings_pages.'
            )

        base = normalizar_base(options['base_path'])
        saida = Path(options['output']).resolve()
        self._preparar_saida(saida)

        call_command('migrate', interactive=False, verbosity=0)
        call_command('seed_demo', stdout=io.StringIO())

        publicas = [reverse(nome) for nome in ROTAS_PUBLICAS]
        restritas = [reverse(nome) for nome in ROTAS_LOGADO] + self._rotas_das_fazendas()
        rotas = publicas + restritas

        ajustes = override_settings(
            STATIC_DEMO=True,
            DEBUG=False,
            ALLOWED_HOSTS=['testserver'],
            FORCE_SCRIPT_NAME=base.rstrip('/'),
            STATIC_URL=base + 'static/',
        )
        with ajustes:
            # O cliente de testes não aplica FORCE_SCRIPT_NAME; o prefixo é definido aqui
            # para que todo reverse()/{% url %} gere links com o caminho-base.
            set_script_prefix(base)
            try:
                self._renderizar_paginas(publicas, restritas, saida)
            finally:
                set_script_prefix('/')

        self._copiar_estaticos(saida / 'static')
        (saida / MARCADOR).write_text('', encoding='utf-8')

        quebrados = self._verificar_links(saida, base)
        if quebrados:
            detalhes = '\n'.join(f'  {origem}: {link}' for origem, link in quebrados)
            raise CommandError(f'{len(quebrados)} link(s) local(is) quebrado(s):\n{detalhes}')

        total = sum(1 for _ in saida.rglob('*') if _.is_file())
        self.stdout.write(self.style.SUCCESS(
            f'Site estático gerado em {saida} ({len(rotas)} páginas, {total} arquivos, base "{base}").'
        ))

    # ------------------------------------------------------------------ etapas

    @staticmethod
    def _rotas_das_fazendas():
        rotas = []
        vinculos = UsuarioFazenda.objects.filter(usuario__usuario_email=DEMO_EMAIL).select_related('fazenda')
        for vinculo in vinculos.order_by('fazenda__nome'):
            nomes = list(ROTAS_DA_FAZENDA)
            if vinculo.nivel_acesso in NIVEIS_GESTAO:
                nomes += ROTAS_DE_GESTAO
            if vinculo.nivel_acesso == NIVEL_ADMIN:
                nomes += ROTAS_DE_ADMIN
            rotas += [reverse(nome, kwargs={'slug': vinculo.fazenda.slug}) for nome in nomes]
        return rotas

    def _preparar_saida(self, saida):
        projeto = Path(settings.BASE_DIR).resolve()
        if saida == projeto or saida in projeto.parents:
            raise CommandError(f'Diretório de saída inválido: {saida}')
        if saida.exists():
            if any(saida.iterdir()) and not (saida / MARCADOR).exists():
                raise CommandError(
                    f'{saida} já existe e não parece ser uma saída deste comando (falta {MARCADOR}). '
                    'Escolha outro diretório ou apague-o manualmente.'
                )
            shutil.rmtree(saida)
        saida.mkdir(parents=True)

    def _renderizar_paginas(self, publicas, restritas, saida):
        anonimo = Client()
        logado = Client()
        sessao = logado.session
        sessao[SESSION_KEY] = Usuario.objects.get(usuario_email=DEMO_EMAIL).usuario_id
        sessao.save()

        for cliente, rotas in ((anonimo, publicas), (logado, restritas)):
            for rota in rotas:
                resposta = cliente.get(rota)
                if resposta.status_code != 200:
                    raise CommandError(f'GET {rota} retornou {resposta.status_code}.')
                destino = saida / rota.strip('/') / 'index.html'
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(resposta.content)
                self.stdout.write(f'  {rota} -> {destino.relative_to(saida).as_posix()}')

        resposta = anonimo.get('/pagina-que-nao-existe-emityma/')
        if resposta.status_code != 404:
            raise CommandError(f'A página de erro retornou {resposta.status_code} em vez de 404.')
        (saida / '404.html').write_bytes(resposta.content)

    def _copiar_estaticos(self, destino):
        copiados = set()
        for finder in finders.get_finders():
            for caminho, storage in finder.list(PADROES_IGNORADOS):
                caminho = caminho.replace('\\', '/')
                if caminho.startswith(IGNORAR_ESTATICOS) or caminho in copiados:
                    continue
                alvo = destino / caminho
                alvo.parent.mkdir(parents=True, exist_ok=True)
                with storage.open(caminho) as origem, open(alvo, 'wb') as arquivo:
                    shutil.copyfileobj(origem, arquivo)
                copiados.add(caminho)

    # ------------------------------------------------------------ verificação

    def _verificar_links(self, saida, base):
        quebrados = []
        for arquivo in sorted(saida.rglob('*')):
            if arquivo.suffix not in ('.html', '.css'):
                continue
            relativo = arquivo.relative_to(saida).as_posix()
            url_do_arquivo = base + relativo
            texto = arquivo.read_text(encoding='utf-8', errors='replace')

            if arquivo.suffix == '.html':
                coletor = _ColetorDeLinks()
                coletor.feed(texto)
                links = coletor.links
            else:
                links = [m.group(2) for m in CSS_URL.finditer(texto)]

            for link in links:
                if not self._link_local_existe(link, url_do_arquivo, saida, base):
                    quebrados.append((relativo, link))
        return quebrados

    @staticmethod
    def _link_local_existe(link, url_do_arquivo, saida, base):
        link = link.strip()
        if not link or link.startswith(('#', 'data:', 'mailto:', 'tel:', 'javascript:')):
            return True
        partes = urlsplit(urljoin(url_do_arquivo, link))
        if partes.scheme or partes.netloc:
            return True  # recurso externo
        caminho = posixpath.normpath(unquote(partes.path)) + ('/' if partes.path.endswith('/') else '')
        if not (caminho + '/').startswith(base) and caminho != base.rstrip('/'):
            return False
        relativo = caminho[len(base):] if caminho.startswith(base) else ''
        alvo = saida / relativo
        if caminho.endswith('/') or alvo.is_dir():
            alvo = alvo / 'index.html'
        return alvo.is_file()
