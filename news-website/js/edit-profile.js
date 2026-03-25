const PROFILE_API_URL = `${CONFIG.API_BASE_URL}/users/profile/`;

document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser(); // Using function from auth.js
    const token = localStorage.getItem('newsHub_accessToken');
    
    // Agar user logged in nahi hai ya token nahi hai
    if (!user || !token) {
        window.location.href = 'login.html?redirect=edit-profile.html';
        return;
    }

    // Populate current data in the form fields
    document.getElementById('edit-name').value = user.name || '';
    document.getElementById('edit-email').value = user.email || '';
    
    const bioElement = document.getElementById('edit-bio');
    if (bioElement) {
        bioElement.value = user.bio || '';
    }

    // === NAYA CODE: Profile Picture Preview Set Karna ===
    const previewImg = document.getElementById('profile-pic-preview');
    if (previewImg) {
        previewImg.src = window.getFullImageUrl(user.profile_picture, 'images/default-avatar.png');
    }

    const profilePicInput = document.getElementById('edit-profile-pic');
    
    // Jab user naya image select kare toh turant usko preview mein dikhayein (bina save kiye)
    if (profilePicInput && previewImg) {
        profilePicInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        });
    }
    // ======================================================

    const form = document.getElementById('edit-profile-form');
    const successDiv = document.getElementById('edit-success');
    const errorDiv = document.getElementById('edit-error');
    const submitBtn = form.querySelector('.auth-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const newName = document.getElementById('edit-name').value.trim();
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;
        
        let newBio = '';
        if (bioElement) {
            newBio = bioElement.value.trim();
        }

        errorDiv.style.display = 'none';
        successDiv.style.display = 'none';

        if (newPassword && newPassword !== confirmNewPassword) {
            errorDiv.textContent = 'New passwords do not match.';
            errorDiv.style.display = 'block';
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        // === NAYA CODE: FormData use karna (kyunki ab humein image file bhejni hai) ===
        const formData = new FormData();
        formData.append('name', newName);
        formData.append('bio', newBio);
        
        if (newPassword) {
            formData.append('password', newPassword); 
        }

        // Agar user ne nayi file select ki hai, toh usko append karein
        if (profilePicInput && profilePicInput.files.length > 0) {
            formData.append('profile_picture', profilePicInput.files[0]);
        }
        // ===============================================================================

        try {
            const response = await fetch(PROFILE_API_URL, {
                method: 'PATCH',
                headers: {
                    // DHYAN DEIN: Yahan 'Content-Type' nahi likhna hai. 
                    // Browser khud 'multipart/form-data' set karega file upload ke liye.
                    'Authorization': `Bearer ${token}`
                },
                body: formData // Payload ki jagah formData bhej rahe hain
            });

            if (response.ok) {
                const updatedUser = await response.json();
                
                // Update current session data in localStorage
                localStorage.setItem('newsHub_currentUser', JSON.stringify(updatedUser));
                
                // Header UI me naam update karne ke liye
                if (typeof updateAuthUI === 'function') updateAuthUI();

                // Purana success text hide kar diya, ab beautiful toast chalega
                if (typeof showToast === 'function') {
                    showToast('Profile updated successfully! Redirecting...', 'success');
                } else {
                    successDiv.textContent = 'Profile updated successfully!';
                    successDiv.style.display = 'block';
                }
                
                document.getElementById('new-password').value = '';
                document.getElementById('confirm-new-password').value = '';

                // NAYA: 2 second (2000 ms) ke baad profile.html par auto-redirect karein
                setTimeout(() => {
                    window.location.href = 'profile.html';
                }, 2000);
                
            } else {
                const errorData = await response.json();
                let errMsg = 'An error occurred while saving.';
                
                if (typeof errorData === 'object' && errorData !== null) {
                    const firstKey = Object.keys(errorData)[0];
                    if (firstKey) {
                        errMsg = `${firstKey}: ${errorData[firstKey]}`;
                    }
                }
                
                errorDiv.textContent = errMsg;
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            console.error("Profile update error:", error);
            errorDiv.textContent = 'Network error. Please try again.';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Save Changes';
        }
    });
});