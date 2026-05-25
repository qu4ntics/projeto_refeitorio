// ReservaIF — main.js
// Scripts globais do sistema

// Fechar alertas automaticamente após 5 segundos
document.addEventListener('DOMContentLoaded', function () {
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