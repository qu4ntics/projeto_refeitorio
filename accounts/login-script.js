function mostrarSenha(){
    var inputSen = document.getElementById('senha')
    var btnMostrar = document.getElementById('btn-senha')
    
    if(inputSen.type === 'password'){
        inputSen.setAttribute('type', 'text')
        btnMostrar.classList.replace('bi-eye','bi-eye-slash')
    }else{
        inputSen.setAttribute('type', 'password')
        btnMostrar.classList.replace('bi-eye-slash', 'bi-eye')
    }
}

function mostrarSenhaConfirma(){
    var inputSen = document.getElementById('confirme-senha')
    var btnMostrar = document.getElementById('btn-conf-senha')
    
    if(inputSen.type === 'password'){
        inputSen.setAttribute('type', 'text')
        btnMostrar.classList.replace('bi-eye','bi-eye-slash')
    }else{
        inputSen.setAttribute('type', 'password')
        btnMostrar.classList.replace('bi-eye-slash', 'bi-eye')
    }
}