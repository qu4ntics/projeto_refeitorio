// ReservaIF — main.js
// Scripts globais do sistema

function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar || !toggle) return;

  const mq = window.matchMedia('(max-width: 768px)');

  function setOpen(open) {
    sidebar.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    if (backdrop) {
      backdrop.hidden = !open;
      backdrop.classList.toggle('is-visible', open);
    }
    document.body.classList.toggle('sidebar-open', open);
  }

  function closeSidebar() {
    setOpen(false);
  }

  toggle.addEventListener('click', function () {
    setOpen(!sidebar.classList.contains('is-open'));
  });

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  sidebar.querySelectorAll('.menu-item').forEach(function (item) {
    item.addEventListener('click', closeSidebar);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  mq.addEventListener('change', function () {
    if (!mq.matches) closeSidebar();
  });
}

// Fechar alertas automaticamente após 5 segundos
document.addEventListener('DOMContentLoaded', function () {
  initSidebar();

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

  // Marcar item do menu como ativo com base na URL atual
  const currentPath = window.location.pathname;
  const menuItems = document.querySelectorAll('.menu-item');
  menuItems.forEach(function (item) {
    if (item.getAttribute('href') === currentPath) {
      item.classList.add('active');
    }
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
    console.log('clicou');
    const next = root.classList.contains('dark-mode') ? 'light-mode' : 'dark-mode';
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  });
}
