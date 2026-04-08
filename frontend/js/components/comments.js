const COMMENTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/comments/`;
const COMMENT_REPORTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/reports/comments/`;

async function fetchComments(articleId) {
    try {
        const response = await fetch(`${COMMENTS_API_URL}?article_id=${articleId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch comments.');
        }

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
    if (!getCurrentUser()) {
        throw new Error('You must be logged in to comment.');
    }

    const response = await apiFetch(COMMENTS_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            article: articleId,
            text
        })
    }, { authRequired: true });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || 'Failed to post comment. Please try again.');
    }

    return data;
}

async function deleteComment(commentId) {
    if (!getCurrentUser()) {
        throw new Error('You must be logged in.');
    }

    const response = await apiFetch(`${COMMENTS_API_URL}${commentId}/`, {
        method: 'DELETE'
    }, { authRequired: true });

    if (!response.ok) {
        throw new Error('Failed to delete comment.');
    }

    return true;
}

async function reportComment(commentId, reason, description) {
    if (!getCurrentUser()) {
        throw new Error('You must be logged in to report comments.');
    }

    const response = await apiFetch(COMMENT_REPORTS_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            comment: commentId,
            reason,
            description
        })
    }, { authRequired: true });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const errorMessage = data.detail || data.comment || data.non_field_errors || 'Failed to report comment.';
        throw new Error(Array.isArray(errorMessage) ? errorMessage[0] : errorMessage);
    }

    return data;
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatCommentDate(isoString) {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
        return 'Just now';
    }

    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
    });
}

function getCommentFeedbackElement() {
    return document.getElementById('comment-feedback') || document.getElementById('comment-feedback-toast');
}

function showCommentFeedback(message, type = 'success') {
    const feedback = getCommentFeedbackElement();
    if (!feedback) {
        return;
    }

    feedback.textContent = message;
    const baseClass = feedback.id === 'comment-feedback-toast'
        ? 'comment-feedback comment-feedback-toast'
        : 'comment-feedback';
    feedback.className = `${baseClass} comment-feedback-${type}`;
    feedback.style.display = 'block';

    window.clearTimeout(showCommentFeedback.timeoutId);
    showCommentFeedback.timeoutId = window.setTimeout(() => {
        feedback.style.display = 'none';
    }, 4000);
}

function showCustomConfirm(message, onConfirmCallback) {
    const existingOverlay = document.getElementById('custom-confirm-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    const overlay = document.createElement('div');
    overlay.id = 'custom-confirm-overlay';
    overlay.className = 'custom-modal-overlay';
    overlay.innerHTML = `
        <div class="custom-modal-box">
            <h3>Delete Comment</h3>
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

function buildReportModal() {
    const template = document.getElementById('report-comment-modal-template');
    const overlay = document.createElement('div');
    overlay.id = 'report-comment-overlay';
    overlay.className = 'custom-modal-overlay';

    if (template) {
        overlay.appendChild(template.content.cloneNode(true));
    } else {
        overlay.innerHTML = `
            <div class="custom-modal-box report-modal-box">
                <h3>Report Flag</h3>
                <p class="report-modal-copy">Flag comments that are spam, abusive, or misleading. Our moderation team will review them.</p>
            </div>
        `;
    }

    return overlay;
}

function renderCommentForm(articleId, containerId, user, articleSlug) {
    const formContainer = document.getElementById('comment-form-container');
    if (!formContainer) {
        return;
    }

    if (!user) {
        formContainer.innerHTML = `
            <p class="login-prompt">
                <a href="/login?redirect=/article/${articleSlug}">Log in</a> to post a comment or flag one for review.
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

        if (!text) {
            showCommentFeedback('Please write a comment before posting.', 'error');
            return;
        }

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
    if (!container) {
        return;
    }

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
        const authorName = escapeHtml(commentUser.name || 'Anonymous');
        const authorRole = escapeHtml(commentUser.role || 'Reader');
        const commentText = escapeHtml(comment.text);
        const createdAt = formatCommentDate(comment.created_at);
        const deleteButton = isOwner
            ? `<button type="button" class="comment-action-btn" data-delete-comment="${comment.id}">Delete</button>`
            : '';
        const reportButton = currentUser && !isOwner
            ? `<button type="button" class="comment-action-btn" data-report-comment="${comment.id}">Report Flag</button>`
            : '';

        return `
            <article class="comment-card">
                <div class="comment-card-header">
                    <div>
                        <strong class="comment-author">${authorName}</strong>
                        <span class="comment-author-role">${authorRole}</span>
                    </div>
                    <time class="comment-date" datetime="${escapeHtml(comment.created_at)}">${createdAt}</time>
                </div>
                <p class="comment-text">${commentText}</p>
                <div class="comment-actions">
                    ${deleteButton}
                    ${reportButton}
                </div>
            </article>
        `;
    }).join('');

    container.querySelectorAll('[data-delete-comment]').forEach((button) => {
        button.addEventListener('click', () => {
            showCustomConfirm('Delete this comment permanently?', async () => {
                try {
                    await deleteComment(button.dataset.deleteComment);
                    showCommentFeedback('Comment deleted successfully.');
                    await renderComments(articleId, containerId, articleSlug);
                } catch (error) {
                    showCommentFeedback(error.message, 'error');
                }
            });
        });
    });

    container.querySelectorAll('[data-report-comment]').forEach((button) => {
        button.addEventListener('click', () => {
            showReportModal(button.dataset.reportComment);
        });
    });

    renderCommentForm(articleId, containerId, currentUser, articleSlug);
}

window.renderComments = renderComments;
