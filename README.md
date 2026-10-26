QuietPhish 🐟🔐

Volunteer-operated phishing investigation workspace — a customized deployment of PhishGuard with Microsoft 365 mailbox ingestion, an independently maintained email-sample corpus, and automated investigation workflows.

Project status: community / early release. This repository packages the customized application and automation scripts. Some integration entry points and the Windows launcher need validation on a clean machine before the project can be described as one-click installable. Detection findings require human review; do not treat automated verdicts as conclusive.

What the system is designed to do

Receive or retrieve suspicious emails from an authorized mailbox, or process .eml samples from the public corpus.

Parse headers, authentication indicators, URLs, attachments, and other signals using the PhishGuard analysis engine.

Track which Microsoft 365 messages have already been processed to avoid repeat investigations.

Poll the external corpus for updates, detect newly added samples, and run the configured investigation automation.

Preserve reports and investigation artifacts locally for analyst review and follow-up.

QuietPhish is not a phishing-sending tool, a production email gateway, or a substitute for an incident responder. Only ingest mailboxes and samples you are authorized to process. Treat links and attachments as potentially hostile; use isolation and never execute suspicious attachments on your everyday computer.

Repository layout

QuietPhish/
├── README.md                         # This guide (at repository root)
├── .gitignore                        # Keeps local secrets and state out of Git
├── .gitmodules                        # Git submodule definition
├── SSSH-QuietPhish.vbs                # Windows launcher; see compatibility warning below
├── email-corpus/                      # Submodule of cw-l/email-corpus
└── PhishGuard/
    ├── .env.example                   # Example environment variables
    ├── requirements.txt
    ├── README.md                      # Original PhishGuard documentation
    ├── phishguard/                     # Application and web interface
    └── automation/
        ├── quietphish_corpus_sync.py
        ├── quietphish_auto_investigate.py
        ├── detect_new_samples.py
        ├── historical_queue.py
        ├── baseline_corpus.py
        └── sample_tracker.py

The email corpus is a Git submodule, not a vendored directory. Its contents and license remain under the upstream project. A normal git clone does not populate it automatically.

Requirements

Windows 10/11 with PowerShell (these instructions target Windows).

Git on PATH.

Python 3.10+ (verify compatible version with the app dependencies).

Internet access to clone the repository and update the corpus.

Optional: Node.js/npm for the upstream Next.js dashboard, depending on the UI launch path.

Optional: an authorized Microsoft 365 mailbox and an Entra ID app registration, if using M365 ingestion.

Optional: API credentials for supported reputation and enrichment services. These are not needed to clone or inspect the code.

1. Download QuietPhish and the corpus

Open Windows PowerShell in the directory where you want the project:

git clone --recurse-submodules https://github.com/scanshield1990/QuietPhish.git
Set-Location .\QuietPhish

If you already cloned without submodules:

git submodule update --init --recursive

Check that both directories exist:

Test-Path .\PhishGuard
Test-Path .\email-corpus\.git

Note: Newer Git submodule checkouts commonly use a .git file, rather than a directory; Test-Path succeeds for either. The corpus-sync script specifically checks for that path.

2. Create a private Python environment

Set-Location .\PhishGuard
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

For editable installation of the PhishGuard package, also run:

.\.venv\Scripts\python.exe -m pip install -e .

Compatibility note: The release includes customized modules with quietphish_ filenames. Some upstream imports, command-line entry points, or launcher targets may still refer to their original module names. If a command fails with ModuleNotFoundError, do not rename files at random; open an issue with the traceback. A clean-install integration test is still needed.

3. Create a local configuration (never commit it)

From QuietPhish\PhishGuard:

Copy-Item .env.example .env
notepad .env

Configure at least the web authentication fields:

PG_WEB_HOST=127.0.0.1
PG_WEB_PORT=8080
PG_WEB_USERNAME=admin
PG_WEB_PASSWORD=REPLACE_WITH_A_UNIQUE_PASSWORD
PG_WEB_SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
PG_MONITOR_ENABLED=false

Generate a fresh random web secret with Python (copy the output only into your local .env):

.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"

The committed .env.example is a template; .env contains your real values and must remain private. Never put API keys or passwords in GitHub issues, screenshots, sample reports, or commits.

Optional: IMAP mailbox ingestion

Set the following in your local .env only if you intend to use IMAP:

