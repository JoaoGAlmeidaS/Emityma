from django.shortcuts import render, redirect
from usuario.models import Usuario
from core.models import Fazenda

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

    return render(request, 'dashboard/dashboard_home.html', {'fazenda': fazenda, 'usuario': usuario, 'fazendas': fazendas})