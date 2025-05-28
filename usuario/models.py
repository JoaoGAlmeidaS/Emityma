from django.db import models

# Create your models here.
class Usuario(models.Model):
    usuario_id          = models.AutoField(primary_key=True)
    usuario_nome        = models.CharField(max_length=80, unique=True)
    usuario_email       = models.EmailField(max_length=80, unique=True)
    usuario_senha       = models.CharField(max_length=30, unique=False)
    usuario_dtCriacao   = models.DateField(auto_now_add=True)
    usuario_imagem      = models.ImageField(upload_to='fotos/usuario', blank=True)