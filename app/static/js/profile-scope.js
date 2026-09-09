// Identity is fixed by the page URL. Switching navigates to a fresh document.
function currentCandidateId() {
    return window.location.pathname.match(/^\/profiles\/([0-9a-f-]{36})\/$/)?.[1] || null;
}

function candidateUrl(path) {
    const id = currentCandidateId();
    return id && path.startsWith('/api/') && !path.startsWith('/api/candidates')
        ? `/api/candidates/${id}/${path.slice(5)}` : path;
}

const profileStorage = {
    key(key) { const id = currentCandidateId(); return id ? `candidate:${id}:${key}` : key; },
    getItem(key) { return localStorage.getItem(this.key(key)); },
    setItem(key, value) { return localStorage.setItem(this.key(key), value); },
    removeItem(key) { return localStorage.removeItem(this.key(key)); },
};

async function initializeProfileSelector() {
    const id = currentCandidateId();
    if (!id) return;
    const bar = document.createElement('div');
    bar.style.cssText = 'margin:64px auto 0;max-width:1200px;padding:12px 24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap';
    const label = document.createElement('label');
    label.textContent = 'Profile: ';
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Candidate profile');
    const res = await fetch('/api/candidates');
    if (!res.ok) throw new Error('Could not load profiles');
    const candidates = await res.json();
    for (const candidate of candidates) {
        const option = document.createElement('option');
        option.value = candidate.candidate_id;
        option.textContent = candidate.display_name;
        option.selected = candidate.candidate_id === id;
        select.append(option);
    }
    label.append(select);
    select.addEventListener('change', () => {
        window.location.assign(`/profiles/${select.value}/${window.location.hash}`);
    });
    const manage = document.createElement('a');
    manage.href = '/'; manage.textContent = 'Manage profiles';
    const pair = document.createElement('button');
    pair.textContent = 'Pair browser extension'; pair.className = 'btn btn-secondary btn-sm';
    pair.addEventListener('click', async () => {
        try {
            const response = await fetch(`/api/candidates/${id}/pairing`, { method: 'POST' });
            if (!response.ok) throw new Error('Pairing unavailable');
            const data = await response.json();
            const code = JSON.stringify({ serverUrl: location.origin, candidateId: id,
                displayName: data.display_name, token: data.token });
            window.prompt('In a dedicated Chrome profile for this candidate, open the extension and paste this pairing code. Verify the employer account before filling.', code);
        } catch (error) { window.alert(error.message); }
    });
    bar.append(label, manage, pair);
    document.querySelector('.navbar').after(bar);
    const main = document.querySelector('main.container');
    if (main) main.style.paddingTop = '24px';
}

document.addEventListener('DOMContentLoaded', () => {
    initializeProfileSelector().catch(error => {
        const message = document.createElement('p'); message.textContent = error.message;
        document.body.prepend(message);
    });
});
