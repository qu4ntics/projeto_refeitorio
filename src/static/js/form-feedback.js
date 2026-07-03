(function () {
  'use strict';

  var SPINNER_HTML = '<span class="btn-spinner" aria-hidden="true"></span>';
  var DEFAULT_LOADING_TEXT = 'Processando...';

  var dialog = null;
  var dialogTitle = null;
  var dialogMessage = null;
  var dialogCancel = null;
  var dialogConfirm = null;
  var pendingForm = null;
  var lastFocused = null;

  function getDialogElements() {
    if (dialog) return;
    dialog = document.getElementById('confirm-dialog');
    if (!dialog) return;
    dialogTitle = dialog.querySelector('[data-confirm-title]');
    dialogMessage = dialog.querySelector('[data-confirm-message]');
    dialogCancel = dialog.querySelector('[data-confirm-cancel]');
    dialogConfirm = dialog.querySelector('[data-confirm-ok]');
  }

  function openDialog(title, message, confirmLabel) {
    getDialogElements();
    if (!dialog) return false;

    lastFocused = document.activeElement;
    if (dialogTitle) dialogTitle.textContent = title;
    if (dialogMessage) dialogMessage.textContent = message;
    if (dialogConfirm) dialogConfirm.textContent = confirmLabel || 'Confirmar';

    dialog.hidden = false;
    dialog.setAttribute('aria-hidden', 'false');
    document.body.classList.add('confirm-dialog-open');

    if (dialogConfirm) dialogConfirm.focus();
    return true;
  }

  function closeDialog() {
    getDialogElements();
    if (!dialog) return;

    if (pendingForm) {
      resetFormButtons(pendingForm);
    }

    dialog.hidden = true;
    dialog.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('confirm-dialog-open');
    pendingForm = null;

    if (dialogConfirm) {
      dialogConfirm.disabled = false;
      dialogConfirm.classList.remove('is-loading');
      dialogConfirm.removeAttribute('aria-busy');
      dialogConfirm.textContent = 'Sair';
    }
    if (dialogCancel) {
      dialogCancel.disabled = false;
    }

    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus();
    }
  }

  function isButtonElement(el) {
    return el && (el.tagName === 'BUTTON' || el.tagName === 'INPUT');
  }

  function resetButtonLoading(btn) {
    if (!isButtonElement(btn) || !btn.classList.contains('is-loading')) return;

    if (btn.dataset.loadingOriginal) {
      if (btn.tagName === 'INPUT') {
        btn.value = btn.dataset.loadingOriginal;
      } else {
        btn.innerHTML = btn.dataset.loadingOriginal;
      }
      delete btn.dataset.loadingOriginal;
    }

    btn.disabled = false;
    btn.classList.remove('is-loading');
    btn.removeAttribute('aria-busy');
  }

  function resetFormButtons(form) {
    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(resetButtonLoading);
  }

  function setButtonLoading(btn, loadingText) {
    if (!isButtonElement(btn) || btn.classList.contains('is-loading')) return;

    if (btn.tagName === 'INPUT') {
      if (!btn.dataset.loadingOriginal) {
        btn.dataset.loadingOriginal = btn.value;
      }
      btn.value = loadingText;
    } else {
      if (!btn.dataset.loadingOriginal) {
        btn.dataset.loadingOriginal = btn.innerHTML;
      }
      btn.innerHTML = SPINNER_HTML + '<span class="btn-label">' + loadingText + '</span>';
    }

    btn.disabled = true;
    btn.classList.add('is-loading');
    btn.setAttribute('aria-busy', 'true');
  }

  function applyFormLoading(form, submitter) {
    var buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    buttons.forEach(function (btn) {
      if (submitter && btn !== submitter) return;
      var text = btn.getAttribute('data-loading-text') || DEFAULT_LOADING_TEXT;
      setButtonLoading(btn, text);
    });
  }

  function handleFormSubmit(event) {
    var form = event.target;
    if (form.tagName !== 'FORM') return;
    if ((form.getAttribute('method') || 'get').toLowerCase() !== 'post') return;
    if (form.hasAttribute('data-no-loading')) return;
    if (form.classList.contains('logout-form') && form.dataset.confirmed !== 'true') return;

    var submitter = event.submitter || null;
    var confirmedLogout = form.classList.contains('logout-form') && form.dataset.confirmed === 'true';
    setTimeout(function () {
      applyFormLoading(form, submitter);
      if (confirmedLogout) {
        form.removeAttribute('data-confirmed');
      }
    }, 0);
  }

  function handleLogoutSubmit(event) {
    var form = event.target;
    if (!form.classList.contains('logout-form')) return;

    if (form.dataset.confirmed === 'true') {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    pendingForm = form;

    if (!openDialog(
      'Sair da conta?',
      'Tem certeza que deseja encerrar sua sessão?',
      'Sair'
    )) {
      form.dataset.confirmed = 'true';
      form.requestSubmit();
    }
  }

  function initDialogHandlers() {
    getDialogElements();
    if (!dialog) return;

    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) {
        closeDialog();
      }
    });

    if (dialogCancel) {
      dialogCancel.addEventListener('click', closeDialog);
    }

    if (dialogConfirm) {
      dialogConfirm.addEventListener('click', function () {
        if (!pendingForm) {
          closeDialog();
          return;
        }

        setButtonLoading(dialogConfirm, 'Saindo...');
        if (dialogCancel) dialogCancel.disabled = true;

        var form = pendingForm;
        closeDialog();
        form.dataset.confirmed = 'true';
        form.requestSubmit();
      });
    }

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && dialog && !dialog.hidden) {
        closeDialog();
      }
    });
  }

  document.addEventListener('submit', handleLogoutSubmit, true);
  document.addEventListener('submit', handleFormSubmit);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDialogHandlers);
  } else {
    initDialogHandlers();
  }
})();
