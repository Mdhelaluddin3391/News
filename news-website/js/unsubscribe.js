// js/unsubscribe.js
const UNSUBSCRIBE_API = `${CONFIG.API_BASE_URL}/newsletter/unsubscribe/`; // Backend endpoint

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('unsubscribe-form');
    const errorDiv = document.getElementById('unsub-error');
    const successDiv = document.getElementById('unsub-success');

    // Prefill email if it comes from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const prefilledEmail = urlParams.get('email');
    if (prefilledEmail) {
        document.getElementById('email').value = prefilledEmail;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();

        // Reset messages
        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        if (!email) {
            errorDiv.textContent = 'Please enter a valid email address.';
            errorDiv.style.display = 'block';
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';

        try {
            // Actual API Call to backend
            const response = await fetch(UNSUBSCRIBE_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            if (response.ok) {
                form.style.display = 'none'; // Hide the form
                document.querySelector('.unsubscribe-message').style.display = 'none';
                successDiv.style.display = 'block';
            } else {
                throw new Error('Failed to unsubscribe. Please try again later.');
            }
        } catch (error) {
            errorDiv.textContent = error.message || 'Network Error. Please check your connection.';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Unsubscribe Me';
        }
    });
});