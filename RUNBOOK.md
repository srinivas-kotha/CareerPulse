# CareerPulse: running, using, and troubleshooting

This guide covers the existing Windows checkout and its background scripts. Run commands in PowerShell. Start with the repository folder:

```powershell
cd C:\Users\srini\Documents\Repo\CareerPulse
```

## 1. Before starting

- Confirm `.venv\Scripts\python.exe` exists. If the environment is missing, follow the installation instructions in [README.md](README.md).
- Start the Ollama desktop application if using local AI. Keep it running while scoring or generating documents.
- Confirm the configured model is installed:

```powershell
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
```

In CareerPulse Settings, select **Ollama (Local)**, select an installed model (for example, `qwen3.5:9b` if installed), and use `http://localhost:11434` as the base URL. Save the settings. A reachable Ollama server alone does not prove that the selected model works.

## 2. Start the application

Choose one mode. Do not start both at the same time.

### Background mode: close PowerShell afterward

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-background.ps1
```

Wait for **CareerPulse is running**. Open <http://127.0.0.1:8085>. You can then close PowerShell and the browser; the server continues running.

The script starts a hidden process, redirects logs outside the repository, and checks the database health response. It refuses to start if port 8085 is occupied. Its startup message does not prove that scraping and AI scoring work; use the checks below.

Background mode is not a Windows service. It does not automatically restart after a crash, reboot, or sign-out. Sleep suspends processing. Keep the computer awake, connected to the internet for scraping, and Ollama running for local AI. Run the start command again after reboot/sign-in.

### Foreground mode: see logs in the terminal

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8085
```

Keep this terminal open. Open <http://127.0.0.1:8085> in your browser. This mode is useful for diagnosing startup errors.

## 3. Use the application

1. **Review Settings.** Check your profile, work history, resume text, search terms, target titles, location preferences, sponsorship requirements, and AI configuration. Confirm the resume contains readable text and accurate facts.
2. **Discover jobs.** Click **Scrape Now**. Watch source results and progress. Sources can finish independently; a blocked source does not mean the entire run failed. Avoid repeatedly clicking while a run is active.
3. **Wait for the pipeline.** A manual scrape proceeds through scraping, enrichment, location classification, and scoring when AI is available. Downloading listings is only the first phase.
4. **Check scores.** Review job details, match reasons, concerns, and supporting quotes. An unscored job is different from a genuine score of zero. Review sponsorship and location eligibility against the actual listing.
5. **Resume unscored work if necessary.** First check that scoring is inactive using section 5. Then run:

   ```powershell
   Invoke-RestMethod -Method Post http://127.0.0.1:8085/api/score
   ```

   This requests scoring of unscored jobs. The response acknowledges the request; it does not mean scoring has completed. Do not repeatedly trigger runs, since requests can wait behind the scoring lock.

6. **Review and prepare applications.** Open a suitable job, inspect the employer's application destination, and generate tailored documents if needed. Read generated documents and autofilled answers before using them. Mark an application as applied only after actual submission, then track its pipeline status and interviews.

The server schedules scraping every six hours by default and scoring hourly while it runs. The scrape interval can be overridden by configuration; individual sources also have due-time rules. Scheduled work is not guaranteed to start immediately after a restart. Use **Scrape Now** for an immediate run.

## 4. Stop or restart

### Check for active work first

```powershell
Invoke-RestMethod http://127.0.0.1:8085/api/scrape/progress | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8085/api/score/progress | ConvertTo-Json
```

Normally wait until both report `active: false`. If a manual scrape needs to be cancelled:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8085/api/scrape/cancel
```

Recheck both progress endpoints afterward. A 404 means there is no active manual scrape to cancel. The progress endpoints are not an inventory of every scheduler task; check logs as well if scheduled work is running.

### Stop a background launch

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-background.ps1
```

The stop script uses the recorded process identity and refuses to stop when scrape or score progress is active. It uses process termination, not graceful application shutdown. It only manages launches made by the background start script.

### Stop a foreground launch

Press **Ctrl+C** in its original terminal. Wait for shutdown to complete. If shutdown appears stuck, read the logs before forcing it; browser scraping may still be cleaning up or retrying.

### Verify shutdown

```powershell
Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue
```

No output means no listener was found on that port. The application URL should no longer respond.

### Restart after code changes

Stop using the matching method above, verify the port is free, then run the chosen start command again. Refresh the browser and check health. Refreshing the browser alone does not load Python code changes. Starting and stopping normally preserves saved jobs and profiles; do not use data reset controls as a restart method.

## 5. Verify that it is working

