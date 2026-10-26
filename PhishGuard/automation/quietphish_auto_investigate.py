import sys
import time
import logging
import json
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths relative to the installed project, not a personal home directory.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from corpus_sync import sync_email_corpus
from detect_new_samples import detect_new_samples
from sample_tracker import calculate_sha256, mark_sample_processed
from historical_queue import get_historical_samples, HISTORICAL_INTERVAL
from phishguard.mail.parser import parse_message
from phishguard.pipeline import analyze_email
from phishguard.email_evidence import save_original_email
from phishguard.web.app import _runtime_ctx, _persist

CHECK_INTERVAL = 300  # Check every 5 minutes
# Runtime state and logs are local artifacts; exclude them from public Git.
STATUS_FILE = ROOT / "automation" / "monitor_status.json"
HISTORICAL_STATE_FILE = ROOT / "automation" / "historical_queue_state.json"

def update_monitor_status(**updates):
    status = {}

    if STATUS_FILE.exists():
        try:
            status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    status.update(updates)
    status["last_updated"] = datetime.now(timezone.utc).isoformat()

    temporary_file = STATUS_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(status, indent=2),
        encoding="utf-8"
    )
    temporary_file.replace(STATUS_FILE)
logging.basicConfig(
    filename=str(ROOT / "automation" / "monitor.log"),
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def historical_batch_due():
    """Check whether the historical investigation batch is due."""
    import time

    if not HISTORICAL_STATE_FILE.exists():
        return True

    try:
        state = json.loads(
            HISTORICAL_STATE_FILE.read_text(encoding="utf-8")
        )

        last_run = float(state.get("last_run", 0))

        return time.time() - last_run >= HISTORICAL_INTERVAL

    except (OSError, ValueError, TypeError):
        return True


def record_historical_batch():
    """Record when a historical investigation batch runs."""
    import time

    state = {
        "last_run": time.time(),
        "last_run_utc": datetime.now(timezone.utc).isoformat()
    }

    HISTORICAL_STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )

def investigate_new_samples():
    update_monitor_status(
        state="running",
        last_check=datetime.now(timezone.utc).isoformat()
    )

    if not sync_email_corpus():
        logging.warning("Git synchronization failed. Retrying next cycle.")
        return

    update_monitor_status(
        last_sync=datetime.now(timezone.utc).isoformat(),
        last_sync_result="success"
    )

    samples = detect_new_samples()

    update_monitor_status(
        new_samples=len(samples)
    )

    if not samples:
        logging.info("No new phishing samples detected.")
        return

    logging.info("Found %d new samples.", len(samples))
    
    completed = 0
    failed = 0
    ctx = _runtime_ctx()

    for sample in samples:
        try:
            raw = sample.read_bytes()
            sha256 = calculate_sha256(sample)
 
            parsed = parse_message(raw)
            report = analyze_email(parsed, ctx)

            # Preserve original email evidence before persisting report
            evidence = save_original_email(
                ctx.config.report_dir,
                report.report_id,
                raw
            )

            # Save investigation report
            _persist(ctx, parsed, report)

            logging.info(
               "[QuietPhish Evidence] Saved %s SHA256: %s",
               evidence["filename"],
               evidence["sha256"]
            )

            mark_sample_processed(sha256, sample)
            completed += 1

            update_monitor_status(
                investigations_completed=completed,
                last_investigation=datetime.now(timezone.utc).isoformat()
            )
            logging.info(
                "Investigation completed: %s | Report: %s",
                sample.name,
                report.report_id
            )

        except Exception:
            failed += 1

            update_monitor_status(
                investigations_failed=failed,
                last_error=datetime.now(timezone.utc).isoformat(),
                last_error_sample=sample.name
            )

            logging.exception(
                "Investigation failed for %s. Will retry later.",
                sample.name
            )

def investigate_historical_samples():
    """Investigate up to three historical emails per scheduled batch."""

    samples = get_historical_samples()

    if not samples:
        logging.info("No unprocessed historical samples remain.")
        return

    logging.info(
        "Starting historical investigation batch: %d samples.",
        len(samples)
    )

    ctx = _runtime_ctx()

    for sample in samples:
        try:
            raw = sample.read_bytes()
            sha256 = calculate_sha256(sample)

            parsed = parse_message(raw)
            report = analyze_email(parsed, ctx)

            # Preserve original forensic evidence.
            evidence = save_original_email(
                ctx.config.report_dir,
                report.report_id,
                raw
            )

            # Save investigation report.
            _persist(ctx, parsed, report)

            # Mark historical sample as processed.
            mark_sample_processed(sha256, sample)

            logging.info(
                "Historical investigation completed: %s | Report: %s",
                sample.name,
                report.report_id
            )

        except Exception:
            logging.exception(
                "Historical investigation failed for %s.",
                sample.name
            )

def main():
    logging.info("SSSH QuietPhish dual-queue investigation started.")

    while True:
        # PRIORITY 1: Investigate newly discovered GitHub emails.
        try:
            investigate_new_samples()
        except Exception:
            logging.exception("New email monitoring cycle failed.")

        # PRIORITY 2: Process historical emails every three hours.
        try:
            if historical_batch_due():
                logging.info("Historical investigation batch is due.")

                investigate_historical_samples()

                # Record completion to maintain the three-hour schedule.
                record_historical_batch()

        except Exception:
            logging.exception("Historical investigation cycle failed.")

        # Continue checking for new emails every five minutes.
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()