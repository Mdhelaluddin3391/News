// js/contact.js

// Replace with your actual backend endpoint for handling contact forms
const CONTACT_API_URL = `${CONFIG.API_BASE_URL}/contact/`; 

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('contact-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form values
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const subject = document.getElementById('subject').value.trim();
        const message = document.getElementById('message').value.trim();
        const submitBtn = this.querySelector('.submit-btn');

        // Create a status message div if it doesn't exist
        let statusDiv = document.getElementById('contact-status');
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'contact-status';
            statusDiv.style.marginBottom = '1rem';
            statusDiv.style.padding = '10px';
            statusDiv.style.borderRadius = '5px';
            statusDiv.style.fontWeight = '500';
            form.insertBefore(statusDiv, form.firstChild);
        }

        // Reset status and disable button while submitting
        statusDiv.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        try {
            // Send data to backend API
            const response = await apiFetch(CONTACT_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, email, subject, message })
            });

            if (response.ok) {
                // Success
                statusDiv.textContent = 'Thank you for your message! We will get back to you soon.';
                statusDiv.style.backgroundColor = '#d1fae5'; // Light green
                statusDiv.style.color = '#065f46';
                statusDiv.style.border = '1px solid #a7f3d0';
                statusDiv.style.display = 'block';
                this.reset(); // Clear the form
            } else {
                // Handle API validation errors
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || 'Failed to send message.');
            }
        } catch (error) {
            // Error
            console.error('Contact form error:', error);
            statusDiv.textContent = error.message || 'An error occurred while sending your message. Please try again later.';
            statusDiv.style.backgroundColor = '#fee2e2'; // Light red
            statusDiv.style.color = '#b91c1c';
            statusDiv.style.border = '1px solid #fecaca';
            statusDiv.style.display = 'block';
        } finally {
            // Re-enable button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send Message';
        }
    });
});
