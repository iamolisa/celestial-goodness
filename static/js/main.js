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
   Stars fly toward the viewer — warp/hyperspace effect.
   Each star starts tiny near the centre and grows outward, creating depth.
   ─────────────────────────────────────────────────────────────────────────── */
(function initStarField() {
  document.querySelectorAll('.star-field').forEach(section => {
    const canvas = document.createElement('canvas');
    canvas.classList.add('star-canvas');
    section.insertBefore(canvas, section.firstChild);
    const ctx = canvas.getContext('2d');
    let stars = [], raf;
    let W, H, CX, CY;

    function makeStar() {
      // Start at a random angle from centre, very close in
      const angle = Math.random() * Math.PI * 2;
      const dist  = Math.random() * 80 + 5;   // start close to centre
      return {
        angle,
        dist,
        speed: Math.random() * 1.8 + 0.6,     // how fast it flies outward
        r:     Math.random() * 1.0 + 0.2,      // base radius
        color: Math.random() < 0.65
          ? 'rgba(255,248,200,'
          : 'rgba(210,160,60,',
        phase: Math.random() * Math.PI * 2,
        twinkleSpeed: Math.random() * 0.03 + 0.01,
      };
    }

    function resize() {
      canvas.width  = W = section.offsetWidth;
      canvas.height = H = section.offsetHeight;
      CX = W / 2;
      CY = H / 2;
      const count = Math.max(80, Math.floor((W * H) / 600));
      // Spread initial distances so they don't all start at centre
      stars = Array.from({ length: count }, (_, i) => {
        const s = makeStar();
        s.dist = Math.random() * Math.hypot(CX, CY); // scattered start
        return s;
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);

      stars.forEach(s => {
        s.dist  += s.speed;
        s.phase += s.twinkleSpeed;

        // Reset star when it flies off screen
        const maxDist = Math.hypot(CX, CY) + 20;
        if (s.dist > maxDist) {
          s.dist  = Math.random() * 30 + 2;
          s.angle = Math.random() * Math.PI * 2;
          s.speed = Math.random() * 1.8 + 0.6;
        }

        const x = CX + Math.cos(s.angle) * s.dist;
        const y = CY + Math.sin(s.angle) * s.dist;

        // Star grows as it gets farther from centre — simulates flying toward you
        const progress = s.dist / Math.hypot(CX, CY);
        const radius   = s.r * (0.3 + progress * 1.8);
        const opacity  = Math.min(1, progress * 1.5) *
                         (0.5 + 0.4 * Math.sin(s.phase));

        // Draw a short streak behind the star for warp feel
        if (progress > 0.15) {
          const tailLen = Math.min(progress * 8, 12);
          const tx = x - Math.cos(s.angle) * tailLen;
          const ty = y - Math.sin(s.angle) * tailLen;
          const grad = ctx.createLinearGradient(tx, ty, x, y);
          grad.addColorStop(0, s.color + '0)');
          grad.addColorStop(1, s.color + (opacity * 0.6).toFixed(3) + ')');
          ctx.beginPath();
          ctx.moveTo(tx, ty);
          ctx.lineTo(x, y);
          ctx.strokeStyle = grad;
          ctx.lineWidth   = radius * 0.8;
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(x, y, Math.max(0.3, radius), 0, Math.PI * 2);
        ctx.fillStyle = s.color + opacity.toFixed(3) + ')';
        ctx.fill();
      });

      raf = requestAnimationFrame(draw);
    }

    const observer = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) { if (!raf) draw(); }
      else { cancelAnimationFrame(raf); raf = null; }
    }, { threshold: 0 });

    observer.observe(section);
    resize();
    window.addEventListener('resize', () => {
      cancelAnimationFrame(raf); raf = null;
      resize(); draw();
    });
  });
})();
