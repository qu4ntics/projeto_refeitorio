document.addEventListener('DOMContentLoaded', () => {
  const drop = document.querySelector('.file-drop');
  const input = drop && drop.querySelector('input[type="file"]');
  const nomeEl = drop && drop.querySelector('.file-drop-filename');

  if (drop && input) {
    const atualizar = () => {
      const arquivo = input.files && input.files[0];
      drop.classList.toggle('has-file', !!arquivo);
      if (arquivo && nomeEl) nomeEl.textContent = arquivo.name;
    };

    input.addEventListener('change', atualizar);

    ['dragenter', 'dragover'].forEach((ev) =>
      drop.addEventListener(ev, (e) => {
        e.preventDefault();
        drop.classList.add('is-drag');
      })
    );
    ['dragleave', 'dragend', 'drop'].forEach((ev) =>
      drop.addEventListener(ev, (e) => {
        e.preventDefault();
        drop.classList.remove('is-drag');
      })
    );
    drop.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        atualizar();
      }
    });

    atualizar();
  }

  document.querySelectorAll('.import-opt').forEach((opt) => {
    const cb = opt.querySelector('input[type="checkbox"]');
    if (!cb) return;
    const sync = () => opt.classList.toggle('is-checked', cb.checked);
    cb.addEventListener('change', sync);
    sync();
  });
});
