from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import NIVEL_ADMIN, NIVEL_GERENTE, NIVEL_OPERADOR, SESSION_KEY
from core.models import Cultura, Fazenda, Plantio, Talhao, Tarefa, UsuarioFazenda
from usuario.models import Usuario

from .services import metricas_fazenda


def criar_usuario(nome):
    usuario = Usuario(usuario_nome=nome, usuario_email=f'{nome.lower()}@exemplo.com')
    usuario.definir_senha('colheita-segura-2025')
    usuario.save()
    return usuario


def criar_fazenda(nome, **membros):
    fazenda = Fazenda.objects.create(
        nome=nome, proprietario='Fulano', uf='MT', cidade='Cuiabá',
        email='contato@exemplo.com', telefone='0000', tamanho=100,
    )
    for usuario, nivel in membros.values():
        UsuarioFazenda.objects.create(fazenda=fazenda, usuario=usuario, nivel_acesso=nivel)
    return fazenda


class BaseDashboardTest(TestCase):
    def setUp(self):
        self.admin = criar_usuario('Admin')
        self.operador = criar_usuario('Operador')
        self.gerente = criar_usuario('Gerente')
        self.estranho = criar_usuario('Estranho')
        self.fazenda = criar_fazenda(
            'Fazenda A',
            a=(self.admin, NIVEL_ADMIN),
            g=(self.gerente, NIVEL_GERENTE),
            o=(self.operador, NIVEL_OPERADOR),
        )
        self.outra = criar_fazenda('Fazenda B', e=(self.estranho, NIVEL_ADMIN))

    def entrar_como(self, usuario):
        sessao = self.client.session
        sessao[SESSION_KEY] = usuario.usuario_id
        sessao.save()

    def url(self, nome, fazenda=None):
        return reverse(nome, kwargs={'slug': (fazenda or self.fazenda).slug})


class AcessoTests(BaseDashboardTest):
    def test_anonimo_e_redirecionado_para_login(self):
        for nome in ('dashboard_home', 'tarefas', 'culturas', 'plantios'):
            self.assertRedirects(self.client.get(self.url(nome)), reverse('entrar'))

    def test_quem_nao_e_membro_recebe_404(self):
        self.entrar_como(self.estranho)
        self.assertEqual(self.client.get(self.url('dashboard_home')).status_code, 404)

    def test_fazenda_inexistente_recebe_404(self):
        self.entrar_como(self.admin)
        resposta = self.client.get(reverse('dashboard_home', kwargs={'slug': 'nao-existe'}))
        self.assertEqual(resposta.status_code, 404)

    def test_paginas_do_dashboard_abrem_para_admin(self):
        self.entrar_como(self.admin)
        for nome in ('dashboard_home', 'gerenciar_fazenda', 'usuarios_fazenda', 'tarefas', 'culturas', 'plantios'):
            self.assertEqual(self.client.get(self.url(nome)).status_code, 200, nome)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_operador_nao_cria_tarefa(self):
        self.entrar_como(self.operador)
        resposta = self.client.post(self.url('criar_tarefa'), {'titulo': 'X', 'descricao': 'Y', 'prioridade': 'A'})
        self.assertRedirects(resposta, self.url('tarefas'))
        self.assertFalse(Tarefa.objects.exists())

    def test_gerente_cria_tarefa(self):
        self.entrar_como(self.gerente)
        self.client.post(self.url('criar_tarefa'), {'titulo': 'Adubar', 'descricao': 'Talhão 1', 'prioridade': 'U'})
        self.assertTrue(Tarefa.objects.filter(fazenda=self.fazenda, titulo='Adubar').exists())

    def test_gerente_nao_gerencia_fazenda_nem_usuarios(self):
        self.entrar_como(self.gerente)
        self.assertRedirects(self.client.get(self.url('gerenciar_fazenda')), self.url('dashboard_home'))
        vinculo_admin = UsuarioFazenda.objects.get(fazenda=self.fazenda, usuario=self.admin)
        self.client.post(self.url('remover_usuario_fazenda'), {'usuario_fazenda_id': vinculo_admin.id})
        self.assertTrue(UsuarioFazenda.objects.filter(id=vinculo_admin.id).exists())

    def test_alterar_dados_exige_post(self):
        self.entrar_como(self.admin)
        self.assertEqual(self.client.get(self.url('excluir_tarefa')).status_code, 405)


