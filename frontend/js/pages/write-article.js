// js/pages/write-article.js

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Auth Check - Only allow roles author, reporter, editor, admin
    const user = getCurrentUser();
    const formContainer = document.querySelector('.writer-container');

    // Allow if user is staff/author OR if explicitly approved as an activist
    const hasAccess = user && (['author', 'reporter', 'editor', 'admin'].includes(user.role) || user.is_activist_approved === true);

    if (!hasAccess) {
        formContainer.innerHTML = `
            <div style="text-align: center; padding: 40px 20px;">
                <i class="fas fa-lock" style="font-size: 3rem; color: #cbd5e1; margin-bottom: 20px;"></i>
                <h1 style="color: #1e293b;">Verified Writers Only</h1>
                <p style="color: #64748b; margin-bottom: 25px;">You must be approved by the Ferox Times editorial team to submit articles.</p>
                <a href="/profile.html" class="btn-submit" style="background: #10b981; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; width: auto;">
                    Apply to Become a Writer
                </a>
            </div>
        `;
        return;
    }

    // 2. Initialize Quill Rich Text Editor
    const quill = new Quill('#editor-container', {
        theme: 'snow',
        placeholder: 'Write your article here...',
        modules: {
            toolbar: [
                [{ 'header': [2, 3, false] }],
                ['bold', 'italic', 'underline', 'strike'],
                ['blockquote'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                [{ 'indent': '-1'}, { 'indent': '+1' }],
                ['link'],
                ['clean']
            ]
        }
    });

    // 3. Load Categories
    const categorySelect = document.getElementById('article-category');
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/news/categories/`);
        if (response.ok) {
            const data = await response.json();
            const categories = data.results || data;
            
            let optionsHtml = '<option value="">-- Select Category --</option>';
            categories.forEach(cat => {
                optionsHtml += `<option value="${cat.id}">${cat.name}</option>`;
            });
            categorySelect.innerHTML = optionsHtml;
        }
    } catch (err) {
        console.error("Failed to load categories:", err);
    }

    // 4. Handle Form Submission
    const form = document.getElementById('article-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusMsg = document.getElementById('status-message');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const title = document.getElementById('article-title').value.trim();
        const categoryId = categorySelect.value;
        const htmlContent = quill.root.innerHTML;
        const textContent = quill.getText().trim();

        // Basic validation
        if (title.length < 5) {
            showError('Title is too short. Needs to be at least 5 characters.');
            return;
        }
        if (textContent.length < 50) {
            showError('Article content is too short. Please write at least 50 characters.');
            return;
        }

        // Submitting
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        
        try {
            // Because authors create articles, sending a bare minimum payload.
            // Backend `perform_create` will set author, status="draft", etc.
            const payload = {
                title: title,
                description: textContent.substring(0, 150) + "...", // Fallback description
                content: htmlContent,
                category_id: parseInt(categoryId),
                status: 'draft', 
                source_name: 'Guest Writer',
                is_imported: false
            };

            const response = await apiFetch(`${CONFIG.API_BASE_URL}/news/articles/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                showSuccess('✅ Article Submitted Successfully! Our editors will review it shortly. Redirecting...');
                quill.root.innerHTML = '';
                form.reset();
                setTimeout(() => {
                    window.location.href = '/profile.html';
                }, 3000);
            } else {
                const data = await response.json().catch(()=>({}));
                let errorText = 'Submission failed.';
                if(data.title) errorText += ` Title: ${data.title.join(', ')}`;
                if(data.description) errorText += ` Description: ${data.description.join(', ')}`;
                if(data.detail) errorText += ` ${data.detail}`;
                showError(errorText);
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right: 8px;"></i> Submit for Editorial Review';
            }

        } catch (error) {
            console.error('Submit Error:', error);
            showError('A network error occurred. Please try again.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane" style="margin-right: 8px;"></i> Submit for Editorial Review';
        }
    });

    function showError(msg) {
        statusMsg.style.display = 'block';
        statusMsg.style.backgroundColor = '#fee2e2';
        statusMsg.style.color = '#b91c1c';
        statusMsg.style.border = '1px solid #fecaca';
        statusMsg.innerText = '❌ ' + msg;
    }

    function showSuccess(msg) {
        statusMsg.style.display = 'block';
        statusMsg.style.backgroundColor = '#d1fae5';
        statusMsg.style.color = '#065f46';
        statusMsg.style.border = '1px solid #a7f3d0';
        statusMsg.innerText = msg;
    }
});
