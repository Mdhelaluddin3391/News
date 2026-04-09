const COMMENTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/comments/`;
const COMMENT_REPORTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/reports/comments/`;

// SECURITY FIX: Centralized HTML escaper
function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function fetchComments(articleId) {
    try {
        // IMPROVEMENT: Properly encode URI components
        const response = await fetch(`${COMMENTS_API_URL}?article=${encodeURIComponent(articleId)}`);
        if (!response.ok) throw new Error('Failed to fetch comments.');

        const data = await response.json();
        return data.results || data;
    } catch (error) {
        if (typeof window.reportFrontendError === 'function') {
            window.reportFrontendError(error, { scope: 'comments', action: 'fetchComments', articleId });
        }
        return [];
    }
}

async function postComment(articleId, text) {
    if (!getCurrentUser()) throw new Error('You must be logged in to comment.');

    const response = await apiFetch(COMMENTS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: articleId, text })
    }, { authRequired: true });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Failed to post comment. Please try again.');

    return data;
}

async function deleteComment(commentId) {
    if (!getCurrentUser()) throw new Error('You must be logged in.');

    const response = await apiFetch(`${COMMENTS_API_URL}${encodeURIComponent(commentId)}/`, {
        method: 'DELETE'
    }, { authRequired: true });

    if (!response.ok) throw new Error('Failed to delete comment.');
    return true;
}

async function reportComment(commentId, reason, description) {
    if (!getCurrentUser()) throw new Error('You must be logged in to report comments.');

    const response = await apiFetch(COMMENT_REPORTS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: commentId, reason, description })
    }, { authRequired: true });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const errorMessage = data.detail || data.comment || data.non_field_errors || 'Failed to report comment.';
        throw new Error(Array.isArray(errorMessage) ? errorMessage[0] : errorMessage);
    }
    return data;
}

function formatCommentDate(isoString) {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return 'Just now';

    return date.toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit'
    });
}

function showCommentFeedback(message, type = 'success') {
    const feedback = document.getElementById('comment-feedback') || document.getElementById('comment-feedback-toast');
    if (!feedback) return;

    feedback.textContent = message;
    const baseClass = feedback.id === 'comment-feedback-toast' ? 'comment-feedback comment-feedback-toast' : 'comment-feedback';
    feedback.className = `${baseClass} comment-feedback-${type}`;
    feedback.style.display = 'block';

    window.clearTimeout(showCommentFeedback.timeoutId);
    showCommentFeedback.timeoutId = window.setTimeout(() => {
        feedback.style.display = 'none';
    }, 4000);
}

