from django.urls import path
from . import views

urlpatterns = [
    path('cadastrar-fazenda/', views.criar_fazenda, name='cadastrar_fazenda'),
]