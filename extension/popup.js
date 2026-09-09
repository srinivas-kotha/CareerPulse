const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const fillBtn = document.getElementById('fillBtn');
const serverUrlInput = document.getElementById('serverUrl');
const saveUrlBtn = document.getElementById('saveUrlBtn');
const settingsLink = document.getElementById('settingsLink');

let isConnected = false;

async function init() {
  const { serverUrl } = await chrome.storage.local.get({ serverUrl: 'http://localhost:8085' });
  serverUrlInput.value = serverUrl;
  const { pairing } = await chrome.storage.local.get('pairing');
  if (pairing) {
    serverUrlInput.value = pairing.serverUrl;
    serverUrlInput.disabled = true;
    saveUrlBtn.disabled = true;
    const label = document.getElementById('pairedCandidate');
    if (label) label.textContent = `Paired with ${pairing.displayName}. Use another Chrome profile for another candidate.`;
    const pairButton = document.getElementById('pairBrowserBtn');
    if (pairButton) pairButton.disabled = true;
  }
  settingsLink.href = `${serverUrl}/#/settings`;
  await checkConnection();
}

async function checkConnection() {
  statusDot.className = 'status-dot';
  statusText.textContent = 'Checking...';
  fillBtn.disabled = true;

  try {
    const response = await chrome.runtime.sendMessage({ type: 'checkConnection' });
    if (response && response.ok) {
      statusDot.classList.add('connected');
      statusText.textContent = response.candidateName ? `Connected: ${response.candidateName}` : 'Connected to CareerPulse';
      fillBtn.disabled = false;
      isConnected = true;
    } else {
      statusDot.classList.add('disconnected');
      statusText.textContent = response?.error || 'Cannot reach server';
      isConnected = false;
    }
  } catch (err) {
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Extension error';
    isConnected = false;
  }
}

fillBtn.addEventListener('click', async () => {
  if (!isConnected) return;

  fillBtn.disabled = true;
  fillBtn.textContent = 'Filling...';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error('No active tab');
    await chrome.tabs.sendMessage(tab.id, { type: 'startFill' });
    window.close();
  } catch (err) {
    console.error('Fill error:', err);
    fillBtn.textContent = 'Fill Application';
    fillBtn.disabled = false;
    statusText.textContent = 'Refresh the page and try again';
    statusDot.className = 'status-dot disconnected';
  }
});

saveUrlBtn.addEventListener('click', async () => {
  let url = serverUrlInput.value.trim().replace(/\/+$/, '');
  if (!url) return;
  if (!/^https?:\/\//i.test(url)) {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'URL must start with http:// or https://';
    return;
  }
  const { pairing } = await chrome.storage.local.get('pairing');
  if (pairing) { statusText.textContent = 'This browser is already paired'; return; }
  await chrome.storage.local.set({ serverUrl: url });
  settingsLink.href = `${url}/#/settings`;
  await checkConnection();
});

settingsLink.addEventListener('click', async (e) => {
  e.preventDefault();
  const { serverUrl } = await chrome.storage.local.get({ serverUrl: 'http://localhost:8085' });
  const { pairing } = await chrome.storage.local.get('pairing');
  const url = pairing ? `${pairing.serverUrl}/profiles/${pairing.candidateId}/#/settings` : `${serverUrl}/#/settings`;
  chrome.tabs.create({ url });
});

init();

let pairingInProgress = false;
document.getElementById('pairBrowserBtn')?.addEventListener('click', async () => {
  if (pairingInProgress) return;
  pairingInProgress = true;
  try {
    const { pairing: existing } = await chrome.storage.local.get('pairing');
    if (existing) throw new Error('Already paired. Use a separate Chrome profile for another candidate.');
    const pairing = JSON.parse(document.getElementById('pairingCode').value);
    const url = new URL(pairing.serverUrl);
    if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) || url.port !== '8085' || url.username || url.password) {
      throw new Error('Pairing requires the local CareerPulse server on port 8085');
    }
    if (!/^[0-9a-f-]{36}$/.test(pairing.candidateId) || typeof pairing.token !== 'string' || pairing.token.length < 32) throw new Error('Invalid pairing code');
    pairing.serverUrl = url.origin;
    const response = await fetch(`${url.origin}/api/candidates/${pairing.candidateId}/health`, {
      headers: { 'X-CareerPulse-Pairing': pairing.token },
    });
    if (!response.ok) throw new Error('Pairing rejected by server');
    await chrome.storage.local.set({ pairing, serverUrl: url.origin });
    await init();
  } catch (error) { statusText.textContent = error.message; }
  finally { pairingInProgress = false; }
});
