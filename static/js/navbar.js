(() => {
  const nav = document.getElementById('main-nav');
  const toggle = document.getElementById('hamburger');
  const menu = document.getElementById('navigation-menu');
  const setOpen = (open) => {
    nav.classList.toggle('nav--open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  };
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('click', event => { if (!nav.contains(event.target)) setOpen(false); });
  nav.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  nav.addEventListener('focusout', event => { if (!nav.contains(event.relatedTarget)) setOpen(false); });
  menu.addEventListener('click', event => { if (event.target.closest('a')) setOpen(false); });
  window.matchMedia('(max-width: 1050px)').addEventListener('change', () => setOpen(false));
  nav.querySelector('.nav__link--active')?.setAttribute('aria-current', 'page');
})();
