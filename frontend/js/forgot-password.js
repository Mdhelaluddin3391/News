// js/forgot-password.js

// Forgot password endpoint - backend endpoint: /api/users/forgot-password/
const FORGOT_PASSWORD_API = `${CONFIG.API_BASE_URL}/users/forgot-password/`;

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('forgot-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        const errorDiv = document.getElementById('forgot-error');
        const successDiv = document.getElementById('forgot-success');
        const submitBtn = form.querySelector('.auth-btn');

        // Reset messages & disable button
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        try {
            const response = await fetch(FORGOT_PASSWORD_API, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });

            // Security Best Practice: Success message show karein taaki email enumeration na ho sake
            successDiv.textContent = 'If that email is registered, we have sent a password reset link. Please check your inbox.';
            successDiv.style.display = 'block';
            form.reset();
            
        } catch (error) {
            console.error('Forgot password network error:', error);
            // Agar server down hai ya network issue hai toh actual error dikhayein
            errorDiv.textContent = 'A network error occurred. Please try again later.';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send Reset Link';
        }
    });
});