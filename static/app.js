let currentUser = JSON.parse(localStorage.getItem('pm09_user') || 'null');
let currentPage = 1;
let debounceTimer = null;

function showSection(id) {
  ['sec-catalog', 'sec-booking', 'sec-cabinet', 'sec-auth'].forEach(s => {
    document.getElementById(s).classList.toggle('hidden', s !== id);
  });
  if (id === 'sec-cabinet') loadApplications();
}

function updateNav() {
  const info = document.getElementById('user-info');
  const btnCab = document.getElementById('nav-cabinet');
  const btnBook = document.getElementById('nav-book');
  const btnAuth = document.getElementById('nav-auth');
  const btnOut = document.getElementById('nav-logout');
  if (currentUser) {
    info.textContent = `${currentUser.full_name} (${currentUser.role})`;
    btnCab.classList.remove('hidden');
    btnBook.classList.remove('hidden');
    btnOut.classList.remove('hidden');
    btnAuth.classList.add('hidden');
  } else {
    info.textContent = 'Гость';
    btnCab.classList.add('hidden');
    btnBook.classList.add('hidden');
    btnOut.classList.add('hidden');
    btnAuth.classList.remove('hidden');
  }
}

function onSearchInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => { currentPage = 1; loadCatalog(); }, 300);
}

async function loadCatalog() {
  const q = document.getElementById('search-q').value;
  const cat = document.getElementById('filter-cat').value;
  const grid = document.getElementById('catalog-grid');
  grid.setAttribute('aria-busy', 'true');
  const res = await fetch(`/api/catalog?q=${encodeURIComponent(q)}&category=${encodeURIComponent(cat)}&page=${currentPage}&per_page=6`);
  const data = await res.json();
  grid.setAttribute('aria-busy', 'false');

  grid.innerHTML = data.items.map(s => {
    const svg = `data:image/svg+xml;utf8,<svg xmlns='http://w3.org' width='320' height='180'><rect width='320' height='180' fill='${encodeURIComponent(s.img_color)}'/><text x='50%' y='50%' fill='white' font-family='sans-serif' font-size='16' dominant-baseline='middle' text-anchor='middle'>${encodeURIComponent(s.category)}</text></svg>`;
    return `<article class="card">
      <img class="card-img" src="${svg}" alt="${s.name}" width="320" height="180" loading="lazy" decoding="async">
      <div class="card-body">
        <div>
          <span class="badge">${s.category}</span>
          <h2 style="margin:4px 0;font-size:17px;">${s.name}</h2>
          <div style="color:#57534e;font-size:13px;">Длительность: ${s.duration_min} мин.</div>
        </div>
        <div>
          <div class="price">${s.price.toFixed(2)} ₽</div>
          <button class="btn" style="width:100%;" onclick="openBooking(${s.id})">Записаться</button>
        </div>
      </div>
    </article>`;
  }).join('');

  const pages = Math.ceil(data.total / data.per_page);
  const pag = document.getElementById('pagination');
  pag.innerHTML = '';
  for (let p = 1; p <= pages; p++) {
    pag.innerHTML += `<button class="btn ${p === currentPage ? '' : 'btn-outline'}" onclick="currentPage=${p};loadCatalog()">${p}</button>`;
  }
}

async function initSelects() {
  const [resS, resSt] = await Promise.all([fetch('/api/catalog?per_page=50'), fetch('/api/stylists')]);
  const services = (await resS.json()).items;
  const stylists = await resSt.json();
  document.getElementById('book-service').innerHTML = services.map(s => `<option value="${s.id}">${s.name} — ${s.price} ₽</option>`).join('');
  document.getElementById('book-stylist').innerHTML = stylists.map(st => `<option value="${st.id}">${st.full_name} (${st.specialization})</option>`).join('');
}

function openBooking(serviceId) {
  if (!currentUser) { showSection('sec-auth'); return; }
  document.getElementById('book-service').value = serviceId;
  showSection('sec-booking');
}

document.getElementById('booking-form').onsubmit = async (e) => {
  e.preventDefault();
  const res = await fetch('/api/applications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: currentUser.id,
      service_id: document.getElementById('book-service').value,
      stylist_id: document.getElementById('book-stylist').value,
      start_date: document.getElementById('book-date').value.replace('T', ' ')
    })
  });
  if (res.ok) showSection('sec-cabinet');
};

async function loadApplications() {
  if (!currentUser) return;
  const res = await fetch(`/api/applications/my?user_id=${currentUser.id}&role=${currentUser.role}`);
  const data = await res.json();
  document.getElementById('cab-sum').textContent = data.total_sum.toFixed(2);
  const isStaff = currentUser.role === 'admin' || currentUser.role === 'operator';
  document.getElementById('apps-tbody').innerHTML = data.items.map(a => `<tr>
    <td>${a.id}</td><td>${a.client}</td><td>${a.service_name}</td><td>${a.stylist}</td>
    <td>${a.price.toFixed(2)} ₽</td><td>${a.start_date}</td>
    <td>${isStaff ? `<select aria-label="Статус записи ${a.id}" onchange="changeStatus(${a.id}, this.value)">
      <option value="1" ${a.status_id==1?'selected':''}>Новая</option>
      <option value="2" ${a.status_id==2?'selected':''}>В работе</option>
      <option value="3" ${a.status_id==3?'selected':''}>Выполнена</option>
      <option value="4" ${a.status_id==4?'selected':''}>Отменена</option>
    </select>` : a.status}</td>
    <td><button class="btn btn-danger" onclick="delApp(${a.id})">Удалить</button></td>
  </tr>`).join('');
}

async function changeStatus(id, status_id) {
  await fetch(`/api/applications/${id}/status`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status_id })
  });
  loadApplications();
}

async function delApp(id) {
  if (!confirm('Удалить запись?')) return;
  await fetch(`/api/applications/${id}`, { method: 'DELETE' });
  loadApplications();
}

document.getElementById('login-form').onsubmit = async (e) => {
  e.preventDefault();
  const res = await fetch('/api/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login: document.getElementById('login-inp').value, password: document.getElementById('pass-inp').value })
  });
  const data = await res.json();
  if (!res.ok) { alert(data.error); return; }
  currentUser = data.user;
  localStorage.setItem('pm09_user', JSON.stringify(currentUser));
  updateNav();
  showSection('sec-cabinet');
};

function logout() {
  currentUser = null;
  localStorage.removeItem('pm09_user');
  updateNav();
  showSection('sec-catalog');
}

updateNav();
loadCatalog();
initSelects();