from django.contrib.auth.hashers import identify_hasher
from django.test import TestCase
from django.urls import reverse

from core.access import SESSION_KEY

from .models import Usuario


class CadastroTests(TestCase):
    def test_cadastro_grava_senha_com_hash(self):
        resposta = self.client.post(reverse('cadastrar'), {
            'username': 'Maria', 'email': 'maria@exemplo.com', 'senha': 'colheita-segura-2025',
        })
        self.assertRedirects(resposta, reverse('entrar'))
        usuario = Usuario.objects.get(usuario_email='maria@exemplo.com')
        self.assertNotEqual(usuario.usuario_senha, 'colheita-segura-2025')
        identify_hasher(usuario.usuario_senha)  # lança ValueError se não for hash
        self.assertTrue(usuario.verificar_senha('colheita-segura-2025'))

    def test_cadastro_rejeita_email_duplicado(self):
        existente = Usuario(usuario_nome='Ana', usuario_email='ana@exemplo.com')
        existente.definir_senha('colheita-segura-2025')
        existente.save()
        resposta = self.client.post(reverse('cadastrar'), {
            'username': 'Outra Ana', 'email': 'ANA@exemplo.com', 'senha': 'colheita-segura-2025',
        })
        self.assertContains(resposta, 'Email já cadastrado')
        self.assertEqual(Usuario.objects.count(), 1)

    def test_cadastro_rejeita_senha_fraca(self):
        resposta = self.client.post(reverse('cadastrar'), {
            'username': 'Joao', 'email': 'joao@exemplo.com', 'senha': '123',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.exists())


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = Usuario(usuario_nome='Ana', usuario_email='ana@exemplo.com')
        self.usuario.definir_senha('colheita-segura-2025')
        self.usuario.save()

    def test_login_correto_cria_sessao(self):
        resposta = self.client.post(reverse('entrar'), {'email': 'ana@exemplo.com', 'senha': 'colheita-segura-2025'})
        self.assertRedirects(resposta, reverse('dashboard'))
        self.assertEqual(self.client.session[SESSION_KEY], self.usuario.usuario_id)

    def test_login_com_senha_errada(self):
        resposta = self.client.post(reverse('entrar'), {'email': 'ana@exemplo.com', 'senha': 'errada'})
        self.assertContains(resposta, 'Email ou senha incorretos')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_sair_encerra_sessao(self):
        self.client.post(reverse('entrar'), {'email': 'ana@exemplo.com', 'senha': 'colheita-segura-2025'})
        self.client.get(reverse('sair'))
        self.assertNotIn(SESSION_KEY, self.client.session)
