from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Usuario(models.Model):
    usuario_id          = models.AutoField(primary_key=True, verbose_name="ID")
    usuario_nome        = models.CharField(max_length=80, unique=True, verbose_name="Nome")
    usuario_email       = models.EmailField(max_length=80, unique=True, verbose_name="Email")
    # Armazena apenas o hash da senha (formato dos hashers do Django).
    usuario_senha       = models.CharField(max_length=128, verbose_name="Senha")
    usuario_dtCriacao   = models.DateField(auto_now_add=True, verbose_name="Data de Criação")
    usuario_imagem      = models.ImageField(upload_to='fotos/usuario', blank=True, verbose_name="Imagem")

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.usuario_nome

    def definir_senha(self, senha):
        self.usuario_senha = make_password(senha)

    def verificar_senha(self, senha):
        return check_password(senha, self.usuario_senha)
