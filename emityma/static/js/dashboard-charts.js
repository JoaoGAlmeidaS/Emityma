// Gráficos da página inicial do dashboard (Chart.js 2).
// Os dados chegam via <script type="application/json"> (filtro json_script do Django).
(function () {
  'use strict';

  if (typeof Chart === 'undefined') {
    return;
  }

  var reduzirMovimento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var CORES = ['#1cc88a', '#4e73df', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#20c997', '#fd7e14'];
  var numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });

  Chart.defaults.global.defaultFontFamily = 'Nunito, -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  Chart.defaults.global.defaultFontColor = '#858796';

  var tooltipBase = {
    backgroundColor: 'rgb(255,255,255)',
    bodyFontColor: '#858796',
    borderColor: '#dddfeb',
    borderWidth: 1,
    xPadding: 15,
    yPadding: 15,
    displayColors: false,
    caretPadding: 10
  };

  function lerJson(id) {
    var elemento = document.getElementById(id);
    return elemento ? JSON.parse(elemento.textContent) : null;
  }

  function opcoes(extra) {
    var base = { maintainAspectRatio: false, animation: reduzirMovimento ? false : undefined };
    Object.keys(extra).forEach(function (chave) { base[chave] = extra[chave]; });
    return base;
  }

  // Área em produção por cultura (rosca)
  var canvasCulturas = document.getElementById('myPieChart');
  var culturas = lerJson('cultura-labels');
  if (canvasCulturas && culturas) {
    new Chart(canvasCulturas, {
      type: 'doughnut',
      data: {
        labels: culturas,
        datasets: [{
          data: lerJson('cultura-percentuais'),
          backgroundColor: CORES,
          hoverBorderColor: 'rgba(234, 236, 244, 1)'
        }]
      },
      options: opcoes({
        tooltips: Object.assign({}, tooltipBase, {
          displayColors: true,
          callbacks: {
            label: function (item, data) {
              return data.labels[item.index] + ': ' + numero.format(data.datasets[0].data[item.index]) + '%';
            }
          }
        }),
        legend: { display: true, position: 'bottom' },
        cutoutPercentage: 75
      })
    });
  }

  // Produção prevista por cultura (barras horizontais)
  var canvasProducao = document.getElementById('graficoProducao');
  var producao = lerJson('producao-labels');
  if (canvasProducao && producao) {
    new Chart(canvasProducao, {
      type: 'horizontalBar',
      data: {
        labels: producao,
        datasets: [{
          label: 'Produção prevista (t)',
          data: lerJson('producao-valores'),
          backgroundColor: '#1cc88a',
          hoverBackgroundColor: '#17a673',
          barPercentage: 0.7
        }]
      },
      options: opcoes({
        legend: { display: false },
        tooltips: Object.assign({}, tooltipBase, {
          callbacks: {
            label: function (item) { return numero.format(item.xLabel) + ' t'; }
          }
        }),
        scales: {
          xAxes: [{
            ticks: { beginAtZero: true, callback: function (valor) { return numero.format(valor) + ' t'; } },
            gridLines: { color: 'rgb(234, 236, 244)', zeroLineColor: 'rgb(234, 236, 244)', drawBorder: false }
          }],
          yAxes: [{ gridLines: { display: false, drawBorder: false } }]
        }
      })
    });
  }
})();
