// js/register.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    const errorDiv = document.getElementById('register-error');
    const submitBtn = form.querySelector('.auth-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const confirm = document.getElementById('confirm-password').value;

        // Basic validation
        if (password !== confirm) {
            errorDiv.textContent = 'Passwords do not match.';
            errorDiv.style.display = 'block';
            return;
        }
        if (password.length < 6) {
            errorDiv.textContent = 'Password must be at least 6 characters.';
            errorDiv.style.display = 'block';
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Registering...';

        const result = await registerUser(name, email, password); // Async call from auth.js
        if (result.success) {
            // Auto-login after registration
            await loginUser(email, password);
            window.location.href = 'index.html';
        } else {
            errorDiv.textContent = result.message;
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register';
        }
    });
});