function showCustomConfirm(message, onConfirmCallback) {
    document.getElementById('custom-confirm-overlay')?.remove();

    const overlay = document.createElement('div');
    overlay.id = 'custom-confirm-overlay';
    overlay.className = 'custom-modal-overlay';
    overlay.innerHTML = `
        <div class="custom-modal-box">
            <h3>Confirm Action</h3>
            <p>${escapeHtml(message)}</p>
            <div class="custom-modal-actions">
                <button class="custom-modal-btn custom-modal-cancel" id="custom-modal-cancel-btn">Cancel</button>
                <button class="custom-modal-btn custom-modal-delete" id="custom-modal-delete-btn">Delete</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('custom-modal-cancel-btn').addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 250);
    });

    document.getElementById('custom-modal-delete-btn').addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 250);
        onConfirmCallback();
    });

    setTimeout(() => overlay.classList.add('active'), 10);
}

function renderCommentForm(articleId, containerId, user, articleSlug) {
    const formContainer = document.getElementById('comment-form-container');
    if (!formContainer) return;

    if (!user) {
        // SECURITY FIX: Escaped articleSlug to prevent Reflected XSS
        formContainer.innerHTML = `
            <p class="login-prompt">
                <a href="/login?redirect=/article/${escapeHtml(articleSlug)}">Log in</a> to post a comment or flag one for review.
            </p>
        `;
        return;
    }

    formContainer.innerHTML = `
        <div class="comment-form">
            <h4>Add a Comment</h4>
            <textarea id="new-comment-text" rows="3" placeholder="Write your comment..."></textarea>
            <button id="submit-comment" type="button">Post Comment</button>
        </div>
    `;

    document.getElementById('submit-comment').addEventListener('click', async () => {
        const textarea = document.getElementById('new-comment-text');
        const button = document.getElementById('submit-comment');
        const text = textarea.value.trim();

        if (!text) return showCommentFeedback('Please write a comment before posting.', 'error');

        button.disabled = true;
        button.textContent = 'Posting...';

        try {
            await postComment(articleId, text);
            textarea.value = '';
            showCommentFeedback('Comment posted successfully.');
            await renderComments(articleId, containerId, articleSlug);
        } catch (error) {
            showCommentFeedback(error.message, 'error');
            button.disabled = false;
            button.textContent = 'Post Comment';
        }
    });
}

function showReportModal(commentId) {
    const existingOverlay = document.getElementById('report-comment-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    const overlay = buildReportModal();
    document.body.appendChild(overlay);

    const cancelButton = document.getElementById('report-cancel-btn');
    const form = document.getElementById('report-form');
    const reasonField = document.getElementById('report-reason');
    const descriptionField = document.getElementById('report-description');
    const submitButton = document.getElementById('report-submit-btn');

    if (!cancelButton || !form || !reasonField || !descriptionField || !submitButton) {
        overlay.remove();
        showCommentFeedback('Could not open the report form.', 'error');
        return;
    }

    cancelButton.addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 250);
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (!reasonField.value) {
            showCommentFeedback('Please select a reason before submitting.', 'error');
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = 'Submitting...';

        try {
            await reportComment(commentId, reasonField.value, descriptionField.value.trim());
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 250);
            showCommentFeedback('Report submitted. Our moderation team will review it shortly.');
        } catch (error) {
            showCommentFeedback(error.message, 'error');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Flag';
        }
    });

    setTimeout(() => overlay.classList.add('active'), 10);
}


async function renderComments(articleId, containerId, articleSlug) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const currentUser = typeof getCurrentUser === 'function' ? getCurrentUser() : null;
    const comments = await fetchComments(articleId);

    if (!comments.length) {
        container.innerHTML = '<p class="comments-empty">No comments yet. Start the conversation.</p>';
        renderCommentForm(articleId, containerId, currentUser, articleSlug);
        return;
    }

    container.innerHTML = comments.map((comment) => {
        const commentUser = comment.user_detail || {};
        const isOwner = currentUser && commentUser.id === currentUser.id;
        const deleteBtn = isOwner ? `<button type="button" class="comment-action-btn" data-delete-comment="${comment.id}">Delete</button>` : '';
        const reportBtn = currentUser && !isOwner ? `<button type="button" class="comment-action-btn" data-report-comment="${comment.id}">Report Flag</button>` : '';

        return `
            <article class="comment-card">
                <div class="comment-card-header">
                    <div>
                        <strong class="comment-author">${escapeHtml(commentUser.name || 'Anonymous')}</strong>
                        <span class="comment-author-role">${escapeHtml(commentUser.role || 'Reader')}</span>
                    </div>
                    <time class="comment-date" datetime="${escapeHtml(comment.created_at)}">${formatCommentDate(comment.created_at)}</time>
                </div>
                <p class="comment-text">${escapeHtml(comment.text)}</p>
                <div class="comment-actions">${deleteBtn}${reportBtn}</div>
            </article>
        `;
    }).join('');

    container.querySelectorAll('[data-delete-comment]').forEach(btn => {
        btn.addEventListener('click', () => {
            showCustomConfirm('Delete this comment permanently?', async () => {
                try {
                    await deleteComment(btn.dataset.deleteComment);
                    showCommentFeedback('Comment deleted successfully.');
                    await renderComments(articleId, containerId, articleSlug);
                } catch (error) {
                    showCommentFeedback(error.message, 'error');
                }
            });
        });
    });

    renderCommentForm(articleId, containerId, currentUser, articleSlug);
}

window.renderComments = renderComments;