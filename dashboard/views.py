from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from usuario.models import Usuario
from core.models import Fazenda, Talhao, Cultura, Plantio, Tarefa, UsuarioFazenda
from django.db.models import Case, When, Value, IntegerField, Sum
from collections import defaultdict
from decimal import Decimal, InvalidOperation

def dashboard(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazendas = Fazenda.objects.filter(usuarios=usuario)

    if request.method == 'POST':
        fazenda_id = request.POST.get('fazenda_id')
        if fazenda_id:
            fazenda = Fazenda.objects.get(id_fazenda=fazenda_id)
            request.session['fazenda_id'] = fazenda_id
            return redirect('dashboard_home', slug=fazenda.slug)

    return render(request, 'dashboard/escolher_fazenda.html', {'fazendas': fazendas, 'usuario': usuario})



def dashboard_home(request, slug):
    fazenda = Fazenda.objects.get(slug=slug)


    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazendas = Fazenda.objects.filter(usuarios=usuario)

    if request.method == 'POST':
        fazenda = request.POST.get('fazenda')
        if fazenda:
            fazenda = Fazenda.objects.get(fazenda=fazenda)
            request.session['fazenda'] = fazenda
            return redirect('dashboard_home', slug=fazenda.slug)
        
        
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)


    tarefas_urgente = Tarefa.objects.filter(fazenda=fazenda, prioridade='U').count()
    tarefas_alta = Tarefa.objects.filter(fazenda=fazenda, prioridade='A').count()
    tarefas_media = Tarefa.objects.filter(fazenda=fazenda, prioridade='M').count()
    tarefas_baixa = Tarefa.objects.filter(fazenda=fazenda, prioridade='B').count()
    total_tarefas = tarefas_urgente + tarefas_alta + tarefas_media + tarefas_baixa

    def percentualB(qtd):
        return round((qtd / total_tarefas) * 100) if total_tarefas > 0 else 0
    

    talhoes = Talhao.objects.filter(fazenda=fazenda)

    area_total = talhoes.aggregate(total=Sum('area'))['total'] or 0

    culturas_area = defaultdict(float)
    area_total = 0

    for talhao in talhoes:
        ultimo_plantio = talhao.plantios.order_by('-dt_plantio').first()
        if ultimo_plantio:
            cultura_nome = ultimo_plantio.cultura.nome
            culturas_area[cultura_nome] += float(talhao.area)
            area_total += float(talhao.area)

    cultura_labels = []
    cultura_percentuais = []

    for cultura, area in culturas_area.items():
        percentual = round((area / area_total) * 100, 2) if area_total else 0
        cultura_labels.append(cultura)
        cultura_percentuais.append(percentual)


    plantios = Plantio.objects.filter(talhao__fazenda=fazenda).select_related('cultura', 'talhao')

    producao_total = Decimal('0')
    for p in plantios:
        try:
            produtividade = Decimal(p.cultura.produtividade_media)
            producao_total += produtividade * Decimal(p.talhao.area)
        except (InvalidOperation, TypeError, ValueError):
            continue


    context = {
        'fazenda': fazenda,
        'usuario': usuario,
        'fazendas': fazendas,
        'total_talhoes': Talhao.objects.filter(fazenda=fazenda).count(),
        'culturas_plantadas': Cultura.objects.filter(plantios__talhao__fazenda=fazenda).distinct().count(),
        'urgente_percentual': percentualB(tarefas_urgente),
        'alta_percentual': percentualB(tarefas_alta),
        'media_percentual': percentualB(tarefas_media),
        'baixa_percentual': percentualB(tarefas_baixa),
        'tarefas_urgente': tarefas_urgente,
        'tarefas_alta': tarefas_alta,
        'tarefas_media': tarefas_media,
        'tarefas_baixa': tarefas_baixa,
        'total_tarefas': total_tarefas,
        'plantios_ativos': Plantio.objects.filter(talhao__fazenda=fazenda, dt_colheitaPrevista__gte=timezone.now()).count(),
        'producao_estimada': ...,
        'nivel_acesso': usuario_fazenda.nivel_acesso,
        'cultura_labels': cultura_labels,
        'cultura_percentuais': cultura_percentuais,
        'producao_estimada': producao_total,
}

    return render(request, 'dashboard/dashboard_home.html', context)

# =======================================================GERENCIAMENTO DA FAZENDA=======================================================================================

