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

        const result = await registerUser(name, email, password);
        if (result.success) {
            // Store email for verification page
            localStorage.setItem('waitingForEmailVerification', email);
            // Redirect to email verification page
            window.location.href = 'verify-email.html';
        } else {
            errorDiv.textContent = result.message;
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register';
        }
    });
});

// NAYA: Initialize Google Sign-in dynamically using CONFIG
window.onload = function () {
    if (window.google && google.accounts) {
        google.accounts.id.initialize({
            client_id: CONFIG.GOOGLE_CLIENT_ID, // Coming from js/config.js
            callback: handleGoogleLogin,        // Coming from js/auth.js
            context: "signup",
            ux_mode: "popup",
            auto_prompt: false
        });
        
        google.accounts.id.renderButton(
            document.getElementById("google-button-container"),
            { 
                theme: "outline", 
                size: "large", 
                shape: "rectangular", 
                text: "continue_with",
                logo_alignment: "center"
            }
        );
    }
};