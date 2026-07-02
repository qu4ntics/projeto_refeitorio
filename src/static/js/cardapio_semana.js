
document.querySelectorAll('.week-tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    document.querySelectorAll('.week-tab').forEach(function(t) {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.day-panel').forEach(function(p) {
      p.classList.remove('active');
    });

    this.classList.add('active');
    this.setAttribute('aria-selected', 'true');
    var panelId = this.getAttribute('data-panel');
    var panel = document.getElementById(panelId);
    if (panel) panel.classList.add('active');
  });
});

(function() {
  var todayPanel = document.querySelector('.day-label .day-today-badge');
  if (!todayPanel) return;
  var panel = todayPanel.closest('.day-panel');
  if (!panel) return;
  var panelId = panel.id;
  var tab = document.querySelector('[data-panel="' + panelId + '"]');
  if (!tab) return;

  document.querySelectorAll('.week-tab').forEach(function(t) {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  document.querySelectorAll('.day-panel').forEach(function(p) {
    p.classList.remove('active');
  });

  tab.classList.add('active');
  tab.setAttribute('aria-selected', 'true');
  panel.classList.add('active');
})();
