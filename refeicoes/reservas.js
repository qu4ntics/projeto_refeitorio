document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
    });
});