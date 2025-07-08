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
    slug            = models.SlugField(max_length=60, unique=True, blank=True)

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
    fazenda      = models.ForeignKey(Fazenda, on_delete=models.CASCADE)
    usuario      = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nivel_acesso = models.CharField(max_length=20, verbose_name="Nível de Acesso")

    class Meta:
        unique_together = ('fazenda', 'usuario')
        verbose_name = "Usuário da Fazenda"
        verbose_name_plural = "Usuários das Fazendas"

    def __str__(self):
        return f"{self.usuario} - {self.fazenda} ({self.nivel_acesso})"

class Cultura(models.Model):
    nome                = models.CharField(max_length=50)
    tp_cultura          = models.CharField(max_length=2)  # GC, GR, LG, PC, FR, FB
    descricao           = models.CharField(max_length=500)
    produtividade_media = models.FloatField(help_text="kg por hectare")
    fazenda             = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name='culturas')

    def __str__(self):
        return self.nome

class Talhao(models.Model):
    nome        = models.CharField(max_length=50)
    area        = models.DecimalField(max_digits=9, decimal_places=2)
    fazenda     = models.ForeignKey('Fazenda', on_delete=models.CASCADE, related_name='talhoes')

    def __str__(self):
        return self.nome
    
    def qtd_cultura(self):
        return self.plantios.count()

class Plantio(models.Model):
    dt_plantio           = models.DateField()
    dt_colheitaPrevista  = models.DateField()
    talhao               = models.ForeignKey(Talhao, on_delete=models.CASCADE, related_name='plantios')
    cultura              = models.ForeignKey(Cultura, on_delete=models.CASCADE, related_name='plantios')

    def __str__(self):
        return f"{self.cultura.nome} em {self.talhao.nome} ({self.dt_plantio})"

class Tarefa(models.Model):
    PRIORIDADE_CHOICES = [
        ('A', 'Alta'),
        ('M', 'Média'),
        ('B', 'Baixa'),
        ('U', 'Urgente'),
    ]

    titulo          = models.CharField(max_length=50)
    descricao       = models.CharField(max_length=500)
    prioridade      = models.CharField(max_length=1, choices=PRIORIDADE_CHOICES)
    dt_solicitacao  = models.DateField(auto_now_add=True)
    fazenda         = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name='tarefas')

    def __str__(self):
        return f"{self.titulo} ({self.get_prioridade_display()})"


