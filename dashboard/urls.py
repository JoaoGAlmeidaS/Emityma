from django.urls import path, include
from dashboard import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # pré-tela de seleção
    path('home/', views.dashboard_home, name='dashboard_home'),  # dashboard real da fazenda
    path('core/', include('core.urls')),
    path('<slug:slug>/', views.dashboard_home, name='dashboard_home'),
]