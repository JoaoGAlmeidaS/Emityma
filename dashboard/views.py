from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from usuario.models import Usuario
from core.models import Fazenda, Talhao, Cultura, Plantio, Tarefa, UsuarioFazenda

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
        fazenda_id = request.POST.get('fazenda_id')
        if fazenda_id:
            fazenda = Fazenda.objects.get(id_fazenda=fazenda_id)
            request.session['fazenda_id'] = fazenda_id
            return redirect('dashboard_home', slug=fazenda.slug)
        
    usuario_fazenda = UsuarioFazenda.objects.get(fazenda=fazenda, usuario=usuario)
    context = {
        'fazenda': fazenda,
        'usuario': usuario,
        'fazendas': fazendas,
        'total_talhoes': Talhao.objects.filter(fazenda=fazenda).count(),
        'culturas_plantadas': Cultura.objects.filter(plantios__talhao__fazenda=fazenda).distinct().count(),
        'tarefas_urgente': Tarefa.objects.filter(fazenda=fazenda, prioridade='U').count(),
        'tarefas_alta': Tarefa.objects.filter(fazenda=fazenda, prioridade='A').count(),
        'tarefas_media': Tarefa.objects.filter(fazenda=fazenda, prioridade='M').count(),
        'tarefas_baixa': Tarefa.objects.filter(fazenda=fazenda, prioridade='B').count(),
        'plantios_ativos': Plantio.objects.filter(talhao__fazenda=fazenda, dt_colheitaPrevista__gte=timezone.now()).count(),
        'producao_estimada': ...,
        'nivel_acesso': usuario_fazenda.nivel_acesso,  # Agora será "Administrador", "Gerente" ou "Operador"
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

    # Cadastro de novo talhão
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
        'talhoes': talhoes,  # Passe apenas a queryset!
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
        # Verifica se já está associado
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

    tarefas = Tarefa.objects.filter(fazenda=fazenda)

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

    culturas = Cultura.objects.filter(plantios__talhao__fazenda=fazenda).distinct()

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
        tp_cultura = request.POST.get('tipo_cultura')  # Ajuste aqui
        descricao = request.POST.get('descricao')
        produtividade_media = request.POST.get('produtividade_media')
        Cultura.objects.create(
            nome=nome,
            tp_cultura=tp_cultura,  # Ajuste aqui
            descricao=descricao,
            produtividade_media=produtividade_media
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
        cultura.tp_cultura = request.POST.get('tipo_cultura')  # Ajuste aqui
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
        messages.error(request, "Você não tem permissão para excluir culturas.")
        return redirect('culturas', slug=slug)

    if request.method == 'POST':
        cultura_id = request.POST.get('cultura_id')
        cultura = get_object_or_404(Cultura, id=cultura_id)
        cultura.delete()
        messages.success(request, "Cultura excluída com sucesso!")
    return redirect('culturas', slug=slug)