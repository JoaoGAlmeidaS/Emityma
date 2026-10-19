"""Controle de autenticação (sessão) e de acesso às fazendas.

O projeto usa um modelo de usuário próprio (`usuario.Usuario`) com o id
guardado em `request.session['usuario_id']`. Estes decorators centralizam
as verificações que antes eram repetidas em cada view.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from usuario.models import Usuario

from .models import Fazenda, UsuarioFazenda

NIVEL_ADMIN = 'Administrador'
NIVEL_GERENTE = 'Gerente'
NIVEL_OPERADOR = 'Operador'
NIVEIS_ACESSO = (NIVEL_ADMIN, NIVEL_GERENTE, NIVEL_OPERADOR)
NIVEIS_GESTAO = (NIVEL_ADMIN, NIVEL_GERENTE)

SESSION_KEY = 'usuario_id'


def usuario_da_sessao(request):
    """Retorna o usuário logado ou None (limpando sessões órfãs)."""
    usuario_id = request.session.get(SESSION_KEY)
    if not usuario_id:
        return None
    usuario = Usuario.objects.filter(usuario_id=usuario_id).first()
    if usuario is None:
        request.session.flush()
    return usuario


def usuario_logado(view):
    """Exige login; disponibiliza o usuário em `request.usuario`."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        usuario = usuario_da_sessao(request)
        if usuario is None:
            return redirect('entrar')
        request.usuario = usuario
        return view(request, *args, **kwargs)

    return wrapper


def acesso_fazenda(niveis=None, redirecionar_para=None, acao='realizar esta ação'):
    """Exige login e vínculo com a fazenda identificada por `slug`.

    - Usuários sem vínculo com a fazenda recebem 404 (não revela que ela existe).
    - Se `niveis` for informado e o nível do usuário não estiver na lista,
      exibe uma mensagem de erro e redireciona para `redirecionar_para`
      (nome de rota que recebe `slug`) ou para a página inicial da fazenda.

    A view decorada recebe `fazenda` e `vinculo` (UsuarioFazenda) como kwargs.
    """

    def decorator(view):
        @wraps(view)
        @usuario_logado
        def wrapper(request, slug, *args, **kwargs):
            fazenda = get_object_or_404(Fazenda, slug=slug)
            vinculo = get_object_or_404(UsuarioFazenda, fazenda=fazenda, usuario=request.usuario)
            if niveis and vinculo.nivel_acesso not in niveis:
                messages.error(request, f'Você não tem permissão para {acao}.')
                return redirect(redirecionar_para or 'dashboard_home', slug=slug)
            return view(request, *args, fazenda=fazenda, vinculo=vinculo, **kwargs)

        return wrapper

    return decorator
