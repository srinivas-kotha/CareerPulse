import { beforeAll, describe, expect, it } from 'vitest';
import { loadScript } from './setup.js';
beforeAll(() => loadScript('views/stats.js'));
describe('scoring run outcome', () => {
    it('never presents failed or interrupted work as success', () => {
        for (const p of [
            {scored: 0, total: 600},
            {scored: 2, total: 5, failed: 3, status: 'stopped'},
            {scored: 2, total: 2, status: 'interrupted', stop_reason: 'Timed out'},
        ]) expect(scoringOutcome(p).type).toBe('info');
    });
    it('describes a bounded successful run without claiming the backlog is empty', () => {
        const result = scoringOutcome({scored: 2, total: 2, status: 'completed'});
        expect(result.type).toBe('success');
        expect(result.message).toBe('Saved 2/2 scores in this run.');
    });
    it('handles no eligible work and missing configuration', () => {
        expect(scoringOutcome({scored: 0, total: 0, status: 'completed'}).type).toBe('success');
        expect(scoringOutcome({status: 'skipped', stop_reason: 'Resume required'}).message).toContain('Resume required');
    });
});