def gerenciar_fazenda(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso

    talhoes = Talhao.objects.filter(fazenda=fazenda)

    if request.method == 'POST':
        nome = request.POST.get('nome')
        area = request.POST.get('area')
        if nome and area:
            Talhao.objects.create(
                nome=nome,
                area=area,
                fazenda=fazenda
            )
            return redirect('gerenciar_fazenda', slug=slug)

    context = {
        'fazenda': fazenda,
        'usuario': usuario,
        'talhoes': talhoes,
        'nivel_acesso': nivel_acesso,
    }
    return render(request, 'dashboard/gerenciar_fazenda.html', context)

def editar_talhao(request, slug):
    if request.method == 'POST':
        talhao_id = request.POST.get('talhao_id')
        nome = request.POST.get('nome')
        area = request.POST.get('area')
        talhao = get_object_or_404(Talhao, id=talhao_id)
        talhao.nome = nome
        talhao.area = area
        talhao.save()
    return redirect('gerenciar_fazenda', slug=slug)

def excluir_talhao(request, slug):
    if request.method == 'POST':
        talhao_id = request.POST.get('talhao_id')
        talhao = get_object_or_404(Talhao, id=talhao_id)
        talhao.delete()
    return redirect('gerenciar_fazenda', slug=slug)

def buscar_usuario_por_email(request, slug):
    email = request.GET.get('email')
    fazenda = get_object_or_404(Fazenda, slug=slug)
    try:
        usuario = Usuario.objects.get(usuario_email=email)
        if UsuarioFazenda.objects.filter(fazenda=fazenda, usuario=usuario).exists():
            return JsonResponse({'erro': 'Usuário já está cadastrado nesta fazenda.'}, status=400)
        return JsonResponse({
            'nome': usuario.usuario_nome,
            'email': usuario.usuario_email,
            'id': usuario.usuario_id
        })
    except Usuario.DoesNotExist:
        return JsonResponse({'erro': 'Usuário não encontrado.'}, status=404)
    

def adicionar_usuario_fazenda(request, slug):
    if request.method == 'POST':
        email = request.POST.get('email')
        nivel_acesso = request.POST.get('nivel_acesso')
        fazenda = get_object_or_404(Fazenda, slug=slug)
        try:
            usuario = Usuario.objects.get(usuario_email=email)
            if UsuarioFazenda.objects.filter(fazenda=fazenda, usuario=usuario).exists():
                messages.warning(request, 'Usuário já está associado a esta fazenda.')
            else:
                UsuarioFazenda.objects.create(fazenda=fazenda, usuario=usuario, nivel_acesso=nivel_acesso)
                messages.success(request, 'Usuário adicionado com sucesso!')
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
    return redirect('gerenciar_fazenda', slug=slug)

def editar_fazenda(request, slug):
    fazenda = get_object_or_404(Fazenda, slug=slug)
    if request.method == 'POST':
        fazenda.nome = request.POST.get('nome')
        fazenda.proprietario = request.POST.get('proprietario')
        fazenda.uf = request.POST.get('uf')
        fazenda.cidade = request.POST.get('cidade')
        fazenda.email = request.POST.get('email')
        fazenda.telefone = request.POST.get('telefone')
        fazenda.tamanho = request.POST.get('tamanho')
        fazenda.save()
        messages.success(request, 'Fazenda atualizada com sucesso!')
    return redirect('gerenciar_fazenda', slug=slug)

# =======================================================USUARIOS=======================================================================================

def usuarios_fazenda(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso
    usuarios = UsuarioFazenda.objects.filter(fazenda=fazenda)


    return render(request, 'dashboard/usuarios_fazenda.html', {
        'fazenda': fazenda,
        'usuarios': usuarios,
        'usuario': usuario,
        'nivel_acesso': nivel_acesso,
    })

def editar_usuario_fazenda(request, slug):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')
        usuario_fazenda_id = request.POST.get('usuario_fazenda_id')
        nivel_acesso = request.POST.get('nivel_acesso')
        usuario_fazenda = get_object_or_404(UsuarioFazenda, id=usuario_fazenda_id, fazenda__slug=slug)
        if usuario_fazenda.usuario.usuario_id == usuario_id:
            messages.error(request, 'Você não pode editar a si mesmo.')
            return redirect('usuarios_fazenda', slug=slug)
        usuario_fazenda.nivel_acesso = nivel_acesso
        usuario_fazenda.save()
        messages.success(request, 'Nível de acesso atualizado com sucesso!')
    return redirect('usuarios_fazenda', slug=slug)

def remover_usuario_fazenda(request, slug):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')
        usuario_fazenda_id = request.POST.get('usuario_fazenda_id')
        usuario_fazenda = get_object_or_404(UsuarioFazenda, id=usuario_fazenda_id, fazenda__slug=slug)
        if usuario_fazenda.usuario.usuario_id == usuario_id:
            messages.error(request, 'Você não pode remover a si mesmo.')
            return redirect('usuarios_fazenda', slug=slug)
        usuario_fazenda.delete()
        messages.success(request, 'Usuário removido com sucesso!')
    return redirect('usuarios_fazenda', slug=slug)

# =======================================================TAREFAS=======================================================================================

def tarefas(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso

    prioridade_order = Case(
        When(prioridade='U', then=Value(1)),
        When(prioridade='A', then=Value(2)),
        When(prioridade='M', then=Value(3)),
        When(prioridade='B', then=Value(4)),
        default=Value(5),
        output_field=IntegerField()
    )

    tarefas = Tarefa.objects.filter(fazenda=fazenda).annotate(
        prioridade_ordem=prioridade_order
    ).order_by('prioridade_ordem', 'dt_solicitacao')

    return render(request, 'dashboard/tarefas.html', {
        'fazenda': fazenda,
        'usuario': usuario,
        'nivel_acesso': nivel_acesso,
        'tarefas': tarefas,
    })

def criar_tarefa(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para criar tarefas.")
        return redirect('tarefas', slug=slug)

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        prioridade = request.POST.get('prioridade')
        Tarefa.objects.create(
            fazenda=fazenda,
            titulo=titulo,
            descricao=descricao,
            prioridade=prioridade
        )
        messages.success(request, "Tarefa criada com sucesso!")
    return redirect('tarefas', slug=slug)

def editar_tarefa(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para editar tarefas.")
        return redirect('tarefas', slug=slug)

    if request.method == 'POST':
        tarefa_id = request.POST.get('tarefa_id')
        tarefa = get_object_or_404(Tarefa, id=tarefa_id, fazenda=fazenda)
        tarefa.titulo = request.POST.get('titulo')
        tarefa.descricao = request.POST.get('descricao')
        tarefa.prioridade = request.POST.get('prioridade')
        tarefa.save()
        messages.success(request, "Tarefa editada com sucesso!")
    return redirect('tarefas', slug=slug)

def excluir_tarefa(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para excluir tarefas.")
        return redirect('tarefas', slug=slug)

    if request.method == 'POST':
        tarefa_id = request.POST.get('tarefa_id')
        tarefa = get_object_or_404(Tarefa, id=tarefa_id, fazenda=fazenda)
        tarefa.delete()
        messages.success(request, "Tarefa excluída com sucesso!")
    return redirect('tarefas', slug=slug)

# =======================================================CULTURA=======================================================================================

def culturas(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso

    culturas = Cultura.objects.filter(fazenda=fazenda)

    return render(request, 'dashboard/culturas.html', {
        'fazenda': fazenda,
        'usuario': usuario,
        'nivel_acesso': nivel_acesso,
        'culturas': culturas,
    })

def criar_cultura(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para criar culturas.")
        return redirect('culturas', slug=slug)

    if request.method == 'POST':
        nome = request.POST.get('nome')
        tp_cultura = request.POST.get('tp_cultura')
        descricao = request.POST.get('descricao')
        produtividade_media = request.POST.get('produtividade_media')
        Cultura.objects.create(
            nome=nome,
            tp_cultura=tp_cultura,
            descricao=descricao,
            produtividade_media=produtividade_media,
            fazenda=fazenda
        )
        messages.success(request, "Cultura criada com sucesso!")
    return redirect('culturas', slug=slug)

def editar_cultura(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para editar culturas.")
        return redirect('culturas', slug=slug)

    if request.method == 'POST':
        cultura_id = request.POST.get('cultura_id')
        cultura = get_object_or_404(Cultura, id=cultura_id)
        cultura.nome = request.POST.get('nome')
        cultura.tp_cultura = request.POST.get('tp_cultura')
        cultura.descricao = request.POST.get('descricao')
        cultura.produtividade_media = request.POST.get('produtividade_media')
        cultura.save()
        messages.success(request, "Cultura editada com sucesso!")
    return redirect('culturas', slug=slug)

def excluir_cultura(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')

    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        return redirect('culturas', slug=slug)

    if request.method == 'POST':
        cultura_id = request.POST.get('cultura_id')
        cultura = get_object_or_404(Cultura, id=cultura_id, fazenda=fazenda)

        if Plantio.objects.filter(cultura=cultura).exists():
            return redirect(f"{request.path}?erro_cultura_em_uso=1")

        cultura.delete()
        messages.success(request, "Cultura excluída com sucesso!")

    return redirect('culturas', slug=slug)

# =======================================================PLANTIO=======================================================================================

def plantios(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso

    culturas = Cultura.objects.filter(fazenda=fazenda)
    talhoes = Talhao.objects.filter(fazenda=fazenda)
    plantios = Plantio.objects.filter(talhao__fazenda=fazenda).select_related('cultura', 'talhao')

    return render(request, 'dashboard/plantios.html', {
        'fazenda': fazenda,
        'usuario': usuario,
        'nivel_acesso': nivel_acesso,
        'culturas': culturas,
        'talhoes': talhoes,
        'plantios': plantios,
    })


def criar_plantio(request, slug):
    fazenda = get_object_or_404(Fazenda, slug=slug)

    if request.method == 'POST':
        cultura_id = request.POST.get('cultura_id')
        talhao_id = request.POST.get('talhao_id')
        dt_plantio = request.POST.get('dt_plantio')
        dt_colheitaPrevista = request.POST.get('dt_colheitaPrevista')

        if not (cultura_id and talhao_id and dt_plantio and dt_colheitaPrevista):
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect('detalhar_fazenda', slug=slug)

        cultura = get_object_or_404(Cultura, id=cultura_id, fazenda=fazenda)
        talhao = get_object_or_404(Talhao, id=talhao_id, fazenda=fazenda)

        Plantio.objects.create(
            cultura=cultura,
            talhao=talhao,
            dt_plantio=dt_plantio,
            dt_colheitaPrevista=dt_colheitaPrevista
        )

        messages.success(request, "Plantio cadastrado com sucesso.")
        return redirect('plantios', slug=slug)
    
    return redirect('plantios', slug=slug)


def editar_plantio(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')

    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = get_object_or_404(UsuarioFazenda, fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para editar plantios.")
        return redirect('plantios', slug=slug)

    if request.method == 'POST':
        plantio_id = request.POST.get('plantio_id')
        plantio = get_object_or_404(Plantio, id=plantio_id)
        plantio.cultura_id = request.POST.get('cultura_id')
        plantio.talhao_id = request.POST.get('talhao_id')
        plantio.dt_plantio = request.POST.get('dt_plantio')
        plantio.dt_colheitaPrevista = request.POST.get('dt_colheitaPrevista')
        plantio.save()
        messages.success(request, "Plantio editado com sucesso!")

    return redirect('plantios', slug=slug)


def excluir_plantio(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')

    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = get_object_or_404(UsuarioFazenda, fazenda=fazenda, usuario=usuario)

    if usuario_fazenda.nivel_acesso not in ["Administrador", "Gerente"]:
        messages.error(request, "Você não tem permissão para excluir plantios.")
        return redirect('plantios', slug=slug)

    if request.method == 'POST':
        plantio_id = request.POST.get('plantio_id')
        plantio = get_object_or_404(Plantio, id=plantio_id)
        plantio.delete()
        messages.success(request, "Plantio excluído com sucesso!")

    return redirect('plantios', slug=slug)

# =======================================================COLHEITA=======================================================================================

def colheita(request, slug):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('entrar')
    usuario = Usuario.objects.get(usuario_id=usuario_id)
    fazenda = get_object_or_404(Fazenda, slug=slug)
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    nivel_acesso = usuario_fazenda.nivel_acesso

    culturas = Cultura.objects.filter(fazenda=fazenda)
    talhoes = Talhao.objects.filter(fazenda=fazenda)
    plantios = Plantio.objects.filter(talhao__fazenda=fazenda).select_related('cultura', 'talhao')

    return render(request, 'dashboard/colheitas.html', {
        'fazenda': fazenda,
        'usuario': usuario,
        'nivel_acesso': nivel_acesso,
        'culturas': culturas,
        'talhoes': talhoes,
        'plantios': plantios,
    })