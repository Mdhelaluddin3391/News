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

// Delete a comment (Backend checks if user is authorized/admin, but we show the button only for the author)
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
            // Django backend serializer mein user detail 'user_detail' object ke andar aati hai
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

        // Attach delete handlers
        container.querySelectorAll('.delete-comment').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const commentId = e.target.dataset.commentId;
                if (!confirm("Are you sure you want to delete this comment?")) return;
                
                try {
                    await deleteComment(commentId);
                    await renderComments(articleId, containerId); // Refresh comments after deleting
                } catch (err) {
                    alert(err.message);
                }
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