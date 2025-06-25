from django.db import models
from usuario.models import Usuario
from django.utils.text import slugify

class Fazenda(models.Model):
    id_fazenda      = models.AutoField(primary_key=True, verbose_name="ID Fazenda")
    nome            = models.CharField(max_length=50, verbose_name="Nome")
    proprietario    = models.CharField(max_length=50, verbose_name="Proprietário")
    uf              = models.CharField(max_length=2, verbose_name="UF")
    cidade          = models.CharField(max_length=50, verbose_name="Cidade")
    email           = models.EmailField(max_length=50, verbose_name="Email")
    telefone        = models.CharField(max_length=30, verbose_name="Telefone")
    tamanho         = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Tamanho (ha)")
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    usuarios = models.ManyToManyField(
        Usuario,
        through='UsuarioFazenda',
        related_name='fazendas'
    )

    class Meta:
        verbose_name = "Fazenda"
        verbose_name_plural = "Fazendas"

    def __str__(self):
        return self.nome

class UsuarioFazenda(models.Model):
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nivel_acesso = models.CharField(max_length=20, verbose_name="Nível de Acesso")

    class Meta:
        unique_together = ('fazenda', 'usuario')
        verbose_name = "Usuário da Fazenda"
        verbose_name_plural = "Usuários das Fazendas"

    def __str__(self):
        return f"{self.usuario} - {self.fazenda} ({self.nivel_acesso})"
