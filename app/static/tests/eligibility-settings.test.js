import { beforeAll, beforeEach, it, expect, vi } from 'vitest';
import { loadScripts } from './setup.js';

beforeAll(() => loadScripts('utils.js', 'api.js', 'views/settings.js'));
beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>';
    globalThis.showToast = vi.fn();
});

it('saves only the selected profile rules and renders another profile without inherited values', async () => {
    let saved;
    vi.spyOn(api, 'request').mockImplementation(async (method, path, body) => {
        if (method === 'POST') saved = body;
        return { eligibility_policy: saved?.eligibility_policy || {} };
    });
    const container = document.getElementById('app');
    renderTabJobSearch(container, {}, { eligibility_policy: { annual_min: 100000, currency: 'USD', confirmed: true } }, []);
    document.getElementById('policy-annual').value = '120000';
    document.getElementById('policy-w2').value = '55.5';
    document.getElementById('save-policy-btn').click();
    await vi.waitFor(() => expect(showToast).toHaveBeenCalledWith('Eligibility rules saved for this profile', 'success'));
    expect(saved.eligibility_policy.annual_min).toBe(120000);
    expect(saved.eligibility_policy.w2_hourly_min).toBe(55.5);
    expect(saved.eligibility_policy.c2c_hourly_min).toBeNull();
    expect(Object.keys(saved)).toEqual(['eligibility_policy']);
    renderTabJobSearch(container, {}, {}, []);
    expect(document.getElementById('policy-annual').value).toBe('');
    expect(document.getElementById('policy-confirmed').checked).toBe(false);
});
