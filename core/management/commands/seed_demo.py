"""Cria (ou recria) um conjunto de dados fictícios para demonstração.

Todos os nomes, e-mails e números são inventados. As datas são relativas ao dia
em que o comando roda, para que sempre existam plantios em andamento e já colhidos.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.access import NIVEL_ADMIN, NIVEL_GERENTE, NIVEL_OPERADOR
from core.models import Cultura, Fazenda, Plantio, Talhao, Tarefa, UsuarioFazenda
from usuario.models import Usuario

DEMO_EMAIL = 'demo@emityma.local'
DEMO_SENHA = 'emityma-demo'
DEMO_FAZENDA_SLUG = 'fazenda-demonstracao'

# (nome, e-mail) — todos usam a senha DEMO_SENHA.
USUARIOS = [
    ('Usuário Demo', DEMO_EMAIL),
    ('Ana Ribeiro', 'ana.ribeiro@emityma.local'),
    ('Carlos Mendes', 'carlos.mendes@emityma.local'),
    ('Beatriz Souza', 'beatriz.souza@emityma.local'),
    ('Rafael Lima', 'rafael.lima@emityma.local'),
    ('Juliana Costa', 'juliana.costa@emityma.local'),
]

# Plantios: (cultura, talhão, início em dias a partir de hoje, colheita prevista em dias).
# Tarefas: (título, descrição, prioridade, aberta há N dias).
FAZENDAS = [
    {
        'slug': DEMO_FAZENDA_SLUG,
        'nome': 'Fazenda Demonstração',
        'proprietario': 'Usuário Demo',
        'uf': 'MT', 'cidade': 'Sorriso',
        'email': 'contato@fazendademo.emityma.local', 'telefone': '(66) 3500-0000',
        'tamanho': 1250,
        'membros': [
            (DEMO_EMAIL, NIVEL_ADMIN),
            ('ana.ribeiro@emityma.local', NIVEL_GERENTE),
            ('carlos.mendes@emityma.local', NIVEL_OPERADOR),
            ('beatriz.souza@emityma.local', NIVEL_OPERADOR),
        ],
        'talhoes': [
            ('Talhão Norte', '320.00'), ('Talhão Sul', '280.50'), ('Talhão Leste', '210.00'),
            ('Talhão Oeste', '185.25'), ('Várzea', '95.00'), ('Talhão da Sede', '45.00'),
        ],
        'culturas': [
            ('Soja', 'LG', 'Soja de ciclo médio para grão, safra de verão.', 3600),
            ('Milho', 'GC', 'Milho segunda safra (safrinha) para grão.', 6200),
            ('Algodão', 'FB', 'Algodão herbáceo; produtividade em pluma.', 1900),
            ('Feijão', 'LG', 'Feijão carioca irrigado, terceira safra.', 1650),
            ('Sorgo', 'GC', 'Sorgo granífero, alternativa ao milho safrinha.', 3800),
            ('Braquiária', 'PC', 'Planta de cobertura para formação de palhada.', 0),
        ],
        'plantios': [
            ('Soja', 'Talhão Norte', -250, -130),
            ('Soja', 'Talhão Sul', -245, -125),
            ('Milho', 'Talhão Norte', -120, 15),
            ('Milho', 'Talhão Sul', -110, 25),
            ('Algodão', 'Talhão Leste', -150, 30),
            ('Sorgo', 'Talhão Oeste', -100, 10),
            ('Feijão', 'Várzea', -40, 50),
            ('Braquiária', 'Talhão da Sede', -60, -5),
            ('Soja', 'Talhão Oeste', 20, 140),
        ],
        'tarefas': [
            ('Revisar plantadeira', 'Checar discos, dosadores e pressão dos pneus antes da safra de soja.', 'U', 2),
            ('Monitorar lagarta no algodão', 'Fazer amostragem de pragas no Talhão Leste e registrar o nível de infestação.', 'U', 1),
            ('Comprar sementes de soja', 'Cotar com três fornecedores a semente para 185 ha do Talhão Oeste.', 'A', 6),
            ('Análise de solo', 'Coletar amostras de 0–20 cm nos talhões Norte e Sul.', 'A', 9),
            ('Calibrar pulverizador', 'Conferir vazão dos bicos antes da próxima aplicação.', 'A', 3),
            ('Limpeza do secador', 'Preparar o secador para a colheita do milho safrinha.', 'M', 12),
            ('Manutenção de cercas', 'Trecho próximo à Várzea danificado pela chuva.', 'M', 15),
            ('Atualizar planilha de custos', 'Lançar notas fiscais de insumos do mês.', 'B', 20),
            ('Organizar almoxarifado', 'Separar EPIs vencidos e repor estoque.', 'B', 25),
        ],
    },
    {
        'slug': 'sitio-boa-esperanca',
        'nome': 'Sítio Boa Esperança',
        'proprietario': 'Rafael Lima',
        'uf': 'MG', 'cidade': 'Lavras',
        'email': 'contato@boaesperanca.emityma.local', 'telefone': '(35) 3800-0000',
        'tamanho': 48,
        'membros': [
            ('rafael.lima@emityma.local', NIVEL_ADMIN),
            (DEMO_EMAIL, NIVEL_GERENTE),
            ('juliana.costa@emityma.local', NIVEL_OPERADOR),
        ],
        'talhoes': [
            ('Pomar de Cima', '12.00'), ('Pomar de Baixo', '9.50'), ('Horta', '2.50'),
            ('Pasto do Córrego', '18.00'),
        ],
        'culturas': [
            ('Laranja Pera', 'FR', 'Pomar de laranja para mesa e suco.', 28000),
            ('Banana Prata', 'FR', 'Bananal irrigado por gotejamento.', 22000),
            ('Capim Mombaça', 'GR', 'Pastagem rotacionada para o gado leiteiro.', 18000),
            ('Feijão', 'LG', 'Feijão das águas para consumo e venda local.', 1400),
        ],
        'plantios': [
            ('Laranja Pera', 'Pomar de Cima', -900, 60),
            ('Banana Prata', 'Pomar de Baixo', -300, 45),
            ('Feijão', 'Horta', -30, 60),
            ('Capim Mombaça', 'Pasto do Córrego', -200, 90),
        ],
        'tarefas': [
            ('Adubação do pomar', 'Aplicar adubação de cobertura no Pomar de Cima.', 'A', 4),
            ('Trocar gotejadores', 'Substituir gotejadores entupidos no bananal.', 'M', 10),
            ('Vender feijão na feira', 'Separar 20 sacas para a feira de sábado.', 'B', 2),
        ],
    },
    {
        'slug': 'fazenda-santa-clara',
        'nome': 'Fazenda Santa Clara',
        'proprietario': 'Juliana Costa',
        'uf': 'GO', 'cidade': 'Rio Verde',
        'email': 'contato@santaclara.emityma.local', 'telefone': '(64) 3600-0000',
        'tamanho': 620,
        'membros': [
            ('juliana.costa@emityma.local', NIVEL_ADMIN),
            ('carlos.mendes@emityma.local', NIVEL_GERENTE),
            (DEMO_EMAIL, NIVEL_OPERADOR),
        ],
        'talhoes': [
            ('Gleba A', '210.00'), ('Gleba B', '190.00'), ('Gleba C', '150.00'),
        ],
        'culturas': [
            ('Soja', 'LG', 'Soja precoce para permitir a safrinha.', 3500),
            ('Milho', 'GC', 'Milho safrinha após a soja.', 5800),
            ('Trigo', 'GC', 'Trigo tropical de sequeiro.', 3000),
        ],
        'plantios': [
            ('Soja', 'Gleba A', -230, -120),
            ('Milho', 'Gleba A', -115, 20),
            ('Soja', 'Gleba B', -225, -115),
            ('Trigo', 'Gleba B', -90, 15),
            ('Milho', 'Gleba C', -100, 35),
        ],
        'tarefas': [
            ('Agendar colheita do trigo', 'Reservar colhedora terceirizada para a Gleba B.', 'U', 1),
            ('Vistoria de armazém', 'Verificar umidade e pragas nos silos.', 'M', 7),
        ],
    },
]


class Command(BaseCommand):
    help = 'Cria (ou recria) dados fictícios de demonstração: usuários, fazendas, talhões, culturas, plantios e tarefas.'

    @transaction.atomic
    def handle(self, *args, **options):
        usuarios = {email: self._usuario(nome, email) for nome, email in USUARIOS}

        # Recria as fazendas de demonstração do zero (os relacionamentos são apagados em cascata).
        Fazenda.objects.filter(slug__in=[f['slug'] for f in FAZENDAS]).delete()
        for dados in FAZENDAS:
            self._fazenda(dados, usuarios)

        self.stdout.write(self.style.SUCCESS(
            f'Dados de demonstração criados: {len(USUARIOS)} usuários e {len(FAZENDAS)} fazendas.\n'
            f'Acesse com {DEMO_EMAIL} / senha "{DEMO_SENHA}" (a mesma senha vale para todos os usuários de exemplo).'
        ))

    @staticmethod
    def _usuario(nome, email):
        usuario = Usuario.objects.filter(usuario_email=email).first() or Usuario(usuario_email=email)
        usuario.usuario_nome = nome
        usuario.definir_senha(DEMO_SENHA)
        usuario.save()
        return usuario

    @staticmethod
    def _fazenda(dados, usuarios):
        hoje = timezone.localdate()
        fazenda = Fazenda.objects.create(
            slug=dados['slug'],
            nome=dados['nome'],
            proprietario=dados['proprietario'],
            uf=dados['uf'],
            cidade=dados['cidade'],
            email=dados['email'],
            telefone=dados['telefone'],
            tamanho=dados['tamanho'],
        )
        for email, nivel in dados['membros']:
            UsuarioFazenda.objects.create(fazenda=fazenda, usuario=usuarios[email], nivel_acesso=nivel)

        talhoes = {
            nome: Talhao.objects.create(fazenda=fazenda, nome=nome, area=Decimal(area))
            for nome, area in dados['talhoes']
        }
        culturas = {
            nome: Cultura.objects.create(
                fazenda=fazenda, nome=nome, tp_cultura=tipo, descricao=descricao, produtividade_media=produtividade,
            )
            for nome, tipo, descricao, produtividade in dados['culturas']
        }
        for cultura, talhao, inicio, colheita in dados['plantios']:
            Plantio.objects.create(
                cultura=culturas[cultura],
                talhao=talhoes[talhao],
                dt_plantio=hoje + timedelta(days=inicio),
                dt_colheitaPrevista=hoje + timedelta(days=colheita),
            )
        for titulo, descricao, prioridade, dias in dados['tarefas']:
            tarefa = Tarefa.objects.create(fazenda=fazenda, titulo=titulo, descricao=descricao, prioridade=prioridade)
            # dt_solicitacao usa auto_now_add; ajusta depois para simular tarefas abertas em dias diferentes.
            Tarefa.objects.filter(pk=tarefa.pk).update(dt_solicitacao=hoje - timedelta(days=dias))
