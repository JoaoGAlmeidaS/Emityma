"""Cálculo dos indicadores exibidos na página inicial do dashboard.

Status de um plantio em relação a hoje:
- planejado: ainda não começou (dt_plantio > hoje);
- andamento: entre o plantio e a colheita prevista (inclusive);
- colhido: a colheita prevista já passou.

Produção estimada de um plantio = produtividade média da cultura (kg/ha) x área do talhão.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from core.access import NIVEIS_ACESSO
from core.models import Plantio, Talhao, Tarefa, UsuarioFazenda

PLANEJADO, ANDAMENTO, COLHIDO = 'planejado', 'andamento', 'colhido'
PRIORIDADES = {'urgente': 'U', 'alta': 'A', 'media': 'M', 'baixa': 'B'}


def _percentual(parte, total, casas=0):
    if not total:
        return 0
    valor = round(float(parte) / float(total) * 100, casas)
    return int(valor) if casas == 0 else valor


def _media(valores):
    valores = list(valores)
    return round(sum(valores) / len(valores)) if valores else None


def status_plantio(plantio, hoje):
    if plantio.dt_plantio > hoje:
        return PLANEJADO
    if plantio.dt_colheitaPrevista < hoje:
        return COLHIDO
    return ANDAMENTO


def producao_toneladas(plantio):
    kg = Decimal(str(plantio.cultura.produtividade_media)) * plantio.talhao.area
    return float(kg / 1000)


def ciclo_dias(plantio):
    return (plantio.dt_colheitaPrevista - plantio.dt_plantio).days


# ----------------------------------------------------------------------- tarefas

def resumo_tarefas(fazenda, hoje):
    """Quantidade e percentual por prioridade, tarefa mais antiga e tempo médio em aberto."""
    tarefas = Tarefa.objects.filter(fazenda=fazenda)
    contagens = tarefas.aggregate(
        **{nome: Count('id', filter=Q(prioridade=codigo)) for nome, codigo in PRIORIDADES.items()}
    )
    total = sum(contagens.values())
    dados = {'total_tarefas': total}
    for nome, quantidade in contagens.items():
        dados[f'tarefas_{nome}'] = quantidade
        dados[f'{nome}_percentual'] = _percentual(quantidade, total)

    mais_antiga = tarefas.order_by('dt_solicitacao', 'id').first()
    dados['tarefa_mais_antiga'] = (
        {'titulo': mais_antiga.titulo, 'dias': (hoje - mais_antiga.dt_solicitacao).days} if mais_antiga else None
    )
    dados['idade_media_tarefas'] = _media((hoje - data).days for data in tarefas.values_list('dt_solicitacao', flat=True))
    return dados


# ---------------------------------------------------------------------- plantios

def resumo_plantios(plantios, hoje):
    """Contagem por status e produção estimada ainda a colher / já colhida (t)."""
    contagem = {PLANEJADO: 0, ANDAMENTO: 0, COLHIDO: 0}
    prevista = colhida = 0.0
    for plantio in plantios:
        status = status_plantio(plantio, hoje)
        contagem[status] += 1
        if status == COLHIDO:
            colhida += producao_toneladas(plantio)
        else:
            prevista += producao_toneladas(plantio)
    return {
        'plantios_planejados': contagem[PLANEJADO],
        'plantios_andamento': contagem[ANDAMENTO],
        'plantios_colhidos': contagem[COLHIDO],
        'producao_prevista_t': round(prevista, 1),
        'producao_colhida_t': round(colhida, 1),
    }


def situacao_talhoes(talhoes, plantios, hoje):
    """Situação atual de cada talhão: em produção, planejado ou livre."""
    por_talhao = defaultdict(list)
    for plantio in plantios:
        por_talhao[plantio.talhao_id].append(plantio)

    situacoes = []
    for talhao in talhoes:
        do_talhao = por_talhao[talhao.id]
        andamento = [p for p in do_talhao if status_plantio(p, hoje) == ANDAMENTO]
        planejados = [p for p in do_talhao if status_plantio(p, hoje) == PLANEJADO]
        colhidos = [p for p in do_talhao if status_plantio(p, hoje) == COLHIDO]

        if andamento:
            atual = max(andamento, key=lambda p: p.dt_plantio)
            item = {'status': ANDAMENTO, 'cultura': atual.cultura.nome, 'data': atual.dt_colheitaPrevista,
                    'rotulo_data': 'Colheita prevista'}
        elif planejados:
            proximo = min(planejados, key=lambda p: p.dt_plantio)
            item = {'status': PLANEJADO, 'cultura': proximo.cultura.nome, 'data': proximo.dt_plantio,
                    'rotulo_data': 'Plantio previsto'}
        else:
            ultimo = max(colhidos, key=lambda p: p.dt_colheitaPrevista, default=None)
            item = {'status': 'livre', 'cultura': ultimo.cultura.nome if ultimo else None,
                    'data': ultimo.dt_colheitaPrevista if ultimo else None, 'rotulo_data': 'Última colheita'}
        item.update(talhao=talhao.nome, area=talhao.area)
        situacoes.append(item)
    return situacoes


def ocupacao(fazenda, talhoes, situacoes):
    """Área dos talhões, área em produção agora e percentuais."""
    area_talhoes = sum((t.area for t in talhoes), Decimal('0'))
    area_em_uso = sum((s['area'] for s in situacoes if s['status'] == ANDAMENTO), Decimal('0'))
    return {
        'total_talhoes': len(talhoes),
        'area_talhoes': area_talhoes,
        'area_em_uso': area_em_uso,
        'percentual_em_uso': _percentual(area_em_uso, area_talhoes),
        'percentual_mapeado': _percentual(area_talhoes, fazenda.tamanho),
    }


def area_por_cultura(situacoes):
    """Percentual da área em produção ocupada por cada cultura."""
    areas = defaultdict(Decimal)
    for situacao in situacoes:
        if situacao['status'] == ANDAMENTO:
            areas[situacao['cultura']] += situacao['area']
    total = sum(areas.values(), Decimal('0'))
    ordenadas = sorted(areas.items(), key=lambda item: item[1], reverse=True)
    return [nome for nome, _ in ordenadas], [_percentual(area, total, casas=2) for _, area in ordenadas]


def proximas_colheitas(plantios, hoje, limite=5):
    """Plantios em andamento ordenados pela colheita prevista."""
    andamento = sorted(
        (p for p in plantios if status_plantio(p, hoje) == ANDAMENTO),
        key=lambda p: (p.dt_colheitaPrevista, p.talhao.nome),
    )
    resultado = []
    for plantio in andamento[:limite]:
        decorrido = (hoje - plantio.dt_plantio).days
        resultado.append({
            'cultura': plantio.cultura.nome,
            'talhao': plantio.talhao.nome,
            'area': plantio.talhao.area,
            'colheita': plantio.dt_colheitaPrevista,
            'dias_restantes': (plantio.dt_colheitaPrevista - hoje).days,
            'progresso': min(100, max(0, _percentual(decorrido, max(ciclo_dias(plantio), 1)))),
            'producao_t': round(producao_toneladas(plantio), 1),
        })
    return resultado


def producao_por_cultura(plantios, hoje):
    """Produção e área ainda a colher por cultura, com o ciclo médio (dias) de cada uma."""
    producao = defaultdict(float)
    area = defaultdict(Decimal)
    ciclos = defaultdict(list)
    for plantio in plantios:
        nome = plantio.cultura.nome
        ciclos[nome].append(ciclo_dias(plantio))
        if status_plantio(plantio, hoje) != COLHIDO:
            producao[nome] += producao_toneladas(plantio)
            area[nome] += plantio.talhao.area

    linhas = [
        {'cultura': nome, 'producao_t': round(producao[nome], 1), 'area': area[nome], 'ciclo_medio': _media(ciclos[nome])}
        for nome in area
    ]
    return sorted(linhas, key=lambda linha: (-linha['producao_t'], linha['cultura']))


# ------------------------------------------------------------------------ equipe

def equipe(fazenda):
    contagem = dict(
        UsuarioFazenda.objects.filter(fazenda=fazenda).values_list('nivel_acesso').annotate(n=Count('id'))
    )
    niveis = [(nivel, contagem.get(nivel, 0)) for nivel in NIVEIS_ACESSO]
    return {'equipe_niveis': niveis, 'equipe_total': sum(n for _, n in niveis)}


# -------------------------------------------------------------------- agregação

def metricas_fazenda(fazenda, hoje=None):
    hoje = hoje or timezone.localdate()
    talhoes = list(Talhao.objects.filter(fazenda=fazenda).order_by('nome'))
    plantios = list(Plantio.objects.filter(talhao__fazenda=fazenda).select_related('cultura', 'talhao'))
    situacoes = situacao_talhoes(talhoes, plantios, hoje)
    labels, percentuais = area_por_cultura(situacoes)
    colheitas = proximas_colheitas(plantios, hoje)
    por_cultura = producao_por_cultura(plantios, hoje)

    return {
        **resumo_tarefas(fazenda, hoje),
        **resumo_plantios(plantios, hoje),
        **ocupacao(fazenda, talhoes, situacoes),
        **equipe(fazenda),
        'situacao_talhoes': situacoes,
        'proximas_colheitas': colheitas,
        'proxima_colheita': colheitas[0] if colheitas else None,
        'producao_por_cultura': por_cultura,
        'producao_labels': [linha['cultura'] for linha in por_cultura],
        'producao_valores': [linha['producao_t'] for linha in por_cultura],
        'cultura_labels': labels,
        'cultura_percentuais': percentuais,
    }
