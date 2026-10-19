from django.contrib import messages
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.access import NIVEIS_GESTAO, NIVEL_ADMIN, acesso_fazenda, usuario_logado
from core.forms import (
    UFS,
    CulturaForm,
    FazendaForm,
    NivelAcessoForm,
    PlantioForm,
    TalhaoForm,
    TarefaForm,
    resumo_erros,
)
from core.models import Cultura, Fazenda, Plantio, Talhao, Tarefa, UsuarioFazenda
from usuario.models import Usuario

from .services import metricas_fazenda


def _contexto(request, fazenda, vinculo, **extra):
    return {
        'fazenda': fazenda,
        'usuario': request.usuario,
        'nivel_acesso': vinculo.nivel_acesso,
        **extra,
    }


def _salvar(request, form, mensagem_sucesso, **atributos):
    """Valida e grava um ModelForm, registrando a mensagem de sucesso ou de erro."""
    if not form.is_valid():
        messages.error(request, resumo_erros(form))
        return None
    objeto = form.save(commit=False)
    for nome, valor in atributos.items():
        setattr(objeto, nome, valor)
    objeto.save()
    messages.success(request, mensagem_sucesso)
    return objeto


@usuario_logado
def dashboard(request):
    fazendas = Fazenda.objects.filter(usuarios=request.usuario).order_by('nome')
    return render(request, 'dashboard/escolher_fazenda.html', {
        'fazendas': fazendas,
        'usuario': request.usuario,
    })


@acesso_fazenda()
def dashboard_home(request, fazenda, vinculo):
    contexto = _contexto(request, fazenda, vinculo, **metricas_fazenda(fazenda))
    return render(request, 'dashboard/dashboard_home.html', contexto)

# ======================================================= GERENCIAMENTO DA FAZENDA =======================================================


@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='gerenciar a fazenda')
def gerenciar_fazenda(request, fazenda, vinculo):
    if request.method == 'POST':
        _salvar(request, TalhaoForm(request.POST), 'Talhão cadastrado com sucesso!', fazenda=fazenda)
        return redirect('gerenciar_fazenda', slug=fazenda.slug)

    talhoes = Talhao.objects.filter(fazenda=fazenda).annotate(qtd_plantios=Count('plantios')).order_by('nome')
    return render(request, 'dashboard/gerenciar_fazenda.html', _contexto(request, fazenda, vinculo, talhoes=talhoes, ufs=UFS))


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='editar talhões')
def editar_talhao(request, fazenda, vinculo):
    talhao = get_object_or_404(Talhao, id=request.POST.get('talhao_id'), fazenda=fazenda)
    _salvar(request, TalhaoForm(request.POST, instance=talhao), 'Talhão atualizado com sucesso!')
    return redirect('gerenciar_fazenda', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='excluir talhões')
def excluir_talhao(request, fazenda, vinculo):
    talhao = get_object_or_404(Talhao, id=request.POST.get('talhao_id'), fazenda=fazenda)
    talhao.delete()
    messages.success(request, 'Talhão excluído com sucesso!')
    return redirect('gerenciar_fazenda', slug=fazenda.slug)


@require_GET
@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='adicionar usuários')
def buscar_usuario_por_email(request, fazenda, vinculo):
    email = request.GET.get('email', '').strip()
    usuario = Usuario.objects.filter(usuario_email__iexact=email).first() if email else None
    if usuario is None:
        return JsonResponse({'erro': 'Usuário não encontrado.'}, status=404)
    if UsuarioFazenda.objects.filter(fazenda=fazenda, usuario=usuario).exists():
        return JsonResponse({'erro': 'Usuário já está cadastrado nesta fazenda.'}, status=400)
    return JsonResponse({'nome': usuario.usuario_nome, 'email': usuario.usuario_email, 'id': usuario.usuario_id})


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='adicionar usuários')
def adicionar_usuario_fazenda(request, fazenda, vinculo):
    form = NivelAcessoForm(request.POST)
    usuario = Usuario.objects.filter(usuario_email__iexact=request.POST.get('email', '').strip()).first()
    if not form.is_valid():
        messages.error(request, 'Selecione um nível de acesso válido.')
    elif usuario is None:
        messages.error(request, 'Usuário não encontrado.')
    elif UsuarioFazenda.objects.filter(fazenda=fazenda, usuario=usuario).exists():
        messages.warning(request, 'Usuário já está associado a esta fazenda.')
    else:
        UsuarioFazenda.objects.create(fazenda=fazenda, usuario=usuario, nivel_acesso=form.cleaned_data['nivel_acesso'])
        messages.success(request, 'Usuário adicionado com sucesso!')
    return redirect('gerenciar_fazenda', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), acao='editar a fazenda')
