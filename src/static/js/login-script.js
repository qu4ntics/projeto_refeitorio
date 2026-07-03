function mostrarSenha() {
    const inputSen = document.getElementById('senha');
    const btnMostrar = document.getElementById('btn-senha');
    const icon = btnMostrar.querySelector('i');

    if (inputSen.type === 'password') {
        inputSen.type = 'text';
        icon.classList.replace('bi-eye', 'bi-eye-slash');
        btnMostrar.setAttribute('aria-label', 'Ocultar senha');
    } else {
        inputSen.type = 'password';
        icon.classList.replace('bi-eye-slash', 'bi-eye');
        btnMostrar.setAttribute('aria-label', 'Mostrar senha');
    }
}

function mostrarSenhaConfirma() {
    const inputSen = document.getElementById('confirme-senha');
    const btnMostrar = document.getElementById('btn-conf-senha');
    const icon = btnMostrar.querySelector('i');

    if (inputSen.type === 'password') {
        inputSen.type = 'text';
        icon.classList.replace('bi-eye', 'bi-eye-slash');
        btnMostrar.setAttribute('aria-label', 'Ocultar senha');
    } else {
        inputSen.type = 'password';
        icon.classList.replace('bi-eye-slash', 'bi-eye');
        btnMostrar.setAttribute('aria-label', 'Mostrar senha');
    }
}