PG_IMAP_SERVER=imap.example.com
PG_IMAP_PORT=993
PG_IMAP_USE_SSL=true
PG_IMAP_USERNAME=your-mailbox@example.com
PG_IMAP_PASSWORD=YOUR_OWN_APP_PASSWORD_IF_SUPPORTED
PG_IMAP_MAILBOX=INBOX
PG_IMAP_UNSEEN_ONLY=true

Modern Microsoft 365 tenants commonly require OAuth instead of basic IMAP credentials; use the M365 integration below where supported. Do not enable both paths until you understand which mailbox and messages each monitors.

4. Optional: Microsoft 365 ingestion

Only connect a mailbox you own or have permission to investigate. Set up a dedicated Entra ID app registration under your own tenant, following your organization's approval and least-privilege requirements. The precise delegated/application permissions and consent flow depend on the implementation and must be checked against the M365 authentication and fetcher modules in this release.

Relevant local .env names used by the underlying configuration include:

PG_M365_TENANT_ID=YOUR_TENANT_ID
PG_M365_CLIENT_ID=YOUR_APP_CLIENT_ID
PG_M365_CLIENT_SECRET=YOUR_CLIENT_SECRET_IF_REQUIRED_BY_YOUR_AUTH_FLOW

Do not assume all three are required. The custom M365 authentication implementation may use interactive/delegated sign-in rather than a client secret; use the permissions and auth flow supported by your actual code. Avoid granting mailbox-wide application permissions unless specifically needed and approved. Do not use personal production mailboxes for testing without consent.

The local phishguard/mail/m365_history.py module stores processed message identifiers in a user-local SQLite database at:

%LOCALAPPDATA%\SSSH\PhishGuard\m365_history.db

That database is runtime state, not a file to distribute. Message history and credentials should not be copied between volunteers.

5. Optional: reputation and threat-intelligence integrations

Enable only providers for which you have your own accounts, API keys, and authorization. Supported configuration names in the supplied example and application include:

PG_VT_ENABLED=false
PG_VT_API_KEY=
PG_GSB_ENABLED=false
PG_GSB_API_KEY=
PG_SANDBOX_ENABLED=false
PG_SANDBOX_PROVIDER=
PG_SANDBOX_API_KEY=
PG_SANDBOX_URL=

Additional provider settings may include URLScan, Shodan, OTX, MISP, and AbuseIPDB; consult PhishGuard/phishguard/quietphish_config.py for their exact current environment variable names. Keep all optional services disabled until configured and tested. Sending email artifacts, URLs, or indicators to third-party services can disclose confidential information; defang and minimize data first.

6. Organization profile

The release deliberately excludes PhishGuard/org_profile.json, because an operator's real organization details should not be published.

To create a local profile, start with the shipped example:

Copy-Item .\docs\org_profile.example.json .\org_profile.json
notepad .\org_profile.json

Review its JSON keys before editing. Configure PG_ORG_PROFILE_PATH=org_profile.json in .env if you want organization-aware checks. Never commit your real internal domains, VIP names, or trusted sender lists.

7. Start the analysis interface

The upstream PhishGuard documentation describes this command from inside PhishGuard:

.\.venv\Scripts\phishguard.exe serve --host 127.0.0.1 --port 8080

Then visit http://127.0.0.1:8080 in a browser.

Important release caveat: This is the upstream documented entry point, not a confirmed clean-install launch command for the renamed QuietPhish modules. The current SSSH-QuietPhish.vbs may also contain legacy absolute paths and an upstream Flask module reference. Do not rely on the VBS launcher until it has been made portable and tested. If the upstream command fails, report the traceback and your Python version rather than guessing at a replacement.

For reference, the upstream usage and architecture documentation remains in PhishGuard/README.md.

8. Check the corpus synchronization manually

From QuietPhish\PhishGuard:

.\.venv\Scripts\python.exe .\automation\quietphish_corpus_sync.py

Expected behavior: the script finds the sibling QuietPhish\email-corpus Git checkout and executes git pull --ff-only there. It returns a success/failure message. The corpus repository must have a valid remote and must not contain conflicting local changes.

For a corpus stored elsewhere, set the environment variable in the PowerShell session running QuietPhish:

$env:QUIETPHISH_CORPUS_PATH = 'D:\Research\email-corpus'

The variable is read by the script at import time. If set, it takes precedence over the sibling checkout.

Submodule behavior: git pull inside the corpus directory can advance the local corpus beyond the commit pinned by QuietPhish. That is expected for a live research feed, but git submodule update --init --recursive can later reset it to the pinned commit. The upstream corpus is independently maintained; do not treat every sample as vetted or safe.

