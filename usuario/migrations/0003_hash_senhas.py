from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations, models


def gerar_hash_das_senhas(apps, schema_editor):
    """Converte senhas antigas, salvas em texto puro, para hash."""
    Usuario = apps.get_model('usuario', 'Usuario')
    for usuario in Usuario.objects.all():
        try:
            identify_hasher(usuario.usuario_senha)
        except ValueError:
            usuario.usuario_senha = make_password(usuario.usuario_senha)
            usuario.save(update_fields=['usuario_senha'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuario', '0002_alter_usuario_usuario_dtcriacao_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='usuario',
            options={'verbose_name': 'Usuário', 'verbose_name_plural': 'Usuários'},
        ),
        migrations.AlterField(
            model_name='usuario',
            name='usuario_senha',
            field=models.CharField(max_length=128, verbose_name='Senha'),
        ),
        migrations.RunPython(gerar_hash_das_senhas, migrations.RunPython.noop),
    ]
