/* KitchenIQ — Auth JS */
const API = window.API_URL;

function showError(msg) {
    const el = document.getElementById('authError');
    if (!el) return;
    el.querySelector('.err-text').textContent = msg;
    el.classList.add('show');
}

function hideError() {
    const el = document.getElementById('authError');
    if (el) el.classList.remove('show');
}

function setLoading(btn, on, originalText) {
    if (on) {
        btn.dataset.original = btn.innerHTML;
        btn.innerHTML = '<span class="kiq-spinner"></span>';
        btn.disabled = true;
    } else {
        btn.innerHTML = originalText || btn.dataset.original;
        btn.disabled = false;
    }
}

async function apiCall(path, body) {
    const res = await fetch(API + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.message || `Error ${res.status}`);
    return data;
}

async function handleLogin(e) {
    e.preventDefault();
    hideError();
    const form = e.target;
    const btn = form.querySelector('button[type=submit]');
    const email = form.email.value.trim();
    const password = form.password.value;

    if (!email || !password) return showError('Please fill in all fields.');
    setLoading(btn, true);

    try {
        const data = await apiCall('/api/auth/login', { email, password });
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user || {}));
        localStorage.setItem('kitchen', JSON.stringify(data.kitchen || {}));
        window.location.href = 'dashboard.html';
    } catch (err) {
        showError(err.message);
        setLoading(btn, false, 'Login');
    }
}

async function handleSignup(e) {
    e.preventDefault();
    hideError();
    const form = e.target;
    const btn = form.querySelector('button[type=submit]');
    const full_name = form.full_name.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const confirm = form.confirm.value;

    if (!full_name || !email || !password || !confirm) return showError('Please fill in all fields.');
    if (password.length < 6) return showError('Password must be at least 6 characters.');
    if (password !== confirm) return showError('Passwords do not match.');
    setLoading(btn, true);

    try {
        const data = await apiCall('/api/auth/register', { email, password, full_name });
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user || {}));
        localStorage.setItem('kitchen', JSON.stringify(data.kitchen || {}));
        window.location.href = 'dashboard.html';
    } catch (err) {
        showError(err.message);
        setLoading(btn, false, 'Create Account');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (signupForm) signupForm.addEventListener('submit', handleSignup);

    // If already logged in, go to dashboard
    if (localStorage.getItem('token') && !window.location.pathname.includes('dashboard')) {
        // Only auto-redirect on auth pages
        if (loginForm || signupForm) window.location.href = 'dashboard.html';
    }
});