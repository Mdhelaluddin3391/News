// js/edit-profile.js

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
    
    // Yaha Bio populate kiya jayega (Aapko HTML mein id="edit-bio" ka textarea add karna hoga)
    const bioElement = document.getElementById('edit-bio');
    if (bioElement) {
        bioElement.value = user.bio || '';
    }

    const form = document.getElementById('edit-profile-form');
    const successDiv = document.getElementById('edit-success');
    const errorDiv = document.getElementById('edit-error');
    const submitBtn = form.querySelector('.auth-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const newName = document.getElementById('edit-name').value.trim();
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;
        
        // Fetch new bio value
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

        // Backend pe bhejne ke liye payload prepare karein, bio ke saath
        const payload = { 
            name: newName,
            bio: newBio
        };
        
        // Agar naya password dala hai toh payload me include karein
        if (newPassword) {
            payload.password = newPassword; 
        }

        try {
            // Backend par PATCH request bhejna (sirf updated fields send karne ke liye)
            const response = await fetch(PROFILE_API_URL, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const updatedUser = await response.json();
                
                // Update current session data in localStorage
                localStorage.setItem('newsHub_currentUser', JSON.stringify(updatedUser));
                
                // Header UI me naam update karne ke liye
                if (typeof updateAuthUI === 'function') updateAuthUI();

                successDiv.textContent = 'Profile updated successfully!';
                successDiv.style.display = 'block';
                
                // Optional: Clear password fields after save
                document.getElementById('new-password').value = '';
                document.getElementById('confirm-new-password').value = '';
            } else {
                const errorData = await response.json();
                let errMsg = 'An error occurred while saving.';
                
                // Error array/object me se pehla message nikalna
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