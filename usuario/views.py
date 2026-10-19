from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from core.access import SESSION_KEY, usuario_da_sessao

from .models import Usuario


def entrar(request):
    if usuario_da_sessao(request):
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '')
        usuario = Usuario.objects.filter(usuario_email__iexact=email).first()
        if usuario and usuario.verificar_senha(senha):
            request.session.cycle_key()
            request.session[SESSION_KEY] = usuario.usuario_id
            return redirect('dashboard')
        return render(request, 'cadastro/login.html', {'error': 'Email ou senha incorretos.', 'email': email})

    return render(request, 'cadastro/login.html')


def cadastrar(request):
    if request.method == 'POST':
        nome = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '')
        contexto = {'nome': nome, 'email': email}

        erro = None
        if not nome or not email or not senha:
            erro = 'Preencha todos os campos.'
        elif Usuario.objects.filter(usuario_nome__iexact=nome).exists():
            erro = 'Usuário já existe.'
        elif Usuario.objects.filter(usuario_email__iexact=email).exists():
            erro = 'Email já cadastrado.'
        else:
            try:
                validate_password(senha)
            except ValidationError as exc:
                erro = ' '.join(exc.messages)

        if erro:
            return render(request, 'cadastro/cadastro.html', {**contexto, 'error': erro})

        usuario = Usuario(usuario_nome=nome, usuario_email=email)
        usuario.definir_senha(senha)
        usuario.save()
        return redirect('entrar')

    return render(request, 'cadastro/cadastro.html')


def sair(request):
    request.session.flush()
    return redirect('entrar')
