(() => {
  const $ = (s, c=document) => c.querySelector(s);
  const $$ = (s, c=document) => [...c.querySelectorAll(s)];
  const header = $('.site-header');
  const progress = $('#progressBar');
  const langToggle = $('#langToggle');
  const menuToggle = $('#menuToggle');
  const mobileMenu = $('#mobileMenu');
  const subnav = $('#subnav');
  let lang = 'ko';
  try { lang = localStorage.getItem('gds-lang') || 'ko'; } catch(e) {}

  function onScroll(){
    const y = window.scrollY;
    header.classList.toggle('scrolled', y > 15);
    const max = document.documentElement.scrollHeight - innerHeight;
    if(progress) progress.style.width = (max ? (y/max*100) : 0) + '%';
    if(subnav) subnav.classList.toggle('stuck', subnav.getBoundingClientRect().top <= header.offsetHeight + 1);
  }
  addEventListener('scroll', onScroll, {passive:true}); onScroll();

  // Reveal on scroll
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if(e.isIntersecting){ $$('.reveal', e.target).forEach(el => el.classList.add('in')); }
  }), {threshold:.08, rootMargin:'0px 0px -5% 0px'});
  $$('[data-observe]').forEach(s => io.observe(s));
  $$('.hero .reveal, .page-hero .reveal').forEach(el => requestAnimationFrame(() => el.classList.add('in')));

  // Active nav (header + product sub-nav handled as separate groups)
  function trackNav(links){
    const secs = links.map(a => document.getElementById(a.dataset.section)).filter(Boolean);
    if(!secs.length) return;
    const obs = new IntersectionObserver(entries => entries.forEach(e => {
      if(e.isIntersecting){ links.forEach(a => a.classList.toggle('active', a.dataset.section === e.target.id)); }
    }), {rootMargin:'-42% 0px -48% 0px', threshold:0});
    secs.forEach(s => obs.observe(s));
  }
  trackNav($$('.desktop-nav a[data-section]'));
  trackNav($$('.subnav a[data-section]'));

  // Language toggle (persisted across pages)
  function applyLang(next){
    lang = next; document.documentElement.lang = lang;
    try { localStorage.setItem('gds-lang', lang); } catch(e) {}
    $$('[data-ko][data-en]').forEach(el => el.textContent = el.dataset[lang]);
    if(langToggle){ $$('span', langToggle).forEach((s,i) => s.classList.toggle('active', (lang==='ko'&&i===0)||(lang==='en'&&i===1))); }
    document.title = lang==='ko' ? 'GDS | 건설정보화시스템의 선두 GDS 지디에스' : 'GDS | Leader in Construction Information Systems';
  }
  if(langToggle) langToggle.addEventListener('click', () => applyLang(lang==='ko'?'en':'ko'));
  if(lang !== 'ko') applyLang(lang);

  // Content overrides saved from admin.html (content.json). Silently ignored when unavailable (e.g. file://).
  fetch('content.json?v=' + Date.now(), {cache:'no-store'}).then(r => r.ok ? r.json() : null).then(c => {
    if(!c) return;
    Object.entries(c.text || {}).forEach(([k,v]) => { const el = document.querySelector(`[data-cms="${k}"]`); if(!el) return; if(v.ko != null) el.dataset.ko = v.ko; if(v.en != null) el.dataset.en = v.en; });
    Object.entries(c.plain || {}).forEach(([k,v]) => { const el = document.querySelector(`[data-cms-text="${k}"]`); if(el) el.textContent = v; });
    Object.entries(c.img || {}).forEach(([k,v]) => { const el = document.querySelector(`[data-cms-img="${k}"]`); if(el && v) el.src = v; });
    Object.entries(c.href || {}).forEach(([k,v]) => { const el = document.querySelector(`[data-cms-href="${k}"]`); if(el && v) el.href = v; });
    Object.entries(c.src || {}).forEach(([k,v]) => { const el = document.querySelector(`[data-cms-src="${k}"]`); if(el && v) el.src = v; });
    applyLang(lang);
  }).catch(() => {});

  // Distributor inquiry form
  const dealerForm = $('#dealerForm');
  if(dealerForm){
    const status = $('#dealerStatus');
    dealerForm.addEventListener('submit', async e => {
      e.preventDefault();
      const fd = new FormData(dealerForm);
      const data = {company: fd.get('company')||'', name: fd.get('name')||'', region: fd.get('region')||'', phone: fd.get('phone')||'', email: fd.get('email')||'', message: fd.get('message')||'', items: fd.getAll('items'), lang};
      if(!data.company.trim() || !data.name.trim() || !data.email.trim()){ status.textContent = lang==='ko' ? '회사명, 담당자, 이메일을 입력해 주세요.' : 'Please fill in company, contact person and e-mail.'; status.className = 'form-status bad'; return; }
      status.textContent = lang==='ko' ? '전송 중…' : 'Sending…'; status.className = 'form-status';
      const btn = dealerForm.querySelector('button[type=submit]'); btn.disabled = true;
      try{
        const r = await fetch('/api/inquiry', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
        if(!r.ok) throw new Error('HTTP ' + r.status);
        dealerForm.reset();
        status.textContent = lang==='ko' ? '문의가 접수되었습니다. 확인 후 연락드리겠습니다.' : 'Your inquiry has been received. We will contact you shortly.'; status.className = 'form-status ok';
      }catch(err){
        // no server available: fall back to e-mail
        const body = encodeURIComponent(`회사명: ${data.company}
담당자: ${data.name}
지역: ${data.region}
연락처: ${data.phone}
이메일: ${data.email}
관심 품목: ${data.items.join(', ')}

${data.message}`);
        location.href = `mailto:gdskorea@gdskorea.net?subject=${encodeURIComponent('[총판 문의] ' + data.company)}&body=${body}`;
        status.textContent = lang==='ko' ? '이메일 프로그램으로 문의를 보냅니다.' : 'Opening your e-mail client to send the inquiry.'; status.className = 'form-status';
      }finally{ btn.disabled = false; }
    });
  }

  // Mobile menu
  function closeMenu(){ if(!mobileMenu) return; mobileMenu.classList.remove('open'); mobileMenu.setAttribute('aria-hidden','true'); menuToggle.setAttribute('aria-expanded','false'); }
  if(menuToggle && mobileMenu){
    menuToggle.addEventListener('click', () => { const open=!mobileMenu.classList.contains('open'); mobileMenu.classList.toggle('open',open); mobileMenu.setAttribute('aria-hidden',String(!open)); menuToggle.setAttribute('aria-expanded',String(open)); });
    $$('#mobileMenu a').forEach(a => a.addEventListener('click', closeMenu));
  }

  // Modals
  function openModal(id){ const m=document.getElementById(id); if(!m)return; m.classList.add('open'); m.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
  function closeModal(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  $$('.modal-open').forEach(b => b.addEventListener('click', () => openModal(b.dataset.modal)));
  $$('.modal-close').forEach(b => b.addEventListener('click', () => closeModal(b.closest('.modal'))));

  // Lightbox for documents / screenshots
  const lightbox = $('#lightbox');
  const lightboxImg = $('#lightboxImg');
  function closeLightbox(){ if(!lightbox) return; lightbox.classList.remove('open'); lightbox.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  if(lightbox){
    $$('[data-lightbox]').forEach(el => el.addEventListener('click', () => {
      lightboxImg.src = el.dataset.lightbox;
      const img = el.querySelector('img'); lightboxImg.alt = img ? img.alt : '';
      lightbox.classList.add('open'); lightbox.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden';
    }));
    $$('.lightbox-close').forEach(b => b.addEventListener('click', closeLightbox));
  }

  addEventListener('keydown', e => { if(e.key==='Escape'){ $$('.modal.open').forEach(closeModal); closeLightbox(); } });

  // close disclosure when anchor links are used on small screens
  $$('a[href^="#"]').forEach(a => a.addEventListener('click', () => { if(innerWidth<1050) closeMenu(); }));
})();
