import { beforeAll, beforeEach, it, expect, vi } from 'vitest';
import { loadScripts } from './setup.js';

beforeAll(() => loadScripts('utils.js', 'api.js', 'views/pipeline.js'));
beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>';
    globalThis.showToast = vi.fn();
    globalThis.navigate = vi.fn();
});

function drag(card, zone) {
    const transfer = { setData: vi.fn() };
    for (const [target, type] of [[card, 'dragstart'], [zone, 'drop'], [card, 'dragend']]) {
        const event = new Event(type, { bubbles: true, cancelable: true });
        Object.defineProperty(event, 'dataTransfer', { value: transfer });
        target.dispatchEvent(event);
    }
}

it('waits for persistence and reloads column data after a move', async () => {
    let savedStatus = 'applied';
    let finishSave;
    vi.spyOn(api, 'request').mockImplementation(async (method, path) => {
        if (path === '/api/offers') return { offers: [] };
        const status = path.split('/').at(-1);
        const jobs = status === savedStatus ? [{ id: 9, title: 'Example', company: 'Example' }] : [];
        return { jobs, count: jobs.length };
    });
    vi.spyOn(api, 'updateApplication').mockImplementation(() => new Promise(resolve => {
        finishSave = () => { savedStatus = 'rejected'; resolve({ ok: true }); };
    }));
    const container = document.getElementById('app');
    await renderPipeline(container);
    drag(container.querySelector('.pipeline-card'), container.querySelector('.pipeline-cards[data-status="rejected"]'));
    expect(container.querySelector('.pipeline-cards[data-status="applied"] .pipeline-card')).not.toBeNull();
    expect(showToast).not.toHaveBeenCalled();
    finishSave();
    await vi.waitFor(() => expect(showToast).toHaveBeenCalledWith('Moved to Rejected', 'success'));
    // The board tab redraw uses captured results; those must now be refreshed.
    container.querySelector('[data-pipeline-tab="board"]').click();
    expect(container.querySelector('.pipeline-cards[data-status="applied"] .pipeline-card')).toBeNull();
    expect(container.querySelector('.pipeline-cards[data-status="rejected"] .pipeline-card')).not.toBeNull();
    await renderPipeline(container);
    expect(container.querySelector('.pipeline-cards[data-status="rejected"] .pipeline-card')).not.toBeNull();
});
