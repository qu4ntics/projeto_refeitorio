document.addEventListener('DOMContentLoaded', function () {
  const STORAGE_KEY = 'reservaif-theme';
  const root = document.documentElement;
  const btn = document.getElementById('config-theme-toggle');
  const icon = document.getElementById('config-theme-icon');
  const label = document.getElementById('config-tema-label');
  const topBtn = document.getElementById('theme-toggle');
  const topIcon = document.getElementById('theme-icon');

  function syncThemeUi() {
    const isDark = root.classList.contains('dark-mode');
    if (label) label.textContent = isDark ? 'Escuro' : 'Claro';
    if (icon) {
      icon.classList.toggle('fa-moon', !isDark);
      icon.classList.toggle('fa-sun', isDark);
    }
    if (topIcon) {
      topIcon.classList.toggle('fa-moon', !isDark);
      topIcon.classList.toggle('fa-sun', isDark);
    }
  }

  function toggleTheme() {
    const next = root.classList.contains('dark-mode') ? 'light-mode' : 'dark-mode';
    localStorage.setItem(STORAGE_KEY, next);
    root.classList.toggle('dark-mode', next === 'dark-mode');
    syncThemeUi();
  }

  syncThemeUi();

  if (btn) {
    btn.addEventListener('click', toggleTheme);
  }

  if (topBtn) {
    topBtn.addEventListener('click', function () {
      setTimeout(syncThemeUi, 0);
    });
  }
});
