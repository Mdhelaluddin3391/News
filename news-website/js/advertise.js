// news-website/js/advertise.js

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('advertise-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Form ki values lena
        const companyName = document.getElementById('company-name').value.trim();
        const email = document.getElementById('email').value.trim();
        const interestedSlot = document.getElementById('interested-slot').value;
        const userMessage = document.getElementById('message').value.trim();
        const submitBtn = this.querySelector('.submit-btn');
        const statusDiv = document.getElementById('ad-status');

        // ContactMessage model (backend) ke liye data format karna
        // Hum subject aur message ko merge kar rahe hain taaki admin ko easily samajh aa jaye
        const subject = `Ad Inquiry: ${interestedSlot} - ${companyName}`;
        const finalMessage = `Company: ${companyName}\nInterested Slot: ${interestedSlot}\n\nMessage:\n${userMessage}`;

        // Reset UI status
        statusDiv.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';

        try {
            // Hum directly existing contact API use kar rahe hain
            const response = await fetch(`${CONFIG.API_BASE_URL}/contact/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    name: companyName, 
                    email: email, 
                    subject: subject, 
                    message: finalMessage 
                })
            });

            if (response.ok) {
                // Success
                statusDiv.textContent = 'Thank you for your interest! Our advertising team will contact you shortly.';
                statusDiv.style.backgroundColor = '#d1fae5'; 
                statusDiv.style.color = '#065f46';
                statusDiv.style.border = '1px solid #a7f3d0';
                statusDiv.style.display = 'block';
                this.reset(); // Form clear karna
            } else {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to submit inquiry.');
            }
        } catch (error) {
            // Error handling
            console.error('Ad inquiry form error:', error);
            statusDiv.textContent = error.message || 'An error occurred while submitting. Please try again later.';
            statusDiv.style.backgroundColor = '#fee2e2'; 
            statusDiv.style.color = '#b91c1c';
            statusDiv.style.border = '1px solid #fecaca';
            statusDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Inquiry';
        }
    });
});