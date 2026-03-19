// news-website/js/careers.js

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('career-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Form ki values nikalna
        const name = document.getElementById('applicant-name').value.trim();
        const email = document.getElementById('applicant-email').value.trim();
        const phone = document.getElementById('applicant-phone').value.trim();
        const role = document.getElementById('applied-role').value;
        const portfolio = document.getElementById('portfolio-link').value.trim();
        const coverLetter = document.getElementById('cover-letter').value.trim();
        
        const submitBtn = this.querySelector('.submit-btn');
        const statusDiv = document.getElementById('career-status');

        // Django Admin ke ContactMessages ke liye data format banana
        const subject = `Job Application: ${role} - ${name}`;
        const finalMessage = `
Applicant Name: ${name}
Phone: ${phone}
Role Applied: ${role}
Portfolio/LinkedIn: ${portfolio}

Cover Letter:
${coverLetter}
        `.trim();

        // UI Reset karna
        statusDiv.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting Application...';

        try {
            // Existing Contact API par bhejna
            const response = await fetch(`${CONFIG.API_BASE_URL}/contact/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    name: name, 
                    email: email, 
                    subject: subject, 
                    message: finalMessage 
                })
            });

            if (response.ok) {
                // Success message
                statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Application submitted successfully! Our HR team will review your profile and contact you if shortlisted.';
                statusDiv.style.backgroundColor = '#d1fae5'; 
                statusDiv.style.color = '#065f46';
                statusDiv.style.border = '1px solid #a7f3d0';
                statusDiv.style.display = 'block';
                this.reset(); 
            } else {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to submit application.');
            }
        } catch (error) {
            // Error handling
            console.error('Career application error:', error);
            statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${error.message || 'An error occurred. Please try again later.'}`;
            statusDiv.style.backgroundColor = '#fee2e2'; 
            statusDiv.style.color = '#b91c1c';
            statusDiv.style.border = '1px solid #fecaca';
            statusDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Application';
        }
    });
});