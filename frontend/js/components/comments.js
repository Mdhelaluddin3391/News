// frontend/js/components/comments.js

const COMMENTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/comments/`;
const COMMENT_REPORTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/reports/comments/`;

// SECURITY FIX: Centralized HTML escaper (Aapne banaya tha, ise as backup rakha hai)
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

    // ✅ SECURITY FIX: Created modal using DOM API instead of innerHTML to completely block DOM XSS
    const modalBox = document.createElement('div');
    modalBox.className = 'custom-modal-box';

    const h3 = document.createElement('h3');
    h3.textContent = 'Confirm Action';

    const p = document.createElement('p');
    p.textContent = message; // textContent automatically escapes dangerous chars

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'custom-modal-actions';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'custom-modal-btn custom-modal-cancel';
    cancelBtn.id = 'custom-modal-cancel-btn';
    cancelBtn.textContent = 'Cancel';

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'custom-modal-btn custom-modal-delete';
    deleteBtn.id = 'custom-modal-delete-btn';
    deleteBtn.textContent = 'Delete';

    actionsDiv.appendChild(cancelBtn);
    actionsDiv.appendChild(deleteBtn);
    modalBox.appendChild(h3);
    modalBox.appendChild(p);
    modalBox.appendChild(actionsDiv);
    overlay.appendChild(modalBox);

    document.body.appendChild(overlay);

    cancelBtn.addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 250);
    });

    deleteBtn.addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 250);
        onConfirmCallback();
    });

    setTimeout(() => overlay.classList.add('active'), 10);
}

function renderCommentForm(articleId, containerId, user, articleSlug) {
    const formContainer = document.getElementById('comment-form-container');
    if (!formContainer) return;

    formContainer.innerHTML = ''; // Clear the container safely

    if (!user) {
        // ✅ SECURITY FIX: Built login prompt safely
        const promptP = document.createElement('p');
        promptP.className = 'login-prompt';

        const loginLink = document.createElement('a');
        loginLink.href = `/login?redirect=/article/${encodeURIComponent(articleSlug)}`;
        loginLink.textContent = 'Log in';

        promptP.appendChild(loginLink);
        promptP.appendChild(document.createTextNode(' to post a comment or flag one for review.'));
        
        formContainer.appendChild(promptP);
        return;
    }

    // ✅ SECURITY FIX: Built comment form safely via DOM API
    const formDiv = document.createElement('div');
    formDiv.className = 'comment-form';

    const h4 = document.createElement('h4');
    h4.textContent = 'Add a Comment';

    const textarea = document.createElement('textarea');
    textarea.id = 'new-comment-text';
    textarea.rows = 3;
    textarea.placeholder = 'Write your comment...';

    const submitBtn = document.createElement('button');
    submitBtn.id = 'submit-comment';
    submitBtn.type = 'button';
    submitBtn.textContent = 'Post Comment';

    formDiv.appendChild(h4);
    formDiv.appendChild(textarea);
    formDiv.appendChild(submitBtn);
    formContainer.appendChild(formDiv);

    submitBtn.addEventListener('click', async () => {
        const text = textarea.value.trim();

        if (!text) return showCommentFeedback('Please write a comment before posting.', 'error');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Posting...';

        try {
            await postComment(articleId, text);
            textarea.value = '';
            showCommentFeedback('Comment posted successfully.');
            await renderComments(articleId, containerId, articleSlug);
        } catch (error) {
            showCommentFeedback(error.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Post Comment';
        }
    });
}

function showReportModal(commentId) {
    const existingOverlay = document.getElementById('report-comment-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    const overlay = buildReportModal(); // Note: ensure this function also uses DOM element creation properly
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

    container.innerHTML = ''; // Safely clear old comments

    if (!comments.length) {
        const emptyMsg = document.createElement('p');
        emptyMsg.className = 'comments-empty';
        emptyMsg.textContent = 'No comments yet. Start the conversation.';
        container.appendChild(emptyMsg);
        
        renderCommentForm(articleId, containerId, currentUser, articleSlug);
        return;
    }

    // ✅ SECURITY FIX: Build comments using secure DOM element creation instead of .map().join('')
    comments.forEach((comment) => {
        const commentUser = comment.user_detail || {};
        const isOwner = currentUser && commentUser.id === currentUser.id;

        const articleEl = document.createElement('article');
        articleEl.className = 'comment-card';

        // 1. Header
        const headerEl = document.createElement('div');
        headerEl.className = 'comment-card-header';

        const authorInfoDiv = document.createElement('div');
        const authorStrong = document.createElement('strong');
        authorStrong.className = 'comment-author';
        authorStrong.textContent = commentUser.name || 'Anonymous';

        const authorRoleSpan = document.createElement('span');
        authorRoleSpan.className = 'comment-author-role';
        authorRoleSpan.textContent = commentUser.role || 'Reader';

        authorInfoDiv.appendChild(authorStrong);
        authorInfoDiv.appendChild(authorRoleSpan);

        const timeEl = document.createElement('time');
        timeEl.className = 'comment-date';
        timeEl.setAttribute('datetime', comment.created_at);
        timeEl.textContent = formatCommentDate(comment.created_at);

        headerEl.appendChild(authorInfoDiv);
        headerEl.appendChild(timeEl);

        // 2. Text Content
        const textEl = document.createElement('p');
        textEl.className = 'comment-text';
        textEl.textContent = comment.text;

        // 3. Actions
        const actionsEl = document.createElement('div');
        actionsEl.className = 'comment-actions';

        if (isOwner) {
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'comment-action-btn';
            deleteBtn.dataset.deleteComment = comment.id;
            deleteBtn.textContent = 'Delete';

            deleteBtn.addEventListener('click', () => {
                showCustomConfirm('Delete this comment permanently?', async () => {
                    try {
                        await deleteComment(deleteBtn.dataset.deleteComment);
                        showCommentFeedback('Comment deleted successfully.');
                        await renderComments(articleId, containerId, articleSlug);
                    } catch (error) {
                        showCommentFeedback(error.message, 'error');
                    }
                });
            });

            actionsEl.appendChild(deleteBtn);
        } else if (currentUser) {
            const reportBtn = document.createElement('button');
            reportBtn.type = 'button';
            reportBtn.className = 'comment-action-btn';
            reportBtn.dataset.reportComment = comment.id;
            reportBtn.textContent = 'Report Flag';

            reportBtn.addEventListener('click', () => {
                // Ensure showReportModal triggers properly
                if (typeof showReportModal === 'function') {
                    showReportModal(reportBtn.dataset.reportComment);
                }
            });

            actionsEl.appendChild(reportBtn);
        }

        // Assemble article
        articleEl.appendChild(headerEl);
        articleEl.appendChild(textEl);
        articleEl.appendChild(actionsEl);

        // Add to container
        container.appendChild(articleEl);
    });

    renderCommentForm(articleId, containerId, currentUser, articleSlug);
}

window.renderComments = renderComments;