"""Configurações usadas apenas para gerar o site estático do GitHub Pages.

Usa um banco SQLite em memória (o `db.sqlite3` local não é lido nem alterado)
e liga o modo demonstração dos templates.

    DJANGO_SETTINGS_MODULE=emityma.settings_pages python manage.py build_pages
"""

import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'somente-para-gerar-paginas-estaticas')
os.environ.setdefault('DJANGO_DEBUG', 'False')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'testserver')

from .settings import *  # noqa: E402,F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

STATIC_DEMO = True