9. Establish a baseline and run the investigation workflow

The automation/ folder contains scripts for baseline generation, detecting new samples, queue tracking, and automated investigation:

baseline_corpus.py
sample_tracker.py
detect_new_samples.py
historical_queue.py
quietphish_auto_investigate.py

Recommended operational sequence:

Confirm your corpus checkout is healthy and the manual sync above succeeds.

Inspect the scripts and choose private directories for investigation artifacts and queue state.

Establish a baseline against the current corpus so existing samples are not all mistaken for new arrivals.

Test detection with a known benign test .eml and inspect the generated analysis before enabling continuous monitoring.

Verify any automatic investigations create reports without exposing secrets, uploading private messages, or contacting untrusted destinations.

Enable scheduling only after a manual end-to-end test succeeds. Keep a single worker initially to avoid duplicate processing.

The exact CLI arguments, baseline file names, task scheduling configuration, and ordering of these scripts have not yet been validated against a clean installation. Do not copy a live operator's queue/status JSON as a starter baseline: those files contain machine-specific state and are intentionally excluded from Git. To reproduce the complete unattended workflow, the project still needs a tested bootstrap command and a documented Windows Task Scheduler setup.

10. Optional: run on a schedule (after manual verification)

Windows Task Scheduler can invoke your chosen verified automation entry point using the virtual environment's python.exe and a working directory of QuietPhish\PhishGuard. Use an account with only the permissions required for the mailbox and corpus; log failures to a private directory, avoid overlapping tasks, and monitor for authentication failures. Do not schedule a script until you've confirmed it works manually.

11. Validate a new installation

From QuietPhish\PhishGuard:

.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\automation\quietphish_corpus_sync.py

Some tests may rely on upstream module names or external dependencies; failures should be documented rather than hidden. Check that local .env, credentials, investigation artifacts, and SQLite databases do not appear in git status before contributing.

Troubleshooting

Symptom

Check

email-corpus folder empty

git submodule update --init --recursive from repository root

Corpus sync reports missing checkout

Confirm email-corpus\.git exists or set QUIETPHISH_CORPUS_PATH

git pull --ff-only fails

Confirm remote, connectivity, and clean corpus working tree

Python module not found

Confirm .venv Python and review renamed quietphish_* modules versus upstream imports

Web interface does not start

Check .env, port availability, and current entry-point compatibility

M365 sign-in fails

Confirm tenant, app registration, account permissions, and the authentication flow supported by the code

Duplicate investigations

Verify baseline, queue state, message history, and whether multiple schedulers are running

No new investigations

Verify corpus updates, detection state, monitored paths, and script logs

Security, privacy, and responsible operation

Use only authorized mailboxes and lawfully obtained samples.

Do not commit .env, tokens, key material, user profiles, message databases, investigation records, or real mailbox exports.

Use test tenants/mailboxes for first-time setup. Apply least privilege and rotate exposed credentials immediately.

Do not execute attachments or visit suspected malicious URLs outside an isolated sandbox.

External enrichment services may retain submitted indicators; obtain approval before sending organizational data.

A phishing classification is an analyst aid, not proof of maliciousness.

Review Git history and use a dedicated secret scanner before publishing contributions. .gitignore does not remove secrets already committed.

Upstream projects and attribution

PhishGuard — original detection engine and application by @iampopg. MIT license; retain the original copyright and permission notice in PhishGuard/README.md and applicable source distributions.

email-corpus — external sample collection by Lee Cheng Wei / cw-l. Included as a Git submodule. Consult its own LICENSE and assess rights and privacy before redistributing individual email samples.

QuietPhish — custom integration and volunteer workflow maintained in this repository. The upstream license does not automatically establish a license for any newly authored material; maintainers should add a clear top-level license and attribution policy.

Contributing

Bug reports, reproducible installation issues, documentation fixes, and tested improvements are welcome. Never include real messages, personal information, API keys, or tokens in issues or pull requests. Clearly identify whether a problem belongs to the upstream engine, the corpus, or QuietPhish-specific automation.

Release readiness note: This guide documents the intended architecture and configuration supported by the files reviewed. It does not claim that the current public checkout has passed an end-to-end fresh-machine installation. Before advertising "same exact automated setup," validate the launcher, renamed-module imports, baseline/queue bootstrap, and scheduled investigation loop on a clean Windows machine.
