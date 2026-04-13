// js/pages/write-article.js

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Auth Check - Only allow roles author, reporter, editor, admin
    const user = getCurrentUser();
    const formContainer = document.querySelector('.writer-container');

    // Allow if user is staff/author OR if explicitly approved as an activist
    const hasAccess = user && (
        (user.role && ['author', 'reporter', 'editor', 'admin'].includes(user.role)) || 
        String(user.is_activist_approved) === 'true'
    );

    if (!hasAccess) {
        formContainer.innerHTML = `
            <div style="text-align: center; padding: 40px 20px;">
                <i class="fas fa-lock" style="font-size: 3rem; color: #cbd5e1; margin-bottom: 20px;"></i>
                <h1 style="color: #1e293b;">Verified Writers Only</h1>
                <p style="color: #64748b; margin-bottom: 25px;">You must be approved by the Ferox Times editorial team to submit articles.</p>
                <a href="/careers" class="btn-submit" style="background: #10b981; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; display: inline-block; width: auto;">
                    Apply to Become a Writer
                </a>
            </div>
        `;
        return;
    }

    // ── 2a. Load Categories FIRST (independent of Quill) ──
    // Pehle categories load karo — yeh Quill se bilkul alag hai
    // Taaki Quill ke crash hone par bhi categories kaam karti rahe
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
        } else {
            console.error('Categories API error:', response.status);
        }
    } catch (err) {
        console.error('Failed to load categories:', err);
    }

    // ── 2b. Initialize Quill Rich Text Editor ──
    // Quill CDN se load hoti hai — agar CSP ya network issue ho toh crash na ho
    // Isliye try-catch lagaya aur plain textarea fallback diya
    let quill = null;
    const editorContainer = document.getElementById('editor-container');

    if (typeof Quill !== 'undefined') {
        try {
            quill = new Quill('#editor-container', {
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
        } catch (quillErr) {
            console.warn('Quill init failed, using textarea fallback:', quillErr);
            quill = null;
        }
    } else {
        console.warn('Quill not loaded (CDN blocked?), using plain textarea fallback.');
    }

    // Agar Quill load nahi hua toh plain textarea show karo
    if (!quill) {
        editorContainer.innerHTML = '<textarea id="fallback-editor" style="width:100%; height:380px; padding:12px; border:1px solid #cbd5e1; border-radius:8px; font-size:1rem; box-sizing:border-box; resize:vertical;" placeholder="Write your article here..."></textarea>';
    }

    // Categories already loaded above (step 2a)

    // ── 2c. Document Upload UI Logic ──
    const docUploadArea = document.getElementById('doc-upload-area');
    const docInput = document.getElementById('supporting-doc');
    const docPreview = document.getElementById('doc-preview');
    const docFilename = document.getElementById('doc-filename');
    const docRemove = document.getElementById('doc-remove');

    // Click on upload area → open file picker
    docUploadArea.addEventListener('click', (e) => {
        if (e.target === docRemove || docRemove.contains(e.target)) return;
        docInput.click();
    });

    // Drag & Drop
    docUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        docUploadArea.style.borderColor = 'var(--primary)';
        docUploadArea.style.background = '#fff1f2';
    });
    docUploadArea.addEventListener('dragleave', () => {
        docUploadArea.style.borderColor = '#cbd5e1';
        docUploadArea.style.background = '#f8fafc';
    });
    docUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        docUploadArea.style.borderColor = '#cbd5e1';
        docUploadArea.style.background = '#f8fafc';
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    docInput.addEventListener('change', () => {
        if (docInput.files.length > 0) handleFileSelect(docInput.files[0]);
    });

    docRemove.addEventListener('click', () => {
        docInput.value = '';
        docPreview.style.display = 'none';
        docUploadArea.style.borderColor = '#cbd5e1';
        docUploadArea.style.background = '#f8fafc';
    });

    function handleFileSelect(file) {
        const maxSize = 20 * 1024 * 1024; // 20 MB
        const allowed = ['application/pdf','image/jpeg','image/png',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword','video/mp4','audio/mpeg','application/zip'];
        if (file.size > maxSize) {
            if (typeof showToast === 'function') showToast('File too large. Maximum allowed size is 20 MB.', 'error');
            return;
        }
        // Transfer to input
        const dt = new DataTransfer();
        dt.items.add(file);
        docInput.files = dt.files;
        // Show preview
        docFilename.textContent = '\uD83D\uDCC4 ' + file.name;
        docPreview.style.display = 'block';
        docUploadArea.style.borderColor = '#10b981';
        docUploadArea.style.background = '#f0fdf4';
    }

    // ── 4. Handle Form Submission ──
    const form = document.getElementById('article-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusMsg = document.getElementById('status-message');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const title = document.getElementById('article-title').value.trim();
        const categoryId = categorySelect.value;
        // Quill ya fallback textarea dono se content lo
        const htmlContent = quill ? quill.root.innerHTML : (document.getElementById('fallback-editor')?.value || '');
        const textContent = quill ? quill.getText().trim() : (document.getElementById('fallback-editor')?.value.trim() || '');
        const docFile = docInput.files[0];
        const guidelinesChecked = document.getElementById('guidelines-agree')?.checked;

        // Basic validation
        if (!guidelinesChecked) {
            showError('You must agree to the Editorial Guidelines before submitting.');
            return;
        }
        if (!categoryId) {
            showError('Please select a category for your article.');
            return;
        }
        if (title.length < 5) {
            showError('Title is too short. Needs to be at least 5 characters.');
            return;
        }
        if (textContent.length < 50) {
            showError('Article content is too short. Please write at least 50 characters.');
            return;
        }
        if (!docFile) {
            showError('Please upload a supporting evidence document. This is required for all submissions.');
            return;
        }

        // Submitting
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        
        try {
            // Use FormData for file upload support
            const formData = new FormData();
            formData.append('title', title);
            formData.append('description', textContent.substring(0, 150) + '...');
            formData.append('content', htmlContent);
            formData.append('category_id', parseInt(categoryId));
            formData.append('status', 'draft');
            formData.append('source_name', 'Guest Writer');
            formData.append('is_imported', 'false');
            if (docFile) {
                formData.append('supporting_document', docFile);
            }

            const response = await apiFetch(`${CONFIG.API_BASE_URL}/news/articles/`, {
                method: 'POST',
                // Content-Type header mat set karo — browser automatically multipart/form-data set karega
                body: formData
            });

            if (response.ok) {
                showSuccess('✅ Article Submitted Successfully! Our editors will review it shortly. Redirecting...');
                if (quill) quill.root.innerHTML = '';
                const fallbackEditor = document.getElementById('fallback-editor');
                if (fallbackEditor) fallbackEditor.value = '';
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