class IsolamentoEntreFazendasTests(BaseDashboardTest):
    """Regressão: antes, ids enviados no POST não eram filtrados pela fazenda."""

    def setUp(self):
        super().setUp()
        self.talhao_b = Talhao.objects.create(fazenda=self.outra, nome='B1', area=Decimal('10'))
        self.cultura_b = Cultura.objects.create(fazenda=self.outra, nome='Soja', tp_cultura='LG', descricao='-', produtividade_media=1)
        self.plantio_b = Plantio.objects.create(
            talhao=self.talhao_b, cultura=self.cultura_b,
            dt_plantio=date(2025, 1, 1), dt_colheitaPrevista=date(2025, 5, 1),
        )
        self.entrar_como(self.admin)

    def test_nao_edita_talhao_de_outra_fazenda(self):
        resposta = self.client.post(self.url('editar_talhao'), {'talhao_id': self.talhao_b.id, 'nome': 'Hack', 'area': '1'})
        self.assertEqual(resposta.status_code, 404)
        self.talhao_b.refresh_from_db()
        self.assertEqual(self.talhao_b.nome, 'B1')

    def test_nao_exclui_plantio_de_outra_fazenda(self):
        resposta = self.client.post(self.url('excluir_plantio'), {'plantio_id': self.plantio_b.id})
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(Plantio.objects.filter(id=self.plantio_b.id).exists())

    def test_nao_usa_cultura_de_outra_fazenda_em_plantio(self):
        talhao_a = Talhao.objects.create(fazenda=self.fazenda, nome='A1', area=Decimal('5'))
        self.client.post(self.url('criar_plantio'), {
            'cultura': self.cultura_b.id, 'talhao': talhao_a.id,
            'dt_plantio': '2025-01-01', 'dt_colheitaPrevista': '2025-03-01',
        })
        self.assertFalse(Plantio.objects.filter(talhao=talhao_a).exists())

    def test_nao_edita_fazenda_da_qual_nao_e_membro(self):
        resposta = self.client.post(self.url('editar_fazenda', self.outra), {'nome': 'Hack'})
        self.assertEqual(resposta.status_code, 404)


