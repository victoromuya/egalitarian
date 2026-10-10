(() => {
  const form = document.getElementById('exam-form');
  if (!form) return;
  const questions = [...form.querySelectorAll('.exam-question')];
  const timer = document.getElementById('timer');
  const status = document.getElementById('save-status');
  const progress = document.getElementById('answer-progress');
  const initialRemaining = Math.max(0, Number(form.dataset.deadline) - Number(form.dataset.serverNow));
  const started = performance.now();
  const flagKey = `exam-flags-${form.elements.submission_id.value}`;
  let flagged = new Set();
  try { flagged = new Set(JSON.parse(sessionStorage.getItem(flagKey) || '[]')); } catch (_) { /* Storage may be disabled. */ }
  let pendingSave = Promise.resolve();
  let submitting = false;
  let expired = false;
  let interval;

  function updateProgress() {
    let answered = 0;
    for (const question of questions) {
      const id = question.dataset.question;
      const selected = Boolean(question.querySelector('input:checked'));
      const isFlagged = flagged.has(id);
      if (selected) answered++;
      const nav = form.querySelector(`.exam-nav-button[data-q="${id}"]`);
      nav.classList.toggle('is-answered', selected);
      nav.classList.toggle('is-flagged', isFlagged);
      nav.setAttribute('aria-label', `Question ${question.dataset.number}, ${selected ? 'answered' : 'unanswered'}${isFlagged ? ', flagged' : ''}`);
      question.classList.toggle('is-flagged', isFlagged);
      const flag = question.querySelector('.exam-flag');
      flag.setAttribute('aria-pressed', String(isFlagged));
      flag.textContent = isFlagged ? 'Flagged — remove flag' : 'Flag for review';
    }
    progress.value = answered;
    document.getElementById('exam-progress').textContent = `${answered} of ${questions.length} answered`;
  }

  function save() {
    if (expired || submitting) return;
    const snapshot = new FormData(form);
    status.textContent = 'Saving answers…';
    pendingSave = pendingSave.then(async () => {
      try {
        const response = await fetch(form.dataset.saveUrl, { method: 'POST', body: snapshot, credentials: 'same-origin', headers: { 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value }, signal: AbortSignal.timeout(8000) });
        if (!response.ok) throw new Error('Save failed');
        status.textContent = 'Answers saved.';
      } catch (_) {
        status.textContent = 'Answers could not be saved. Check your connection; retry by selecting an answer again.';
      }
    });
  }

  async function submit(auto) {
    if (submitting) return;
    if (!auto) {
      const unanswered = questions.length - Number(progress.value);
      if (!window.confirm(`Submit your exam? ${unanswered ? `${unanswered} unanswered question${unanswered === 1 ? '' : 's'} will score zero.` : 'All questions are answered.'}`)) return;
    }
    submitting = true;
    clearInterval(interval);
    form.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = true; button.textContent = 'Submitting…'; });
    if (auto) { expired = true; document.getElementById('timer-note').textContent = 'Time is up. Submitting your saved answers…'; }
    await pendingSave;
    HTMLFormElement.prototype.submit.call(form);
  }

  function tick() {
    const remaining = Math.max(0, Math.ceil((initialRemaining - (performance.now() - started)) / 1000));
    timer.textContent = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
    timer.closest('.exam-clock').classList.toggle('is-urgent', remaining <= 300);
    if (remaining === 0) submit(true);
  }
  form.addEventListener('change', event => { if (event.target.matches('input[type="radio"]')) { updateProgress(); save(); } });
  form.addEventListener('submit', event => { event.preventDefault(); submit(false); });
  form.querySelectorAll('.exam-flag').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.q;
    if (flagged.has(id)) flagged.delete(id); else flagged.add(id);
    try { sessionStorage.setItem(flagKey, JSON.stringify([...flagged])); } catch (_) { /* Storage may be disabled. */ }
    updateProgress();
  }));
  form.querySelectorAll('.exam-nav-button').forEach(button => button.addEventListener('click', () => {
    const question = document.getElementById(`q${button.dataset.q}`);
    question.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    question.querySelector('input').focus({ preventScroll: true });
  }));
  window.addEventListener('online', save);
  updateProgress();
  interval = setInterval(tick, 250);
  tick();
})();
