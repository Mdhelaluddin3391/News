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

        const result = await loginUser(email, password);
        
        if (result.success) {
            const urlParams = new URLSearchParams(window.location.search);
            const redirect = urlParams.get('redirect') || '/';
            window.location.href = redirect;
        } else {
            if (result.needsVerification) {
                errorDiv.textContent = result.message;
                errorDiv.style.display = 'block';
                setTimeout(() => {
                    // ✅ ROUTING FIX: Redirect to the actual verification page using clean URL
                    window.location.href = "/verify-email";
                }, 2000);
            } else {
                errorDiv.textContent = result.message;
                errorDiv.style.display = 'block';
            }
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    });
});

// NAYA: Initialize Google Sign-in dynamically using CONFIG
window.onload = function () {
    if (window.google && google.accounts) {
        google.accounts.id.initialize({
            client_id: CONFIG.GOOGLE_CLIENT_ID, // Coming from js/config.js
            callback: handleGoogleLogin,        // Coming from js/auth.js
            context: "signin",
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
