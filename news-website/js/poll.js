// js/poll.js
const POLL_API_URL = `${CONFIG.API_BASE_URL}/interactions/polls`;

async function loadActivePoll() {
    const pollSection = document.getElementById('poll-widget-section');
    const pollContainer = document.getElementById('poll-container');
    
    if (!pollSection || !pollContainer) return;

    try {
        const response = await fetch(`${POLL_API_URL}/active/`);
        if (!response.ok) {
            pollSection.style.display = 'none'; // Agar poll nahi hai toh hide kar do
            return;
        }

        const poll = await response.json();
        pollSection.style.display = 'block'; // Poll mil gaya, toh show karo

        // Check karein ki user pehle hi vote de chuka hai ya nahi
        const hasVoted = localStorage.getItem(`poll_voted_${poll.id}`);

        if (hasVoted) {
            renderPollResults(poll, pollContainer);
        } else {
            renderPollForm(poll, pollContainer);
        }

    } catch (error) {
        console.error("Poll load error:", error);
    }
}

function renderPollForm(poll, container) {
    let optionsHtml = '';
    poll.options.forEach(opt => {
        optionsHtml += `
            <label class="poll-option-label">
                <input type="radio" name="poll_option" value="${opt.id}">
                ${opt.text}
            </label>
        `;
    });

    container.innerHTML = `
        <div class="poll-question">${poll.question}</div>
        ${poll.description ? `<div class="poll-desc">${poll.description}</div>` : ''}
        <form id="poll-form" data-poll-id="${poll.id}">
            ${optionsHtml}
            <button type="submit" class="poll-submit-btn">Submit Vote</button>
        </form>
    `;

    document.getElementById('poll-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const selectedOption = document.querySelector('input[name="poll_option"]:checked');
        
        if (!selectedOption) {
            if(typeof showToast === 'function') showToast("Please select an option to vote!", "error");
            return;
        }

        const btn = e.target.querySelector('button');
        btn.textContent = "Voting...";
        btn.disabled = true;

        try {
            const res = await fetch(`${POLL_API_URL}/vote/${selectedOption.value}/`, { method: 'POST' });
            if (res.ok) {
                // Vote count ho gaya, local storage mein mark kar do
                localStorage.setItem(`poll_voted_${poll.id}`, 'true');
                if(typeof showToast === 'function') showToast("Vote submitted successfully!", "success");
                // Reload poll to show results
                loadActivePoll();
            }
        } catch (err) {
            btn.textContent = "Submit Vote";
            btn.disabled = false;
        }
    });
}

function renderPollResults(poll, container) {
    let resultsHtml = `
        <div class="poll-question">${poll.question}</div>
        ${poll.description ? `<div class="poll-desc">${poll.description}</div>` : ''}
        <div style="margin-top: 15px;">
    `;

    poll.options.forEach(opt => {
        // Percentage nikalna
        const percentage = poll.total_votes > 0 ? Math.round((opt.votes / poll.total_votes) * 100) : 0;
        
        resultsHtml += `
            <div class="poll-result-item">
                <div class="poll-result-header">
                    <span>${opt.text}</span>
                    <span>${percentage}%</span>
                </div>
                <div class="poll-progress-bg">
                    <div class="poll-progress-fill" style="width: ${percentage}%;"></div>
                </div>
            </div>
        `;
    });

    resultsHtml += `
        </div>
        <div class="poll-total-votes"><i class="fas fa-users"></i> Total Votes: ${poll.total_votes}</div>
        <div style="text-align:center; font-size:0.8rem; color:var(--primary); margin-top:10px; font-weight:bold;">✓ You have already voted</div>
    `;

    container.innerHTML = resultsHtml;
}

// Page load hone par poll fetch karein
document.addEventListener('DOMContentLoaded', () => {
    // Thoda delay taaki baaki news jaldi load ho jayein
    setTimeout(loadActivePoll, 1000); 
});