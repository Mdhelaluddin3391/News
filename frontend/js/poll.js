// js/poll.js
const POLL_API_URL = `${CONFIG.API_BASE_URL}/interactions/polls`;

async function loadActivePoll() {
    const pollSection = document.getElementById('poll-widget-section');
    const pollContainer = document.getElementById('poll-container');
    
    if (!pollSection || !pollContainer) return;

    // 1. Sabse pehle poll section ko hide kar do. 
    // Isse empty container frontend par nahi dikhega jab tak data load na ho jaye.
    pollSection.style.display = 'none';

    try {
        const response = await fetch(`${POLL_API_URL}/active/`);
        
        // 2. Agar API response sahi nahi hai (jaise 404 No Active Poll), toh yahin ruk jao (section hide hi rahega)
        if (!response.ok) {
            return;
        }

        const poll = await response.json();

        // 3. Check karein ki poll valid hai aur usme options majood hain ya nahi
        if (!poll || !poll.options || !Array.isArray(poll.options) || poll.options.length === 0) {
            console.warn("No active poll or options available.");
            return; // Agar options nahi hain, toh bhi section hide hi rahega
        }

        // 4. Agar yahan tak code aaya hai, iska matlab valid poll mil gaya hai. Ab section ko show kar do.
        pollSection.style.display = 'block'; 

        // Check karein ki user pehle hi vote de chuka hai ya nahi
        const hasVoted = localStorage.getItem(`poll_voted_${poll.id}`);

        if (hasVoted) {
            renderPollResults(poll, pollContainer);
        } else {
            renderPollForm(poll, pollContainer);
        }

    } catch (error) {
        console.error("Poll load error:", error);
        // Error aane par bhi section by default hide hi rahega, so frontend kharab nahi hoga
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
        const originalText = btn.textContent;
        btn.textContent = "Voting...";
        btn.disabled = true;

        try {
            const res = await fetch(`${POLL_API_URL}/vote/${selectedOption.value}/`, { method: 'POST' });
            if (res.ok) {
                localStorage.setItem(`poll_voted_${poll.id}`, 'true');
                if(typeof showToast === 'function') showToast("Vote submitted successfully!", "success");
                loadActivePoll();
            } else {
                if(typeof showToast === 'function') showToast("Failed to submit vote.", "error");
                btn.textContent = originalText;
                btn.disabled = false;
            }
        } catch (err) {
            console.error("Vote submission error:", err);
            btn.textContent = originalText;
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

    const totalVotes = poll.total_votes || 0;

    poll.options.forEach(opt => {
        const optVotes = opt.votes || 0;
        const percentage = totalVotes > 0 ? Math.round((optVotes / totalVotes) * 100) : 0;
        
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
        <div class="poll-total-votes"><i class="fas fa-users"></i> Total Votes: ${totalVotes}</div>
        <div style="text-align:center; font-size:0.8rem; color:var(--primary); margin-top:10px; font-weight:bold;">✓ You have already voted</div>
    `;

    container.innerHTML = resultsHtml;
}

// Page load hone par poll fetch karein
document.addEventListener('DOMContentLoaded', () => {
    // Thoda delay taaki baaki news jaldi load ho jayein
    setTimeout(loadActivePoll, 1000); 
});