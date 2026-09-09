async function loadProfiles() {
    const response = await fetch('/api/candidates');
    if (!response.ok) throw new Error('Could not load profiles');
    const profiles = await response.json();
    const list = document.getElementById('profiles');
    list.replaceChildren();
    for (const profile of profiles) {
        const link = document.createElement('a');
        link.className = 'card'; link.style.padding = '20px';
        link.href = `/profiles/${profile.candidate_id}/`;
        link.textContent = profile.display_name;
        list.append(link);
    }
    if (!profiles.length) list.textContent = 'No profiles yet.';
}
document.getElementById('create-profile').addEventListener('submit', async event => {
    event.preventDefault();
    const button = event.target.querySelector('button'); button.disabled = true;
    try {
        const response = await fetch('/api/candidates', { method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ display_name: document.getElementById('display-name').value }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not create profile');
        location.assign(`/profiles/${data.candidate_id}/#/settings`);
    } catch (error) { document.getElementById('profile-error').textContent = error.message; }
    finally { button.disabled = false; }
});
loadProfiles().catch(error => { document.getElementById('profile-error').textContent = error.message; });
