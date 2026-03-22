// js/unsubscribe.js
const UNSUBSCRIBE_API = `${CONFIG.API_BASE_URL}/newsletter/unsubscribe/`; 

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('unsubscribe-form');
    const errorDiv = document.getElementById('unsub-error');
    const successDiv = document.getElementById('unsub-success');
    const emailInputGroup = document.getElementById('email-input-group');
    const emailInput = document.getElementById('email');
    const submitBtn = form.querySelector('button[type="submit"]');
    const unsubMessage = document.querySelector('.unsubscribe-message');

    // URL se token ya prefilled email nikaalein
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const prefilledEmail = urlParams.get('email');

    // Agar token URL mein hai (Yani user ne email confirmation link par click kiya hai)
    if (token) {
        if (emailInputGroup) emailInputGroup.style.display = 'none'; // Email field chupa dein
        if (emailInput) emailInput.removeAttribute('required');
        
        unsubMessage.textContent = 'Please click the button below to confirm and permanently remove your email from our list.';
        submitBtn.textContent = 'Confirm Unsubscribe';
    } else if (prefilledEmail) {
        if (emailInput) emailInput.value = prefilledEmail;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';

        const payload = {};
        
        // Check karein payload mein kya bhejna hai
        if (token) {
            payload.token = token;
        } else {
            const email = emailInput.value.trim();
            if (!email) {
                errorDiv.textContent = 'Please enter a valid email address.';
                errorDiv.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Unsubscribe Me';
                return;
            }
            payload.email = email;
        }

        try {
            const response = await fetch(UNSUBSCRIBE_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                form.style.display = 'none'; // Form ko successfully hide karein
                unsubMessage.style.display = 'none';
                
                successDiv.innerHTML = `<i class="fas fa-check-circle" style="margin-right: 8px;"></i> ${data.message}`;
                successDiv.style.display = 'block';
            } else {
                throw new Error(data.error || 'Failed to unsubscribe. Please try again later.');
            }
        } catch (error) {
            errorDiv.textContent = error.message || 'Network Error. Please check your connection.';
            errorDiv.style.display = 'block';
        } finally {
            if (form.style.display !== 'none') {
                submitBtn.disabled = false;
                submitBtn.textContent = token ? 'Confirm Unsubscribe' : 'Unsubscribe Me';
            }
        }
    });
});