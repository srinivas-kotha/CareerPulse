import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import { loadScripts } from './setup.js';
beforeAll(() => { loadScripts('utils.js', 'onboarding.js'); });
beforeEach(() => {
    localStorage.clear();
    document.body.innerHTML = '<a class="nav-link" data-route="settings"></a>';
    globalThis.api = { request: vi.fn(async (_, url) => url === '/api/profile' ? {full_name:'Example',email:'example@test.com'} : {resumes:[{id:1}]}), getAISettings: vi.fn(async () => ({provider:'ollama'})) };
});
describe('saved setup on startup', () => {
    it('does not show welcome in a fresh browser when saved setup exists', async () => {
        await initializeOnboarding();
        expect(document.getElementById('onboarding-wizard')).toBeNull();
        expect(isOnboardingDone()).toBe(true);
    });
    it('does not treat an API failure as lost profile data', async () => {
        api.request.mockRejectedValue(new Error('offline'));
        await initializeOnboarding();
        expect(document.getElementById('onboarding-wizard')).toBeNull();
        expect(document.getElementById('setup-indicator')).toBeNull();
    });
    it('shows setup for a genuinely empty installation', async () => {
        api.request.mockResolvedValue({});
        await initializeOnboarding();
        expect(document.getElementById('onboarding-wizard')).not.toBeNull();
    });
});
