// js/comments.js
// ==================== COMMENTS MODULE ====================
// Depends on auth.js (getCurrentUser)

// Real Django backend endpoint for comments
const COMMENTS_API_URL = `${CONFIG.API_BASE_URL}/interactions/comments/`;

// Fetch comments for an article
async function fetchComments(articleId) {
    try {
        const response = await fetch(`${COMMENTS_API_URL}?article_id=${articleId}`);
        if (!response.ok) throw new Error('Failed to fetch comments');
        
        const data = await response.json();
        // Return results array if paginated, otherwise the whole data array
        return data.results || data;
    } catch (error) {
        console.error('Error fetching comments:', error);
        return [];
    }
}

// Post a new comment
async function postComment(articleId, text) {
    const token = localStorage.getItem('newsHub_accessToken');
    if (!token) throw new Error('You must be logged in to comment.');

    const response = await fetch(COMMENTS_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            article: articleId,
            text: text
        })
    });

    if (!response.ok) {
        throw new Error('Failed to post comment. Please try again.');
    }
    
    return await response.json();
}

// Delete a comment
async function deleteComment(commentId) {
    const token = localStorage.getItem('newsHub_accessToken');
    if (!token) throw new Error('You must be logged in.');

    const response = await fetch(`${COMMENTS_API_URL}${commentId}/`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!response.ok) {
        throw new Error('Failed to delete comment.');
    }
    return true;
}

// ==================== Custom Delete Confirmation Popup ====================
function showCustomConfirm(message, onConfirmCallback) {
    // Agar pehle se popup bana hua hai toh use nikal do
    let existingOverlay = document.getElementById('custom-confirm-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    // Naya popup HTML create karein
    const overlay = document.createElement('div');
    overlay.id = 'custom-confirm-overlay';
    overlay.className = 'custom-modal-overlay';
    
    overlay.innerHTML = `
        <div class="custom-modal-box">
            <h3>Delete Comment</h3>
            <p>${message}</p>
            <div class="custom-modal-actions">
                <button class="custom-modal-btn custom-modal-cancel" id="custom-modal-cancel-btn">Cancel</button>
                <button class="custom-modal-btn custom-modal-delete" id="custom-modal-delete-btn">Delete</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);

    // Cancel Button logic
    document.getElementById('custom-modal-cancel-btn').addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300); // Animation ke baad remove
    });

    // Delete Button logic
    document.getElementById('custom-modal-delete-btn').addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300);
        onConfirmCallback(); // Delete action perform karein
    });

    // Thoda sa delay dekar animation trigger karein
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

// Render comments list and form
async function renderComments(articleId, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const user = getCurrentUser();
    const comments = await fetchComments(articleId);

    if (comments.length === 0) {
        container.innerHTML = '<p class="no-comments">No comments yet. Be the first to comment!</p>';
    } else {
        let html = '';
        comments.forEach(c => {
            const authorId = c.user_detail ? c.user_detail.id : null;
            const authorName = c.user_detail ? c.user_detail.name : 'Unknown User';
            const isAuthor = user && authorId === user.id;
            
            html += `
                <div class="comment" data-comment-id="${c.id}">
                    <div class="comment-header">
                        <span class="comment-author">${authorName}</span>
                        <span class="comment-date">${new Date(c.created_at).toLocaleString()}</span>
                    </div>
                    <div class="comment-text">${c.text}</div>
                    ${isAuthor ? `
                        <div class="comment-actions">
                            <button class="delete-comment" data-comment-id="${c.id}">Delete</button>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        container.innerHTML = html;

        // Attach delete handlers with Custom Modal
        container.querySelectorAll('.delete-comment').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.dataset.commentId;
                
                // Puraana confirm box hata kar naya wala use kiya
                showCustomConfirm("Are you sure you want to delete this comment? This action cannot be undone.", async () => {
                    try {
                        // Jab tak delete ho raha hai button text change kar do
                        e.target.textContent = 'Deleting...';
                        await deleteComment(commentId);
                        await renderComments(articleId, containerId); // Refresh comments after deleting
                    } catch (err) {
                        alert(err.message);
                    }
                });
            });
        });
    }

    // Render comment form or login prompt
    const formContainer = document.getElementById('comment-form-container');
    if (user) {
        formContainer.innerHTML = `
            <div class="comment-form">
                <h4>Add a Comment</h4>
                <textarea id="new-comment-text" rows="3" placeholder="Write your comment..."></textarea>
                <button id="submit-comment">Post Comment</button>
            </div>
        `;
        document.getElementById('submit-comment').addEventListener('click', async () => {
            const text = document.getElementById('new-comment-text').value.trim();
            if (!text) return;
            
            const btn = document.getElementById('submit-comment');
            btn.disabled = true;
            btn.textContent = 'Posting...';
            
            try {
                await postComment(articleId, text);
                document.getElementById('new-comment-text').value = '';
                await renderComments(articleId, containerId); // Refresh comments after posting
            } catch (err) {
                alert(err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Post Comment';
            }
        });
    } else {
        formContainer.innerHTML = `
            <p class="login-prompt">
                <a href="login.html?redirect=article.html?id=${articleId}">Log in</a> to post a comment.
            </p>
        `;
    }
}