(function () {
	'use strict';

	var reduzirMovimento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	//===== Preloader
	function esconderPreloader() {
		var preloader = document.querySelector('.preloader');
		if (preloader) {
			preloader.style.opacity = '0';
			preloader.style.display = 'none';
		}
	}

	window.addEventListener('load', function () {
		window.setTimeout(esconderPreloader, reduzirMovimento ? 0 : 500);
	});

	//===== Menu fixo no topo e botão "voltar ao topo"
	var headerNavbar = document.querySelector('.navbar-area');
	var backToTop = document.querySelector('.scroll-top');

	function atualizarCabecalho() {
		var posicao = window.pageYOffset || document.documentElement.scrollTop;
		if (headerNavbar) {
			headerNavbar.classList.toggle('sticky', posicao > headerNavbar.offsetTop);
		}
		if (backToTop) {
			backToTop.style.display = posicao > 50 ? 'flex' : 'none';
		}
	}

	//===== Destaca no menu a seção visível
	var linksSecao = Array.prototype.filter.call(document.querySelectorAll('.page-scroll'), function (link) {
		var href = link.getAttribute('href');
		return href && href.charAt(0) === '#' && document.querySelector(href);
	});

	function atualizarMenuAtivo() {
		var posicao = (window.pageYOffset || document.documentElement.scrollTop) + 73;
		linksSecao.forEach(function (link) {
			var secao = document.querySelector(link.getAttribute('href'));
			var ativa = secao.offsetTop <= posicao && secao.offsetTop + secao.offsetHeight > posicao;
			link.classList.toggle('active', ativa);
			if (ativa) {
				link.setAttribute('aria-current', 'true');
			} else {
				link.removeAttribute('aria-current');
			}
		});
	}

	window.addEventListener('scroll', function () {
		atualizarCabecalho();
		atualizarMenuAtivo();
	}, { passive: true });
	atualizarCabecalho();

	//===== Fecha o menu mobile ao clicar em um link
	var navbarToggler = document.querySelector('.navbar-toggler');
	var navbarCollapse = document.querySelector('.navbar-collapse');

	if (navbarToggler && navbarCollapse) {
		document.querySelectorAll('.navbar-collapse a').forEach(function (link) {
			link.addEventListener('click', function () {
				navbarToggler.classList.remove('active');
				navbarCollapse.classList.remove('show');
				navbarToggler.setAttribute('aria-expanded', 'false');
			});
		});
		navbarToggler.addEventListener('click', function () {
			navbarToggler.classList.toggle('active');
		});
	}

	//===== Contadores
	if (typeof counterUp === 'function') {
		new counterUp({
			start: 0,
			duration: reduzirMovimento ? 0 : 2000,
			intvalues: true,
			interval: 100,
			append: 'K'
		}).start();
	}

	//===== Animações de entrada (desativadas para quem prefere menos movimento)
	if (typeof WOW === 'function' && !reduzirMovimento) {
		new WOW().init();
	}
})();
