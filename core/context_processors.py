from django.conf import settings


def site(request):
    """Variáveis globais disponíveis em todos os templates."""
    return {'STATIC_DEMO': getattr(settings, 'STATIC_DEMO', False)}
