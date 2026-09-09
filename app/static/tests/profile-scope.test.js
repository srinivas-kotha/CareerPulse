import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import { loadScript } from './setup.js';

const first = '11111111-1111-4111-8111-111111111111';
const second = '22222222-2222-4222-8222-222222222222';
beforeAll(() => loadScript('api.js'));
beforeEach(() => { history.replaceState({}, '', '/'); localStorage.clear(); });

describe('candidate page identity', () => {
    it('scopes JSON requests, uploads and direct document/SSE URLs', async () => {
        history.replaceState({}, '', `/profiles/${first}/`);
        globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
        await api.getJob(1);
        expect(fetch.mock.calls[0][0]).toBe(`/api/candidates/${first}/jobs/1`);
        await api.uploadResume(new File(['resume'], 'resume.txt'));
        expect(fetch.mock.calls[1][0]).toBe(`/api/candidates/${first}/resume/upload`);
        expect(candidateUrl('/api/queue/events')).toBe(`/api/candidates/${first}/queue/events`);
        expect(candidateUrl('/api/jobs/1/resume.pdf')).toBe(`/api/candidates/${first}/jobs/1/resume.pdf`);
        expect(candidateUrl('/api/candidates')).toBe('/api/candidates');
    });
    it('keeps saved preferences separate for two candidate tabs', () => {
        history.replaceState({}, '', `/profiles/${first}/`);
        profileStorage.setItem('careerpulse_onboarded', 'true');
        profileStorage.setItem('filters', 'first');
        history.replaceState({}, '', `/profiles/${second}/`);
        expect(profileStorage.getItem('careerpulse_onboarded')).toBeNull();
        expect(profileStorage.getItem('filters')).toBeNull();
        profileStorage.setItem('filters', 'second');
        history.replaceState({}, '', `/profiles/${first}/`);
        expect(profileStorage.getItem('filters')).toBe('first');
    });
    it('renders candidate names as text and uses a full navigation switcher', async () => {
        history.replaceState({}, '', `/profiles/${first}/`);
        document.body.innerHTML = '<nav class="navbar"></nav>';
        globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [
            { candidate_id: first, display_name: '<img src=x onerror=alert(1)>' },
            { candidate_id: second, display_name: 'Second' },
        ] });
        await initializeProfileSelector();
        expect(document.querySelectorAll('option')).toHaveLength(2);
        expect(document.querySelector('select').value).toBe(first);
        expect(document.querySelector('img')).toBeNull();
        expect(document.querySelector('a').getAttribute('href')).toBe('/');
    });
});
