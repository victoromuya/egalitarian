(() => {
  const hero = document.querySelector('[data-hero]');
  if (!hero) return;
  const slides = [...hero.querySelectorAll('[data-slide]')];
  const choices = [...hero.querySelectorAll('[data-hero-choice]')];
  const pause = hero.querySelector('[data-hero-pause]');
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0;
  let paused = motion.matches;
  let timer;
  const schedule = () => {
    clearTimeout(timer);
    // Keep rotating while the pointer rests on the hero or its controls.
    // Only protect focus inside slide content, which becomes inert on rotation.
    const slideHasFocus = slides.some(slide => slide.contains(document.activeElement));
    if (!paused && !document.hidden && !slideHasFocus) {
      timer = setTimeout(() => show((current + 1) % slides.length), 10000);
    }
  };
  const show = (index) => {
    current = index;
    slides.forEach((slide, i) => {
      slide.classList.toggle('is-active', i === index);
      slide.setAttribute('aria-hidden', String(i !== index));
      slide.inert = i !== index;
      choices[i].setAttribute('aria-pressed', String(i === index));
    });
    schedule();
  };
  const updatePause = () => {
    pause.textContent = paused ? 'Play slides' : 'Pause slides';
    pause.setAttribute('aria-label', paused ? 'Start automatic slide rotation' : 'Pause automatic slide rotation');
    schedule();
  };
  choices.forEach((choice, i) => choice.addEventListener('click', () => show(i)));
  pause.addEventListener('click', () => { paused = !paused; updatePause(); });
  hero.addEventListener('focusin', schedule);
  hero.addEventListener('focusout', () => setTimeout(schedule, 0));
  document.addEventListener('visibilitychange', schedule);
  motion.addEventListener('change', () => { paused = motion.matches; updatePause(); });
  updatePause();
  show(0);
})();