Run these read-only checks in another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8085/api/health | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8085/api/scrape/progress | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8085/api/score/progress | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8085/api/stats | ConvertTo-Json
```

| Check | Expected result | What it does not prove |
| --- | --- | --- |
| Health | `status: healthy`, `db: ok`, `scheduler: running`; with AI configured, `ai_status: ok` | Every source works or model output passes validation |
| Manual scrape progress | Phase/current source changes; completed sources and listing counts appear | A source returning zero is necessarily broken |
| Scrape results | `listings_found` shows fetched results; `new_jobs` shows newly saved jobs | Every fetched listing is new; deduplication can make new jobs zero |
| Score progress | During work, `scored` increases, sometimes only after a batch finishes | `active: false` means all jobs were scored |
| Stats | `total_scored` increases after successful scoring; job counts reflect saved visible data | Counts must equal the current run totals or raw database row counts |
| Job details | Stored score has plausible reasons and source-grounded evidence | A high score guarantees eligibility or an interview |

Compare results over a few minutes rather than expecting every poll to change. Local AI can be slow. If scoring becomes inactive with `scored` below `total`, inspect logs for validation failures, timeouts, or connection errors. The normal manual score endpoint has a 30-minute limit, so large backlogs may need multiple runs.

Progress is held in memory and may reset after restart. An empty progress response after startup is not proof that scraping has never run. Health includes `last_scrape`; compare it with logs and saved jobs rather than treating it as proof that every source succeeded.

## 6. Find and read logs

Background logs are stored in `%LOCALAPPDATA%\CareerPulse\background`. Each launch has separate output and error files; ordinary INFO messages may also appear in the error log.

```powershell
$logRoot = Join-Path $env:LOCALAPPDATA 'CareerPulse\background'
Get-ChildItem -LiteralPath $logRoot | Sort-Object LastWriteTime -Descending
$launch = Get-Content -LiteralPath (Join-Path $logRoot 'process.json') -Raw | ConvertFrom-Json
Get-Content -LiteralPath $launch.stderr -Tail 80
Get-Content -LiteralPath $launch.stdout -Tail 40
```

To follow new messages, add `-Wait` to a `Get-Content` command. Press Ctrl+C to stop following the log; this does not stop the background server.

## 7. Troubleshooting

| Symptom | What to do |
| --- | --- |
| Port 8085 already in use / address already in use | Check the health URL. If CareerPulse is running, use it or stop its existing launch before restarting. Inspect the owning PID with the command below; do not kill every Python process. |
| Access denied stopping a process | Stop it from the original terminal/account that launched it. If it was launched elevated, use that terminal. Do not launch a second server against the same database to work around this. |
| No background launch record | The stop script cannot identify a foreground or older launch. Use its original terminal. |
| Stop script reports active work | Wait and recheck progress; cancel the manual scrape if appropriate. There is no dedicated score-cancel endpoint in this workflow. |
| Stop script fails because health/progress is unreachable | Inspect logs and the port owner. Do not assume the recorded process is still serving CareerPulse. Use the owning terminal or identify the exact application process in Task Manager. |
| Startup health check times out | Read the launch error log and check port 8085 before retrying. The process may still be starting. |
| Ollama connection refused or model unavailable | Open Ollama, check `/api/tags` or `ollama list`, then verify the saved provider, base URL, and installed model in Settings. |
| Ollama returns HTTP 200 but scoring fails evidence validation | The request succeeded, but the output was rejected. Check readable resume/job text. The matcher has one bounded correction retry; unsupported output remains unscored. Restart after matcher changes and check progress before retrying. |
| Consecutive empty batches / provider likely down | Inspect preceding errors. Older logs use this message for evidence failures too; it is not proof of a provider outage. |
| Indeed CAPTCHA or HTTP 403 | Indeed is blocking automated access. Inspect other sources and use the listing website manually when needed. Repeated retries do not establish success. |
| Browser driver closes during shutdown, then HTTP fallback starts | This is an observed scraper shutdown issue, not evidence that background mode failed. The current workflow does not claim it is fixed. Prefer stopping after scraping finishes. |
| No jobs appear | Remove restrictive feed filters, check source listing counts and search terms, and inspect source errors. Existing listings can be deduplicated; some sources need credentials. |
| Feed loads but scores do not change | Check AI health, resume availability, score progress, and validation logs. A working web page alone does not verify scoring. |
| Machine rebooted or slept | Start Ollama and CareerPulse again after reboot. Wake the machine after sleep, then verify health and progress. Background scripts do not install automatic startup. |

Identify the listener without stopping it:

```powershell
Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

## 8. Protect data and report a problem

These launch commands use the checkout's `data/jobfinder.db` default. Keep the same working directory on restart. Keep resumes, credentials, databases, backups, and logs out of Git. For a live SQLite database, use an online SQLite backup with an integrity check; copying only the main `.db` file while it is running can omit WAL changes.

When asking for help, include the action taken, foreground/background mode, approximate time, relevant health/progress output, and the nearby error-log lines. Remove personal details, resume text, credentials, and application answers before sharing. Do not clear jobs, reset all data, or delete the database to troubleshoot a startup or scoring error.
