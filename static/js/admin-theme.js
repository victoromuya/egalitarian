(() => {
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  let preference;
  try { preference = localStorage.getItem('theme'); } catch (_) { /* Use system appearance if storage is unavailable. */ }
  let theme = preference === 'light' || preference === 'dark' ? preference : (systemTheme.matches ? 'dark' : 'light');
  function update(mode, persist = false) {
    theme = mode;
    document.documentElement.dataset.theme = mode;
    if (persist) {
      preference = mode;
      try { localStorage.setItem('theme', mode); } catch (_) { /* Switching still works without persistence. */ }
    }
    document.querySelectorAll('[data-admin-theme]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.adminTheme === mode));
    });
  }
  update(theme);
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-admin-theme]').forEach(button => {
      button.addEventListener('click', () => update(button.dataset.adminTheme, true));
    });
    update(theme);
  });
  systemTheme.addEventListener('change', event => {
    if (preference !== 'light' && preference !== 'dark') update(event.matches ? 'dark' : 'light');
  });
  window.addEventListener('storage', event => {
    if (event.key === 'theme') {
      preference = event.newValue;
      update(preference === 'light' || preference === 'dark' ? preference : (systemTheme.matches ? 'dark' : 'light'));
    }
  });
})();
