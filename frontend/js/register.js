document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    const errorDiv = document.getElementById('register-error');
    const successDiv = document.getElementById('register-success');
    const submitBtn = form.querySelector('.auth-btn');
    const nextSteps = document.getElementById('verification-next-steps');
    const verificationEmail = document.getElementById('verification-email');
    const openVerificationPageBtn = document.getElementById('open-verification-page');
    const resendLink = document.getElementById('register-resend-link');
    const altAuth = document.getElementById('register-alt-auth');
    const loginLink = document.getElementById('register-login-link');

    openVerificationPageBtn.addEventListener('click', () => {
        window.location.href = "/verify-email";
    });

    resendLink.addEventListener('click', async (event) => {
        event.preventDefault();
        const email = localStorage.getItem('waitingForEmailVerification');
        if (!email) {
            showError('No pending email verification found. Please register again.');
            return;
        }

        resendLink.textContent = 'Sending...';
        resendLink.style.pointerEvents = 'none';

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/users/resend-verification-email/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json();

            if (!response.ok) {
                showError(data.error || 'Could not resend the verification email.');
                return;
            }

            showSuccess(data.message || 'Verification email sent successfully.');
            nextSteps.style.display = 'block';
        } catch (error) {
            showError('Network error. Please try again.');
        } finally {
            resendLink.textContent = 'Resend verification email';
            resendLink.style.pointerEvents = '';
        }
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const confirm = document.getElementById('confirm-password').value;

        if (password !== confirm) {
            showError('Passwords do not match.');
            return;
        }

        if (password.length < 6) {
            showError('Password must be at least 6 characters.');
            return;
        }

        clearMessages();
        submitBtn.disabled = true;
        submitBtn.textContent = 'Registering...';

        const result = await registerUser(name, email, password);
        if (!result.success) {
            showError(result.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register';
            return;
        }

        localStorage.setItem('waitingForEmailVerification', result.email || email);
        verificationEmail.textContent = result.email || email;

        const successMessage = result.emailSent
            ? (result.message || 'Registration successful. Please verify your email.')
            : 'Registration successful, but the verification email could not be sent right now. Use the resend option below.';

        showSuccess(successMessage);
        form.style.display = 'none';
        if (altAuth) {
            altAuth.style.display = 'none';
        }
        if (loginLink) {
            loginLink.style.display = 'none';
        }
        nextSteps.style.display = 'block';
    });

    function clearMessages() {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
        successDiv.textContent = '';
        successDiv.style.display = 'none';
    }

    function showError(message) {
        successDiv.style.display = 'none';
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    function showSuccess(message) {
        errorDiv.style.display = 'none';
        successDiv.textContent = message;
        successDiv.style.display = 'block';
    }
});

window.onload = function () {
    if (window.google && google.accounts) {
        google.accounts.id.initialize({
            client_id: CONFIG.GOOGLE_CLIENT_ID,
            callback: handleGoogleLogin,
            context: 'signup',
            ux_mode: 'popup',
            auto_prompt: false
        });

        google.accounts.id.renderButton(
            document.getElementById('google-button-container'),
            {
                theme: 'outline',
                size: 'large',
                shape: 'rectangular',
                text: 'continue_with',
                logo_alignment: 'center'
            }
        );
    }
};
