// ReservaIF — main.js
// Scripts globais do sistema

function markActiveNavByPath() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.menu-item, .bottom-nav-item').forEach(function (item) {
    if (item.getAttribute('href') === currentPath) {
      item.classList.add('active');
    }
  });
}

// Fechar alertas automaticamente após 5 segundos
document.addEventListener('DOMContentLoaded', function () {
  markActiveNavByPath();

  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s';
      setTimeout(function () {
        alert.remove();
      }, 400);
    }, 5000);
  });
});

const STORAGE_KEY = 'reservaif-theme';
const root = document.documentElement;
const btn = document.getElementById('theme-toggle');
const icon = document.getElementById('theme-icon');

function applyTheme(theme) {
  const isDark = theme === 'dark-mode';
  root.classList.toggle('dark-mode', isDark);
  const iconLight = root.dataset.themeIconLight;
  const iconDark = root.dataset.themeIconDark;
  if (icon && iconLight && iconDark) {
    icon.src = isDark ? iconLight : iconDark;
  }
}

// Preferência salva (ou padrão claro)
const saved = localStorage.getItem(STORAGE_KEY) || 'light-mode';
applyTheme(saved);

if (btn) {
  btn.addEventListener('click', function () {
    const next = root.classList.contains('dark-mode') ? 'light-mode' : 'dark-mode';
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  });
}
