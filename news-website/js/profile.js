// js/profile.js
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser(); // Gets user from auth.js local storage
    const profileContent = document.getElementById('profile-content');

    if (!user) {
        // Not logged in, redirect to login
        window.location.href = 'login.html?redirect=profile.html';
        return;
    }

    // Display user info using Django backend fields
    const joinDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown Date';
    const profilePic = user.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=100&q=80';

    profileContent.innerHTML = `
        <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
            <img src="${profilePic}" alt="Profile Picture" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid var(--primary);">
            <div>
                <h2 style="margin-bottom: 5px;">${user.name}</h2>
                <p style="color: var(--gray);">${user.email}</p>
            </div>
        </div>
        <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <p><strong>Bio:</strong> ${user.bio || 'No bio added yet.'}</p>
            <p style="margin-top: 10px;"><strong>Member since:</strong> ${joinDate}</p>
        </div>
        <div style="display: flex; gap: 15px;">
            <a href="edit-profile.html" class="auth-btn" style="text-decoration: none; text-align: center; padding: 10px 20px;">Edit Profile</a>
            <a href="index.html" class="auth-btn" style="background-color: var(--gray); text-decoration: none; text-align: center; padding: 10px 20px;">Back to Home</a>
        </div>
    `;
});