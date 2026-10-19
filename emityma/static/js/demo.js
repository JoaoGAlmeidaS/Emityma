// Modo demonstração (GitHub Pages): não há servidor para receber formulários.
// Intercepta envios e ações que dependem do backend e mostra um aviso.
(function () {
  'use strict';

  var MENSAGEM = 'Demonstração somente leitura: esta ação precisa do servidor Django. Execute o projeto localmente para salvar alterações.';
  var timer = null;

  function avisar() {
    var aviso = document.querySelector('.demo-aviso');
    if (!aviso) {
      aviso = document.createElement('div');
      aviso.className = 'demo-aviso';
      aviso.setAttribute('role', 'status');
      aviso.setAttribute('aria-live', 'polite');
      document.body.appendChild(aviso);
    }
    aviso.textContent = MENSAGEM;
    aviso.hidden = false;
    window.clearTimeout(timer);
    timer = window.setTimeout(function () { aviso.hidden = true; }, 5000);
  }

  document.addEventListener('submit', function (event) {
    event.preventDefault();
    avisar();
  }, true);

  // Busca de usuário por e-mail (AJAX) em "Gerenciar fazenda".
  document.addEventListener('click', function (event) {
    if (event.target.closest && event.target.closest('#buscar-usuario')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      avisar();
    }
  }, true);
})();
