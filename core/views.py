from django.shortcuts import render, redirect
from .models import Fazenda, UsuarioFazenda
from usuario.models import Usuario

def criar_fazenda(request):
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(usuario_id=usuario_id) if usuario_id else None
    if not usuario_id:
        return redirect('entrar')  # Redireciona para login se não estiver logado

    if request.method == 'POST':
        nome = request.POST.get('nome')
        proprietario = request.POST.get('proprietario')
        uf = request.POST.get('uf')
        cidade = request.POST.get('cidade')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone')
        tamanho = request.POST.get('tamanho')

        # Cria a fazenda
        fazenda = Fazenda.objects.create(
            nome=nome,
            proprietario=proprietario,
            uf=uf,
            cidade=cidade,
            email=email,
            telefone=telefone,
            tamanho=tamanho
        )

        # Relaciona o usuário à fazenda com nível de acesso (exemplo: 'admin')
        usuario = Usuario.objects.get(usuario_id=usuario_id)
        UsuarioFazenda.objects.create(
            fazenda=fazenda,
            usuario=usuario,
            nivel_acesso='admin'
        )

        return redirect('dashboard')  # Redirecione para onde desejar após o cadastro

    return render(request, 'core/criar_fazenda.html', {'usuario': usuario, 'show_dashboard_btn': True})