def editar_fazenda(request, fazenda, vinculo):
    _salvar(request, FazendaForm(request.POST, instance=fazenda), 'Fazenda atualizada com sucesso!')
    return redirect('gerenciar_fazenda', slug=fazenda.slug)

# ======================================================= USUÁRIOS =======================================================


@acesso_fazenda(niveis=NIVEIS_GESTAO, acao='ver os usuários da fazenda')
def usuarios_fazenda(request, fazenda, vinculo):
    usuarios = UsuarioFazenda.objects.filter(fazenda=fazenda).select_related('usuario').order_by('usuario__usuario_nome')
    return render(request, 'dashboard/usuarios_fazenda.html', _contexto(request, fazenda, vinculo, usuarios=usuarios))


def _vinculo_de_outro_usuario(request, fazenda, acao):
    """Busca o vínculo enviado no POST, impedindo que o usuário altere a si mesmo."""
    alvo = get_object_or_404(UsuarioFazenda, id=request.POST.get('usuario_fazenda_id'), fazenda=fazenda)
    if alvo.usuario_id == request.usuario.usuario_id:
        messages.error(request, f'Você não pode {acao} a si mesmo.')
        return None
    return alvo


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), redirecionar_para='usuarios_fazenda', acao='editar usuários')
def editar_usuario_fazenda(request, fazenda, vinculo):
    alvo = _vinculo_de_outro_usuario(request, fazenda, 'editar')
    form = NivelAcessoForm(request.POST)
    if alvo and form.is_valid():
        alvo.nivel_acesso = form.cleaned_data['nivel_acesso']
        alvo.save(update_fields=['nivel_acesso'])
        messages.success(request, 'Nível de acesso atualizado com sucesso!')
    elif alvo:
        messages.error(request, 'Selecione um nível de acesso válido.')
    return redirect('usuarios_fazenda', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=(NIVEL_ADMIN,), redirecionar_para='usuarios_fazenda', acao='remover usuários')
def remover_usuario_fazenda(request, fazenda, vinculo):
    alvo = _vinculo_de_outro_usuario(request, fazenda, 'remover')
    if alvo:
        alvo.delete()
        messages.success(request, 'Usuário removido com sucesso!')
    return redirect('usuarios_fazenda', slug=fazenda.slug)

# ======================================================= TAREFAS =======================================================

ORDEM_PRIORIDADE = Case(
    When(prioridade='U', then=Value(1)),
    When(prioridade='A', then=Value(2)),
    When(prioridade='M', then=Value(3)),
    When(prioridade='B', then=Value(4)),
    default=Value(5),
    output_field=IntegerField(),
)


@acesso_fazenda()
def tarefas(request, fazenda, vinculo):
    lista = (
        Tarefa.objects.filter(fazenda=fazenda)
        .annotate(prioridade_ordem=ORDEM_PRIORIDADE)
        .order_by('prioridade_ordem', 'dt_solicitacao')
    )
    return render(request, 'dashboard/tarefas.html', _contexto(request, fazenda, vinculo, tarefas=lista))


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='tarefas', acao='criar tarefas')
def criar_tarefa(request, fazenda, vinculo):
    _salvar(request, TarefaForm(request.POST), 'Tarefa criada com sucesso!', fazenda=fazenda)
    return redirect('tarefas', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='tarefas', acao='editar tarefas')
