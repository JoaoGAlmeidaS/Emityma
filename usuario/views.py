from django.shortcuts import render, redirect
from .models import Usuario

# Create your views here.
def entrar(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        try:
            usuario = Usuario.objects.get(usuario_email=email, usuario_senha=senha)
            request.session['usuario_id'] = usuario.usuario_id
            return redirect('/dashboard/')
        except Usuario.DoesNotExist:
            return render(request, 'cadastro/login.html', {'error': 'Email ou senha incorretos'})

    return render(request, 'cadastro/login.html')

def cadastrar(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        
        if Usuario.objects.filter(usuario_nome=username).exists():
            return render(request, 'cadastro/cadastro.html', {'error': 'Usuário já existe'})
        if Usuario.objects.filter(usuario_email=email).exists():
            return render(request, 'cadastro/cadastro.html', {'error': 'Email já cadastrado'})
        usuario = Usuario(
            usuario_nome=username,
            usuario_email=email,
            usuario_senha=senha  # Salva como texto simples (tenho que mudar depois)
        )
        usuario.save()
        return redirect('entrar')
    return render(request, 'cadastro/cadastro.html')

def sair(request):
    request.session.flush()
    return redirect('entrar')
