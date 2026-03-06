// js/login.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form');
    const errorDiv = document.getElementById('login-error');
    const submitBtn = form.querySelector('.auth-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';

        const result = await loginUser(email, password); // Async call from auth.js
        
        if (result.success) {
            const urlParams = new URLSearchParams(window.location.search);
            const redirect = urlParams.get('redirect') || 'index.html';
            window.location.href = redirect;
        } else {
            errorDiv.textContent = result.message;
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    });
});