class ValidacaoTests(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.entrar_como(self.admin)

    def test_area_invalida_nao_gera_erro_500(self):
        resposta = self.client.post(self.url('gerenciar_fazenda'), {'nome': 'T1', 'area': 'abc'}, follow=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Talhao.objects.filter(fazenda=self.fazenda).exists())
        self.assertContains(resposta, 'Não foi possível salvar')

    def test_colheita_antes_do_plantio_e_rejeitada(self):
        talhao = Talhao.objects.create(fazenda=self.fazenda, nome='A1', area=Decimal('5'))
        cultura = Cultura.objects.create(fazenda=self.fazenda, nome='Milho', tp_cultura='GC', descricao='-', produtividade_media=1)
        self.client.post(self.url('criar_plantio'), {
            'cultura': cultura.id, 'talhao': talhao.id,
            'dt_plantio': '2025-05-01', 'dt_colheitaPrevista': '2025-01-01',
        })
        self.assertFalse(Plantio.objects.exists())

    def test_cultura_em_uso_nao_e_excluida(self):
        talhao = Talhao.objects.create(fazenda=self.fazenda, nome='A1', area=Decimal('5'))
        cultura = Cultura.objects.create(fazenda=self.fazenda, nome='Milho', tp_cultura='GC', descricao='-', produtividade_media=1)
        Plantio.objects.create(talhao=talhao, cultura=cultura, dt_plantio=date(2025, 1, 1), dt_colheitaPrevista=date(2025, 6, 1))
        resposta = self.client.post(self.url('excluir_cultura'), {'cultura_id': cultura.id}, follow=True)
        self.assertTrue(Cultura.objects.filter(id=cultura.id).exists())
        self.assertContains(resposta, 'associada a plantios')

    def test_nivel_de_acesso_invalido_e_rejeitado(self):
        vinculo = UsuarioFazenda.objects.get(fazenda=self.fazenda, usuario=self.operador)
        self.client.post(self.url('editar_usuario_fazenda'), {'usuario_fazenda_id': vinculo.id, 'nivel_acesso': 'AD'})
        vinculo.refresh_from_db()
        self.assertEqual(vinculo.nivel_acesso, NIVEL_OPERADOR)

    def test_nome_de_cultura_e_escapado_no_grafico(self):
        talhao = Talhao.objects.create(fazenda=self.fazenda, nome='A1', area=Decimal('5'))
        cultura = Cultura.objects.create(
            fazenda=self.fazenda, nome='</script><script>alert(1)</script>',
            tp_cultura='GC', descricao='-', produtividade_media=1,
        )
        hoje = timezone.localdate()
        Plantio.objects.create(talhao=talhao, cultura=cultura, dt_plantio=hoje - timedelta(days=10),
                               dt_colheitaPrevista=hoje + timedelta(days=10))
        resposta = self.client.get(self.url('dashboard_home'))
        self.assertNotContains(resposta, '<script>alert(1)</script>')
        self.assertContains(resposta, 'id="cultura-labels"')
        self.assertContains(resposta, 'id="producao-labels"')


class MetricasTests(BaseDashboardTest):
    """Cenário com data fixa (fazenda de 100 ha):

    - T1 (10 ha): milho colhido + soja em andamento
    - T2 (30 ha): milho em andamento, na metade do ciclo
    - T3 (20 ha): soja planejada
    - T4 (40 ha): sem plantios
    """

    HOJE = date(2026, 3, 1)

    def setUp(self):
        super().setUp()
        h = self.HOJE

        def dias(n):
            return h + timedelta(days=n)

        t1 = Talhao.objects.create(fazenda=self.fazenda, nome='T1', area=Decimal('10'))
        t2 = Talhao.objects.create(fazenda=self.fazenda, nome='T2', area=Decimal('30'))
        t3 = Talhao.objects.create(fazenda=self.fazenda, nome='T3', area=Decimal('20'))
        Talhao.objects.create(fazenda=self.fazenda, nome='T4', area=Decimal('40'))
        soja = Cultura.objects.create(fazenda=self.fazenda, nome='Soja', tp_cultura='LG', descricao='-', produtividade_media=100)
        milho = Cultura.objects.create(fazenda=self.fazenda, nome='Milho', tp_cultura='GC', descricao='-', produtividade_media=200)
        Plantio.objects.create(talhao=t1, cultura=milho, dt_plantio=dias(-200), dt_colheitaPrevista=dias(-100))
        Plantio.objects.create(talhao=t1, cultura=soja, dt_plantio=dias(-10), dt_colheitaPrevista=dias(90))
        Plantio.objects.create(talhao=t2, cultura=milho, dt_plantio=dias(-30), dt_colheitaPrevista=dias(30))
        Plantio.objects.create(talhao=t3, cultura=soja, dt_plantio=dias(10), dt_colheitaPrevista=dias(110))

        for titulo, prioridade, aberta_ha in (('Antiga', 'U', 10), ('B', 'A', 4), ('C', 'A', 2), ('D', 'B', 0)):
            tarefa = Tarefa.objects.create(fazenda=self.fazenda, titulo=titulo, descricao='d', prioridade=prioridade)
            Tarefa.objects.filter(pk=tarefa.pk).update(dt_solicitacao=dias(-aberta_ha))

        self.m = metricas_fazenda(self.fazenda, hoje=h)

    def test_status_e_producao_dos_plantios(self):
        m = self.m
        self.assertEqual((m['plantios_planejados'], m['plantios_andamento'], m['plantios_colhidos']), (1, 2, 1))
        # a colher: soja T1 (1 t) + milho T2 (6 t) + soja T3 (2 t); colhido: milho T1 (2 t)
        self.assertEqual(m['producao_prevista_t'], 9.0)
        self.assertEqual(m['producao_colhida_t'], 2.0)

    def test_ocupacao_e_area_por_cultura(self):
        m = self.m
        self.assertEqual(m['total_talhoes'], 4)
        self.assertEqual(m['area_talhoes'], Decimal('100'))
        self.assertEqual(m['area_em_uso'], Decimal('40'))
        self.assertEqual(m['percentual_em_uso'], 40)
        self.assertEqual(m['percentual_mapeado'], 100)
        self.assertEqual(list(zip(m['cultura_labels'], m['cultura_percentuais'])), [('Milho', 75.0), ('Soja', 25.0)])

    def test_situacao_dos_talhoes(self):
        situacao = {s['talhao']: (s['status'], s['cultura'], s['data']) for s in self.m['situacao_talhoes']}
        h = self.HOJE
        self.assertEqual(situacao['T1'], ('andamento', 'Soja', h + timedelta(days=90)))
        self.assertEqual(situacao['T2'], ('andamento', 'Milho', h + timedelta(days=30)))
        self.assertEqual(situacao['T3'], ('planejado', 'Soja', h + timedelta(days=10)))
        self.assertEqual(situacao['T4'], ('livre', None, None))

    def test_proximas_colheitas(self):
        colheitas = self.m['proximas_colheitas']
        self.assertEqual([(c['cultura'], c['talhao']) for c in colheitas], [('Milho', 'T2'), ('Soja', 'T1')])
        self.assertEqual(colheitas[0]['dias_restantes'], 30)
        self.assertEqual(colheitas[0]['progresso'], 50)
        self.assertEqual(colheitas[0]['producao_t'], 6.0)
        self.assertEqual(self.m['proxima_colheita'], colheitas[0])

    def test_producao_por_cultura_e_ciclo_medio(self):
        linhas = {l['cultura']: (l['producao_t'], l['area'], l['ciclo_medio']) for l in self.m['producao_por_cultura']}
        self.assertEqual(linhas['Milho'], (6.0, Decimal('30'), 80))   # ciclos de 100 e 60 dias
        self.assertEqual(linhas['Soja'], (3.0, Decimal('30'), 100))
        self.assertEqual(self.m['producao_labels'], ['Milho', 'Soja'])

    def test_tarefas_e_equipe(self):
        m = self.m
        self.assertEqual(m['total_tarefas'], 4)
        self.assertEqual((m['tarefas_urgente'], m['tarefas_alta'], m['tarefas_media'], m['tarefas_baixa']), (1, 2, 0, 1))
        self.assertEqual(m['alta_percentual'], 50)
        self.assertEqual(m['tarefa_mais_antiga'], {'titulo': 'Antiga', 'dias': 10})
        self.assertEqual(m['idade_media_tarefas'], 4)
        self.assertEqual(m['equipe_niveis'], [(NIVEL_ADMIN, 1), (NIVEL_GERENTE, 1), (NIVEL_OPERADOR, 1)])
        self.assertEqual(m['equipe_total'], 3)

    def test_fazenda_sem_dados_nao_quebra(self):
        m = metricas_fazenda(self.outra, hoje=self.HOJE)
        self.assertEqual(m['area_talhoes'], 0)
        self.assertEqual(m['percentual_em_uso'], 0)
        self.assertIsNone(m['proxima_colheita'])
        self.assertIsNone(m['tarefa_mais_antiga'])
        self.assertEqual(m['producao_por_cultura'], [])

    def test_pagina_exibe_as_novas_secoes(self):
        # A página usa a data real; o cenário (data fixa no passado) aparece como talhões livres.
        self.entrar_como(self.admin)
        resposta = self.client.get(self.url('dashboard_home'))
        for texto in ('Área em produção', 'Próximas colheitas', 'Produção prevista por cultura',
                      'Situação dos talhões', 'Equipe: 3 pessoas', 'Aberta há mais tempo'):
            self.assertContains(resposta, texto)
