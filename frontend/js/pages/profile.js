// js/profile.js
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser(); // Gets user from auth.js local storage
    const profileContent = document.getElementById('profile-content');

    if (!user) {
        // ✅ ROUTING FIX: Use clean URL for redirect
        window.location.href = "/login?redirect=/profile";
        return;
    }

    // Display user info using Django backend fields
    const joinDate = user.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'Unknown Date';
    
    // NAYA CODE: Global helper function for profile picture URL - NAYA UPDATE: added slash /
    const profilePic = window.getFullImageUrl(user.profile_picture, '/images/default-avatar.png');
    const containClass = profilePic.includes('default-avatar.png') ? 'img-contain' : '';

    // ✅ SEO FIX: Use clean URLs for edit-profile and home buttons
    profileContent.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; text-align: center; margin-bottom: 30px;">
            <div style="position: relative; margin-bottom: 15px;">
                <img src="${profilePic}" alt="Profile Picture" class="${containClass}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid var(--primary); box-shadow: 0 4px 10px rgba(0,0,0,0.1);" onerror="this.onerror=null; this.src='/images/default-news.png'; this.classList.add('img-contain');">
            </div>
            <h2 style="font-size: 2rem; color: var(--dark); margin-bottom: 5px;">${user.name}</h2>
            <p style="color: var(--gray); font-size: 1.1rem; background: var(--accent); padding: 5px 15px; border-radius: 20px; display: inline-block;">${user.email}</p>
        </div>
        
        <div style="background: #f8fafc; padding: 25px; border-radius: 12px; margin-bottom: 30px; border-left: 5px solid var(--primary); box-shadow: var(--shadow);">
            <h3 style="margin-bottom: 10px; font-size: 1.2rem; color: var(--dark);">About Me</h3>
            <p style="color: #475569; font-size: 1.05rem; line-height: 1.6;">${user.bio ? user.bio : '<span style="font-style: italic; color: var(--gray);">No bio added yet. Tell us about yourself!</span>'}</p>
            <div style="margin-top: 15px; font-size: 0.9rem; color: var(--gray);">
                <i class="far fa-calendar-alt"></i> <strong>Member since:</strong> ${joinDate}
            </div>
        </div>
        
        <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
            <a href="/edit-profile" style="background-color: var(--primary); color: white; text-decoration: none; padding: 12px 30px; border-radius: 30px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); min-width: 160px; text-align: center;">
                <i class="fas fa-user-edit" style="margin-right: 8px;"></i> Edit Profile
            </a>
            ${(['author', 'reporter', 'editor', 'admin'].includes(user.role) || String(user.is_activist_approved) === 'true') ? `
            <a href="/write-article" style="background-color: #10b981; color: white; text-decoration: none; padding: 12px 30px; border-radius: 30px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); min-width: 160px; text-align: center;">
                <i class="fas fa-pen-nib" style="margin-right: 8px;"></i> Write Raw Article
            </a>
            ` : `
            <a href="/careers" style="background-color: #f59e0b; color: white; text-decoration: none; padding: 12px 30px; border-radius: 30px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); min-width: 160px; text-align: center;">
                <i class="fas fa-certificate" style="margin-right: 8px;"></i> Apply for Verification
            </a>
            `}
            <a href="/" style="background-color: transparent; color: var(--primary); border: 2px solid var(--primary); text-decoration: none; padding: 10px 30px; border-radius: 30px; font-weight: 600; transition: all 0.3s ease; min-width: 160px; text-align: center;" 
               onmouseover="this.style.backgroundColor='var(--primary)'; this.style.color='white';" 
               onmouseout="this.style.backgroundColor='transparent'; this.style.color='var(--primary)';">
                <i class="fas fa-home" style="margin-right: 8px;"></i> Back to Home
            </a>
        </div>
    `;
});