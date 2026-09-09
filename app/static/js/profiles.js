async function loadProfiles() {
    const response = await fetch('/api/candidates');
    if (!response.ok) throw new Error('Could not load profiles');
    const profiles = await response.json();
    const list = document.getElementById('profiles');
    list.replaceChildren();
    for (const profile of profiles) {
        const card = document.createElement('div');
        card.className = 'card'; card.style.padding = '20px';
        const link = document.createElement('a');
        link.href = `/profiles/${profile.candidate_id}/`;
        link.textContent = profile.display_name;
        const actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:8px;margin-top:12px';
        for (const [label, action] of [['Rename', 'rename'], ['Delete profile', 'delete']]) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = action === 'delete' ? 'btn btn-danger' : 'btn btn-secondary';
            button.textContent = label;
            button.setAttribute('aria-label', `${label}: ${profile.display_name}`);
            button.addEventListener('click', () => manageProfile(profile, action, button));
            actions.append(button);
        }
        card.append(link, actions);
        list.append(card);
    }
    if (!profiles.length) list.textContent = 'No profiles yet.';
}

async function manageProfile(profile, action, button) {
    const deleting = action === 'delete';
    const value = window.prompt(deleting
        ? `Permanently delete "${profile.display_name}" and its resume, settings, jobs, applications, and browser data? Backups stored outside the profile are retained. Type the exact profile name to confirm:`
        : 'New profile name:', deleting ? '' : profile.display_name);
    if (value === null) return;
    const error = document.getElementById('profile-error');
    error.textContent = '';
    if (deleting && value !== profile.display_name) {
        error.textContent = 'Profile name did not match. Nothing was deleted.';
        return;
    }
    if (!deleting && (!value.trim() || value.trim().length > 120)) {
        error.textContent = 'Display name must contain 1 to 120 characters';
        return;
    }
    button.disabled = true;
    try {
        const response = await fetch(`/api/candidates/${profile.candidate_id}`, {
            method: deleting ? 'DELETE' : 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(deleting ? { confirm_name: value } : { display_name: value.trim() })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not update profile');
        document.getElementById('profile-created').textContent = deleting ? 'Profile deleted.' : 'Profile renamed.';
        await loadProfiles();
    } catch (cause) { error.textContent = cause.message; }
    finally { button.disabled = false; }
}
document.getElementById('create-profile').addEventListener('submit', async event => {
    event.preventDefault();
    const button = event.target.querySelector('button[type="submit"]'); button.disabled = true;
    const cancel = event.target.querySelector('button[type="reset"]'); cancel.disabled = true;
    document.getElementById('profile-error').textContent = '';
    document.getElementById('profile-created').replaceChildren();
    try {
        const response = await fetch('/api/candidates', { method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ display_name: document.getElementById('display-name').value }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not create profile');
        event.target.reset();
        const status = document.getElementById('profile-created');
        const setup = document.createElement('a');
        setup.href = `/profiles/${data.candidate_id}/#/settings`;
        setup.textContent = 'Set up profile';
        status.append(document.createTextNode(`${data.display_name} created. `), setup);
        await loadProfiles();
    } catch (error) { document.getElementById('profile-error').textContent = error.message; }
    finally { button.disabled = false; cancel.disabled = false; }
});
document.getElementById('create-profile').addEventListener('reset', () => {
    document.getElementById('profile-error').textContent = '';
    document.getElementById('profile-created').replaceChildren();
});
loadProfiles().catch(error => { document.getElementById('profile-error').textContent = error.message; });
