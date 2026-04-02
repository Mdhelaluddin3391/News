// js/verify-email.js

const API_BASE_URL = CONFIG.API_BASE_URL;
const TOKEN_KEY = 'feroxTimes_accessToken';

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('verify-email-form');
    const errorDiv = document.getElementById('verify-error');
    const successDiv = document.getElementById('verify-success');
    const resendBtn = document.getElementById('resend-btn');
    const submitBtn = form.querySelector('.auth-btn');
    const tokenInput = document.getElementById('token');

    // Check if verification token is in URL query params
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');

    if (tokenFromUrl) {
        // Auto-verify with token from URL
        verifyEmailWithToken(tokenFromUrl);
    }

    // Handle manual token submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const token = tokenInput.value.trim();

        if (!token) {
            errorDiv.textContent = 'Please enter the verification token.';
            errorDiv.style.display = 'block';
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying...';

        await verifyEmailWithToken(token);
    });

    // Resend verification email
    resendBtn.addEventListener('click', async (e) => {
        e.preventDefault();

        const email = localStorage.getItem('waitingForEmailVerification');
        if (!email) {
            errorDiv.textContent = 'Email not found. Please register again.';
            errorDiv.style.display = 'block';
            return;
        }

        resendBtn.disabled = true;
        resendBtn.textContent = 'Sending...';

        try {
            const response = await fetch(`${API_BASE_URL}/users/resend-verification-email/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            const data = await response.json();

            if (response.ok) {
                errorDiv.style.display = 'none';
                successDiv.style.display = 'block';
                successDiv.innerHTML = '<i class="fas fa-envelope"></i> Verification email sent! Check your inbox.';
            } else {
                errorDiv.textContent = data.error || 'Failed to resend verification email.';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Network error. Please try again.';
            errorDiv.style.display = 'block';
        } finally {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Verification Email';
        }
    });
});

async function verifyEmailWithToken(token) {
    const errorDiv = document.getElementById('verify-error');
    const successDiv = document.getElementById('verify-success');
    const formContainer = document.getElementById('verify-form-container');
    const submitBtn = document.querySelector('.auth-btn');

    try {
        const response = await fetch(`${API_BASE_URL}/users/verify-email/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });

        const data = await response.json();

        if (response.ok) {
            // Success!
            errorDiv.style.display = 'none';
            successDiv.style.display = 'block';
            formContainer.style.display = 'none';

            // Clear localStorage
            localStorage.removeItem('waitingForEmailVerification');

            // Redirect to login after 3 seconds
            setTimeout(() => {
                window.location.href = "/login";
            }, 3000);
        } else {
            errorDiv.textContent = data.error || 'Verification failed. Please try again.';
            errorDiv.style.display = 'block';
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Verify Email';
            }
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Verify Email';
        }
    }
}