def editar_tarefa(request, fazenda, vinculo):
    tarefa = get_object_or_404(Tarefa, id=request.POST.get('tarefa_id'), fazenda=fazenda)
    _salvar(request, TarefaForm(request.POST, instance=tarefa), 'Tarefa editada com sucesso!')
    return redirect('tarefas', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='tarefas', acao='excluir tarefas')
def excluir_tarefa(request, fazenda, vinculo):
    tarefa = get_object_or_404(Tarefa, id=request.POST.get('tarefa_id'), fazenda=fazenda)
    tarefa.delete()
    messages.success(request, 'Tarefa excluída com sucesso!')
    return redirect('tarefas', slug=fazenda.slug)

# ======================================================= CULTURAS =======================================================


@acesso_fazenda()
def culturas(request, fazenda, vinculo):
    lista = Cultura.objects.filter(fazenda=fazenda).order_by('nome')
    return render(request, 'dashboard/culturas.html', _contexto(request, fazenda, vinculo, culturas=lista))


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='culturas', acao='criar culturas')
def criar_cultura(request, fazenda, vinculo):
    _salvar(request, CulturaForm(request.POST), 'Cultura criada com sucesso!', fazenda=fazenda)
    return redirect('culturas', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='culturas', acao='editar culturas')
def editar_cultura(request, fazenda, vinculo):
    cultura = get_object_or_404(Cultura, id=request.POST.get('cultura_id'), fazenda=fazenda)
    _salvar(request, CulturaForm(request.POST, instance=cultura), 'Cultura editada com sucesso!')
    return redirect('culturas', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='culturas', acao='excluir culturas')
def excluir_cultura(request, fazenda, vinculo):
    cultura = get_object_or_404(Cultura, id=request.POST.get('cultura_id'), fazenda=fazenda)
    if cultura.plantios.exists():
        messages.error(request, 'Esta cultura não pode ser excluída porque está associada a plantios.')
    else:
        cultura.delete()
        messages.success(request, 'Cultura excluída com sucesso!')
    return redirect('culturas', slug=fazenda.slug)

# ======================================================= PLANTIOS =======================================================


@acesso_fazenda()
def plantios(request, fazenda, vinculo):
    return render(request, 'dashboard/plantios.html', _contexto(
        request, fazenda, vinculo,
        culturas=Cultura.objects.filter(fazenda=fazenda).order_by('nome'),
        talhoes=Talhao.objects.filter(fazenda=fazenda).order_by('nome'),
        plantios=Plantio.objects.filter(talhao__fazenda=fazenda).select_related('cultura', 'talhao').order_by('-dt_plantio'),
    ))


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='plantios', acao='cadastrar plantios')
def criar_plantio(request, fazenda, vinculo):
    _salvar(request, PlantioForm(request.POST, fazenda=fazenda), 'Plantio cadastrado com sucesso!')
    return redirect('plantios', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='plantios', acao='editar plantios')
def editar_plantio(request, fazenda, vinculo):
    plantio = get_object_or_404(Plantio, id=request.POST.get('plantio_id'), talhao__fazenda=fazenda)
    _salvar(request, PlantioForm(request.POST, instance=plantio, fazenda=fazenda), 'Plantio editado com sucesso!')
    return redirect('plantios', slug=fazenda.slug)


@require_POST
@acesso_fazenda(niveis=NIVEIS_GESTAO, redirecionar_para='plantios', acao='excluir plantios')
def excluir_plantio(request, fazenda, vinculo):
    plantio = get_object_or_404(Plantio, id=request.POST.get('plantio_id'), talhao__fazenda=fazenda)
    plantio.delete()
    messages.success(request, 'Plantio excluído com sucesso!')
    return redirect('plantios', slug=fazenda.slug)
