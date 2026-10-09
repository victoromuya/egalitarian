(() => {
  const filters = [...document.querySelectorAll('[data-course-filter]')];
  const cards = [...document.querySelectorAll('[data-course-category]')];
  document.querySelectorAll('[data-learning-filter]').forEach(link => {
    link.addEventListener('click', () => {
      filters.find(button => button.dataset.courseFilter === link.dataset.learningFilter)?.click();
    });
  });
  filters.forEach(button => button.addEventListener('click', () => {
    filters.forEach(filter => {
      const selected = filter === button;
      filter.classList.toggle('is-active', selected);
      filter.setAttribute('aria-pressed', String(selected));
    });
    let visible = 0;
    cards.forEach(card => {
      const matches = card.dataset.courseCategory === button.dataset.courseFilter;
      card.hidden = !matches || visible >= 3;
      if (!card.hidden) visible++;
    });
    document.getElementById('course-filter-empty').hidden = visible > 0 || cards.length === 0;
  }));

  const storiesTrack = document.getElementById('stories-track');
  const storiesToggle = document.querySelector('.stories-toggle');
  if (storiesTrack && storiesToggle) {
    const duplicate = storiesTrack.firstElementChild.cloneNode(true);
    duplicate.setAttribute('aria-hidden', 'true');
    duplicate.setAttribute('inert', '');
    duplicate.classList.add('stories-group--duplicate');
    storiesTrack.appendChild(duplicate);
    storiesTrack.classList.add('is-ready');
    storiesToggle.addEventListener('click', () => {
      const paused = storiesToggle.getAttribute('aria-pressed') !== 'true';
      storiesToggle.setAttribute('aria-pressed', String(paused));
      storiesToggle.textContent = paused ? 'Resume scrolling' : 'Pause scrolling';
      storiesTrack.classList.toggle('is-paused', paused);
    });
  }

  const form = document.getElementById('newsletter-form');
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button');
    const status = document.getElementById('newsletter-status');
    button.disabled = true;
    status.textContent = 'Saving your subscription…';
    try {
      const response = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } });
      const result = await response.json();
      status.textContent = result.message;
      if (response.ok) form.reset();
    } catch {
      status.textContent = 'We couldn’t save your subscription. Please try again.';
    } finally {
      button.disabled = false;
    }
  });
})();
