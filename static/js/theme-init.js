(() => {
  let saved;
  try { saved = localStorage.getItem('egalitarian-theme'); } catch {}
  const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = saved === 'light' || saved === 'dark' ? saved : (systemDark ? 'dark' : 'light');
})();
