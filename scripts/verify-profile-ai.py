"""Optional local Ollama check; two synthetic profiles, no live DB or cloud calls."""
import argparse
import asyncio
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai_client import AIClient
from app.candidates import CandidateRegistry
from app.candidate_runtime import CandidateRuntimeManager


async def verify(model):
    fixtures = [
        ('Platform', 'Built Python services and automated deployment testing. Maintained PostgreSQL databases.',
         'Build Python services and automated deployment testing. Maintain PostgreSQL databases.'),
        ('Design', 'Designed accessible interfaces and conducted usability testing. Created interactive product prototypes.',
         'Design accessible interfaces and conduct usability testing. Create interactive product prototypes.'),
    ]
    with tempfile.TemporaryDirectory(prefix='careerpulse-local-ai-') as root:
        registry = CandidateRegistry(root)
        async with CandidateRuntimeManager(registry) as manager:
            runtimes = []
            for name, resume, description in fixtures:
                record = await registry.create(name)
                runtime = await manager.get(record.candidate_id)
                await runtime.state.db.save_user_profile(requires_sponsorship='no', eligibility_policy={'confirmed': True})
                await runtime.state.reinit_ai_services(AIClient('ollama', model=model, base_url='http://127.0.0.1:11434'), resume)
                job_id = await runtime.state.db.insert_job(
                    title=name + ' role', company='Synthetic Example', location='Remote',
                    salary_min=None, salary_max=None, description=description,
                    url='https://example.invalid/same-job', posted_date=None,
                    application_method='url', contact_email=None)
                await runtime.state.db.set_job_location_region(job_id, 'US')
                runtimes.append(runtime)
            # Sequential local calls keep the hardware load bounded.
            for index, runtime in enumerate(runtimes):
                await runtime.state.score_unscored(runtime.state.bg_db)
                score = await runtime.state.db.get_score(1)
                if score is None:
                    raise RuntimeError(f'Synthetic profile {index + 1}: model returned no validated score')
                if index == 0:
                    assert await runtimes[1].state.db.get_score(1) is None
                print(f'Profile {index + 1}: validated local score saved only to its own DB', flush=True)
            assert runtimes[0].state.matcher.resume_text != runtimes[1].state.matcher.resume_text
    print('PASS: two isolated synthetic profiles scored with local Ollama. This is not the 30-case quality benchmark.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='An already installed Ollama model tag')
    args = parser.parse_args()
    asyncio.run(verify(args.model))
