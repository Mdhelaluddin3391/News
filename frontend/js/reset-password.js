// js/reset-password.js

// Aapke Django backend ka reset-password endpoint
const RESET_PASSWORD_API = `${CONFIG.API_BASE_URL}/users/reset-password/`; 

// Get token from URL (e.g., reset-password.html?token=abcdef123456)
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('reset-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const newPass = document.getElementById('new-password').value;
        const confirm = document.getElementById('confirm-password').value;
        const errorDiv = document.getElementById('reset-error');
        const successDiv = document.getElementById('reset-success');
        const submitBtn = form.querySelector('.auth-btn');

        // Reset messages
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        // Validation
        if (newPass !== confirm) {
            errorDiv.textContent = 'Passwords do not match.';
            errorDiv.style.display = 'block';
            return;
        }
        if (newPass.length < 6) {
            errorDiv.textContent = 'Password must be at least 6 characters.';
            errorDiv.style.display = 'block';
            return;
        }
        if (!token) {
            errorDiv.textContent = 'Invalid or missing reset token. Please request a new password reset link.';
            errorDiv.style.display = 'block';
            return;
        }

        // Disable button while processing
        submitBtn.disabled = true;
        submitBtn.textContent = 'Resetting...';

        try {
            // Actual API call to backend
            const response = await fetch(RESET_PASSWORD_API, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // Backend ko token aur naya password bhej rahe hain
                body: JSON.stringify({ token: token, password: newPass }) 
            });

            if (response.ok) {
                // Success
                successDiv.textContent = 'Your password has been reset successfully. Redirecting to login...';
                successDiv.style.display = 'block';
                form.reset();
                
                // Redirect to login after 3 seconds
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 3000);
            } else {
                // Handle API error (e.g., invalid or expired token)
                const data = await response.json();
                throw new Error(data.detail || data.error || 'Failed to reset password. The link might be expired.');
            }
        } catch (error) {
            console.error('Reset password error:', error);
            errorDiv.textContent = error.message || 'A network error occurred. Please try again later.';
            errorDiv.style.display = 'block';
        } finally {
            // Re-enable button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Reset Password';
        }
    });
});