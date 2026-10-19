from django.shortcuts import redirect, render

from .access import NIVEL_ADMIN, usuario_logado
from .forms import UFS, FazendaForm
from .models import UsuarioFazenda


@usuario_logado
def criar_fazenda(request):
    form = FazendaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        fazenda = form.save()
        UsuarioFazenda.objects.create(fazenda=fazenda, usuario=request.usuario, nivel_acesso=NIVEL_ADMIN)
        return redirect('dashboard_home', slug=fazenda.slug)

    return render(request, 'core/criar_fazenda.html', {
        'usuario': request.usuario,
        'form': form,
        'ufs': UFS,
        'show_dashboard_btn': True,
    })
