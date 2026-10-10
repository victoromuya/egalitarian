(() => {
  const root = document.documentElement;
  const buttons = [...document.querySelectorAll('[data-theme-toggle]')];
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const readPreference = () => { try { return localStorage.getItem('egalitarian-theme'); } catch { return null; } };
  let chosen = readPreference();
  const apply = theme => {
    root.dataset.theme = theme;
    const dark = theme === 'dark';
    buttons.forEach(button => {
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
      button.title = `Switch to ${dark ? 'light' : 'dark'} mode`;
    });
  };
  apply(root.dataset.theme === 'dark' ? 'dark' : 'light');
  buttons.forEach(button => button.addEventListener('click', () => {
    chosen = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('egalitarian-theme', chosen); } catch {}
    apply(chosen);
  }));
  system.addEventListener('change', event => {
    if (chosen !== 'dark' && chosen !== 'light') apply(event.matches ? 'dark' : 'light');
  });
  window.addEventListener('storage', event => {
    if (event.key !== 'egalitarian-theme' && event.key !== null) return;
    chosen = readPreference();
    apply(chosen === 'light' || chosen === 'dark' ? chosen : (system.matches ? 'dark' : 'light'));
  });
})();
