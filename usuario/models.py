from django.db import models

# Create your models here.
class Usuario(models.Model):
    usuario_id          = models.AutoField(primary_key=True, verbose_name="ID")
    usuario_nome        = models.CharField(max_length=80, unique=True, verbose_name="Nome")
    usuario_email       = models.EmailField(max_length=80, unique=True, verbose_name="Email")
    usuario_senha       = models.CharField(max_length=30, unique=False, verbose_name="Senha")
    usuario_dtCriacao   = models.DateField(auto_now_add=True, verbose_name="Data de Criação")
    usuario_imagem      = models.ImageField(upload_to='fotos/usuario', blank=True, verbose_name="Imagem")
