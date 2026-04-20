// Y-axis formatting helpers shared across all Chart.js charts
window.BudgetChart = {
  getNiceMax: function(value) {
    if (value <= 0) return 1000;
    if (value <= 5000) return Math.ceil(value / 1000) * 1000;
    if (value <= 50000) return Math.ceil(value / 5000) * 5000;
    if (value <= 100000) return Math.ceil(value / 10000) * 10000;
    return Math.ceil(value / 50000) * 50000;
  },
  getStepSize: function(maxValue) {
    if (maxValue <= 1000) return 200;
    if (maxValue <= 5000) return 1000;
    if (maxValue <= 10000) return 2000;
    if (maxValue <= 50000) return 5000;
    if (maxValue <= 100000) return 10000;
    return 50000;
  },
  formatYen: function(value) {
    return '\u00a5' + Number(value).toLocaleString('ja-JP');
  },
  yAxisConfig: function(datasets) {
    var allValues = [].concat.apply([], datasets);
    var absMax = Math.max.apply(null, allValues.map(function(v) { return Math.abs(v); }));
    var niceMax = this.getNiceMax(absMax);
    var step = this.getStepSize(niceMax);
    var self = this;
    return {
      beginAtZero: true,
      suggestedMax: niceMax,
      ticks: {
        stepSize: step,
        precision: 0,
        callback: function(v) { return self.formatYen(v); }
      }
    };
  }
};
