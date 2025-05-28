from django.shortcuts import render, redirect
from .models import Usuario

# Create your views here.
def entrar(request):
    return render(request, 'cadastro/login.html')

def cadastrar(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        # Verifica se já existe usuário com mesmo nome ou email
        if Usuario.objects.filter(usuario_nome=username).exists():
            return render(request, 'cadastro/cadastro.html', {'error': 'Usuário já existe'})
        if Usuario.objects.filter(usuario_email=email).exists():
            return render(request, 'cadastro/cadastro.html', {'error': 'Email já cadastrado'})
        usuario = Usuario(
            usuario_nome=username,
            usuario_email=email,
            usuario_senha=password  # Salva como texto simples (tenho que mudar depois)
        )
        usuario.save()
        return redirect('entrar')
    return render(request, 'cadastro/cadastro.html')