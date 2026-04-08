// news-website/js/careers.js
const JOBS_API_URL = `${CONFIG.API_BASE_URL}/jobs/active/`;

async function loadDynamicJobs() {
    const jobsContainer = document.getElementById('dynamic-jobs-container');
    const roleSelect = document.getElementById('applied-role');
    
    if (!jobsContainer) return;

    try {
        const response = await fetch(JOBS_API_URL);
        
        // --- NAYA CODE ADD KIYA: 404 HTML Error ko gracefully handle karne ke liye ---
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        // -------------------------------------------------------------------------

        const data = await response.json();
        // DRF returns paginated data inside 'results'
        const jobs = data.results || data;

        if (jobs.length === 0) {
            jobsContainer.innerHTML = '<p style="text-align: center; grid-column: 1/-1; color: var(--gray); font-size: 1.1rem;">Currently, there are no open positions. Check back later!</p>';
            return;
        }

        let jobsHtml = '';
        let optionsHtml = '<option value="">-- Select a role --</option>';

        jobs.forEach(job => {
            // 1. Job Card banana
            jobsHtml += `
                <div class="job-card">
                    <div class="job-title">${job.title}</div>
                    <div class="job-meta">
                        <span><i class="fas fa-map-marker-alt"></i> ${job.location}</span>
                        <span><i class="fas fa-briefcase"></i> ${job.employment_type_display}</span>
                    </div>
                    <div class="job-desc">${job.description}</div>
                    <a href="#apply-section" class="read-more" style="font-weight: bold;" onclick="document.getElementById('applied-role').value='${job.title}'">Apply Now &rarr;</a>
                </div>
            `;
            // 2. Dropdown Option banana
            optionsHtml += `<option value="${job.title}">${job.title}</option>`;
        });

        // Niche ka "General" option wapas add karna
        optionsHtml += '<option value="General / Other">General Application (Other)</option>';

        jobsContainer.innerHTML = jobsHtml;
        if (roleSelect) {
            roleSelect.innerHTML = optionsHtml;
        }

    } catch (error) {
        console.error("Error loading jobs:", error);
        jobsContainer.innerHTML = '<p style="text-align: center; grid-column: 1/-1; color: red;">Failed to load job postings. Please try again later.</p>';
    }
}



document.addEventListener('DOMContentLoaded', () => {
    loadDynamicJobs();
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
            const response = await apiFetch(`${CONFIG.API_BASE_URL}/contact/`, {
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
                const data = await response.json().catch(() => ({}));
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
