document.addEventListener('DOMContentLoaded', function() {
    // Previne múltiplos cliques em formulários (Double-click)
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Busca botões de envio dentro do formulário que está sendo enviado
            const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            
            buttons.forEach(btn => {
                // Delay zero permite que o evento de submit seja propagado antes de desabilitar
                setTimeout(() => {
                    btn.disabled = true;
                    btn.classList.add('btn-processing');
                    btn.textContent = 'Processando...';
                }, 0);
            });
        });
    });
});