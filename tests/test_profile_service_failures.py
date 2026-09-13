from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai_client import AIClient
from app.embeddings import EmbeddingClient
from app.circuit_breaker import CircuitBreaker
from app import scheduler, enrichment


async def test_one_profiles_ai_failure_does_not_block_another():
    first, second = AIClient('ollama'), AIClient('ollama')
    first._chat_with_retry = AsyncMock(side_effect=OSError('Synthetic connection failure'))
    second._chat_with_retry = AsyncMock(return_value='Second profile result')
    for _ in range(5):
        with pytest.raises(OSError):
            await first.chat('Synthetic')
    with pytest.raises(RuntimeError, match='Circuit breaker'):
        await first.chat('Synthetic')
    assert await second.chat('Synthetic') == 'Second profile result'


async def test_one_profiles_embedding_failure_does_not_block_another():
    first, second = EmbeddingClient('ollama'), EmbeddingClient('ollama')
    first._embed_with_retry = AsyncMock(side_effect=OSError('Synthetic failure'))
    second._embed_with_retry = AsyncMock(return_value=[0.1, 0.2])
    for _ in range(5):
        with pytest.raises(OSError):
            await first.embed('Synthetic')
    with pytest.raises(RuntimeError, match='Circuit breaker'):
        await first.embed('Synthetic')
    assert await second.embed('Synthetic') == [0.1, 0.2]


async def test_source_failures_and_recovery_are_profile_scoped(monkeypatch):
    monkeypatch.setattr(scheduler, '_scraper_breaker', CircuitBreaker(failure_threshold=1))
    scrape = AsyncMock(side_effect=[OSError('Synthetic failure'), []])
    source = SimpleNamespace(source_name='synthetic', scrape=scrape)
    first = SimpleNamespace(candidate_id='first')
    second = SimpleNamespace(candidate_id='second', get_allowed_regions=AsyncMock(return_value=[]),
                             get_remote_only=AsyncMock(return_value=False), mark_scraper_ran=AsyncMock())
    await scheduler.run_scrape_cycle(first, [source], force=True)
    await scheduler.run_scrape_cycle(first, [source], force=True)
    assert scrape.await_count == 1
    await scheduler.run_scrape_cycle(second, [source], force=True)
    assert scrape.await_count == 2


async def test_enrichment_failure_is_profile_scoped(monkeypatch):
    monkeypatch.setattr(enrichment, '_enrichment_breaker', CircuitBreaker(failure_threshold=1))
    fetch = AsyncMock(side_effect=[None, 'Second profile listing'])
    monkeypatch.setattr(enrichment, '_fetch_and_extract', fetch)
    assert await enrichment.enrich_job_description('https://example.invalid', 'test', 'first') is None
    assert await enrichment.enrich_job_description('https://example.invalid', 'test', 'first') is None
    assert await enrichment.enrich_job_description('https://example.invalid', 'test', 'second') == 'Second profile listing'
