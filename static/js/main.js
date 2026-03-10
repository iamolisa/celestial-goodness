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
  document.body.style.transition = 'opacity 0.4s ease';
  // Double rAF ensures browser has painted the opacity:0 frame
  // before we animate to 1 — prevents the stuck-dim bug
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.body.style.opacity = '1';
    });
  });
  // Safety net — always restore opacity after 800ms no matter what
  setTimeout(() => {
    document.body.style.opacity = '1';
    document.body.style.pointerEvents = 'auto';
  }, 800);
});


/* ── API helper ──
   Usage: const data = await api.post('/api/booking', payload);
          const data = await api.get('/api/admin/bookings');
   Returns parsed JSON; throws on network error.
   ──────────────────────────────────────────────────────────── */
const api = {
  async request(method, url, body = null) {
    try {
      const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body) opts.body = JSON.stringify(body);
      const res  = await fetch(url, opts);
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      console.error('API error:', method, url, err);
      return { ok: false, status: 0, data: { error: 'Network error' } };
    }
  },
  get:    (url)          => api.request('GET',    url),
  post:   (url, body)    => api.request('POST',   url, body),
  patch:  (url, body)    => api.request('PATCH',  url, body),
  delete: (url)          => api.request('DELETE', url),
};


/* ── Animated Star Field (canvas) ──────────────────────────────────────────
   Stars are fixed in the sky and only twinkle (fade in/out at their own pace).
   A very slow right-to-left parallax scroll gives the feel of gazing at a
   moving night sky — no upward drift, no flames, just stars.
   ─────────────────────────────────────────────────────────────────────────── */
(function initStarField() {
  document.querySelectorAll('.star-field').forEach(section => {
    const canvas = document.createElement('canvas');
    canvas.classList.add('star-canvas');
    section.insertBefore(canvas, section.firstChild);
    const ctx = canvas.getContext('2d');
    let stars = [], raf;

    /* Each star has:
       ox/oy  — original spawn position (used with scrollX offset)
       r      — radius (tiny, 0.3–1.5 px)
       base   — base opacity it oscillates around
       amp    — how much the twinkle deviates from base
       phase  — current position in the twinkle sine wave
       speed  — twinkle speed (radians per frame)
       color  — rgba prefix string                                         */
    function makeStar() {
      const base = Math.random() * 0.5 + 0.2;   // 0.2 – 0.7
      return {
        ox:    Math.random() * canvas.width  * 2, // spawn across 2× width so field wraps
        oy:    Math.random() * canvas.height,
        r:     Math.random() * 1.2 + 0.3,
        base,
        amp:   Math.random() * 0.3 + 0.1,         // twinkle depth
        phase: Math.random() * Math.PI * 2,        // random start in cycle
        speed: Math.random() * 0.02  + 0.008,      // twinkle speed (radians/frame)
        color: Math.random() < 0.65
          ? 'rgba(255,248,200,'   // near-white warm
          : 'rgba(210,160,60,',   // antique gold
      };
    }

    function resize() {
      canvas.width  = section.offsetWidth;
      canvas.height = section.offsetHeight;
      // ~1 star per 700 px² — enough to feel dense but not cluttered
      const count = Math.max(60, Math.floor((canvas.width * canvas.height) / 700));
      stars = Array.from({ length: count }, makeStar);
    }

    // scrollX advances 0.015 px per frame — imperceptibly slow rightward drift
    let scrollX = 0;

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      scrollX += 0.4;                               // ~24 px/sec at 60fps

      stars.forEach(s => {
        // Advance twinkle phase
        s.phase += s.speed;

        // Smooth sine-wave opacity — never flickers harshly
        const opacity = s.base + s.amp * Math.sin(s.phase);

        // Screen x wraps so the field tiles seamlessly
        const sx = (s.ox - scrollX) % canvas.width;
        const x  = sx < 0 ? sx + canvas.width : sx;

        ctx.beginPath();
        ctx.arc(x, s.oy, s.r, 0, Math.PI * 2);
        ctx.fillStyle = s.color + opacity.toFixed(3) + ')';
        ctx.fill();
      });

      raf = requestAnimationFrame(draw);
    }

    // Pause animation when section is off-screen
    const observer = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        if (!raf) draw();
      } else {
        cancelAnimationFrame(raf);
        raf = null;
      }
    }, { threshold: 0 });

    observer.observe(section);

    resize();
    window.addEventListener('resize', () => {
      cancelAnimationFrame(raf);
      raf = null;
      resize();
      draw();
    });
  });
})();
