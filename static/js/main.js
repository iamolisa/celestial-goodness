/* ============================================================
   Celestial Goodness Astrology & Tarot — Shared JavaScript (main.js)
   Loaded on every page via base.html.
   Handles: navbar toggle, toast notifications, page animations,
            and any other site-wide behaviour.
   ============================================================ */

/* ── Navbar mobile toggle ── */
(function () {
  const btn    = document.getElementById('menuBtn');
  const menu   = document.getElementById('mobileMenu');
  const iconM  = document.getElementById('iconMenu');
  const iconC  = document.getElementById('iconClose');

  if (!btn || !menu) return;

  btn.addEventListener('click', () => {
    const isOpen = menu.classList.toggle('open');
    // Keep hidden-class in sync for screen readers
    menu.setAttribute('aria-hidden', String(!isOpen));
    if (iconM) iconM.classList.toggle('hidden',  isOpen);
    if (iconC) iconC.classList.toggle('hidden', !isOpen);
  });

  // Close menu when any nav link is clicked
  menu.querySelectorAll('a').forEach(a =>
    a.addEventListener('click', () => {
      menu.classList.remove('open');
      menu.setAttribute('aria-hidden', 'true');
      if (iconM) iconM.classList.remove('hidden');
      if (iconC) iconC.classList.add('hidden');
    })
  );
})();


/* ── Toast notification ──
   Usage: showToast('Your message')           → gold border
          showToast('Error text', 'error')    → red border
   ──────────────────────────────────────────── */
let _toastTimer = null;

function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  if (!toast) return;

  toast.textContent = msg;
  toast.classList.toggle('error', type === 'error');
  toast.classList.add('show');

  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}


/* ── Scroll-triggered fade-in-up for .js-reveal elements ──
   Add class "js-reveal" to any element you want to animate
   in as it enters the viewport.
   ──────────────────────────────────────────────────────── */
(function () {
  const els = document.querySelectorAll('.js-reveal');
  if (!els.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fade-in-up');
          entry.target.style.opacity = '1';
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  els.forEach((el) => {
    el.style.opacity = '0';
    observer.observe(el);
  });
})();


/* ── Set current year in footer ── */
(function () {
  const el = document.getElementById('yr');
  if (el) el.textContent = new Date().getFullYear();
})();


/* ── Smooth page load fade-in ── */
document.addEventListener('DOMContentLoaded', () => {
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.3s ease';
  requestAnimationFrame(() => {
    document.body.style.opacity = '1';
  });
});


/* ── API helper ──
   Usage: const data = await api.post('/api/booking', payload);
          const data = await api.get('/api/admin/bookings');
   Returns parsed JSON; throws on network error.
   ──────────────────────────────────────────────────────────── */
const api = {
  async request(method, url, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  },
  get:    (url)          => api.request('GET',    url),
  post:   (url, body)    => api.request('POST',   url, body),
  patch:  (url, body)    => api.request('PATCH',  url, body),
  delete: (url)          => api.request('DELETE', url),
};
