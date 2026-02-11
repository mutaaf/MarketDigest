#!/usr/bin/env python3
"""Entry point: --type morning|afternoon|weekly --mode facts|full|both --dry-run --action-items"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import setup_logging
from config.settings import get_settings
from src.digest.builder import DigestBuilder
from src.digest.morning import build_morning_digest
from src.digest.afternoon import build_afternoon_digest
from src.digest.weekly import build_weekly_digest
from src.digest.daytrade import build_daytrade_digest
from src.delivery.telegram_bot import TelegramDelivery

logger = setup_logging()

DIGEST_BUILDERS = {
    "morning": build_morning_digest,
    "afternoon": build_afternoon_digest,
    "weekly": build_weekly_digest,
    "daytrade": build_daytrade_digest,
}

HISTORY_FILE = Path(__file__).parent.parent / "logs" / "digest_history.json"


def _save_history(digest_type: str, mode: str, success: bool, message_count: int = 0, dry_run: bool = False) -> None:
    """Append run metadata to digest_history.json."""
    HISTORY_FILE.parent.mkdir(exist_ok=True)

    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            history = []

    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": digest_type,
        "mode": mode,
        "success": success,
        "message_count": message_count,
        "dry_run": dry_run,
    })

    # Keep last 100 entries
    history = history[-100:]

    try:
        HISTORY_FILE.write_text(json.dumps(history, indent=2))
    except OSError as e:
        logger.warning(f"Failed to save digest history: {e}")


def _build_digest(build_fn, builder, mode, out_data=None):
    """Call the build function with the appropriate mode."""
    return build_fn(builder, mode=mode, out_data=out_data)


def _print_dry_run(content, label):
    """Print a digest to console with HTML tags stripped."""
    import re
    print("\n" + "=" * 60)
    print(f"DRY RUN — {label}")
    print("=" * 60)
    clean = re.sub(r"<[^>]+>", "", content)
    print(clean)
    print("=" * 60)
    print(f"Total length: {len(content)} chars")
    from src.digest.formatter import split_message
    msgs = split_message(content)
    print(f"Would send {len(msgs)} Telegram message(s)")
    return len(msgs)


def main():
    parser = argparse.ArgumentParser(description="Financial Market Digest")
    parser.add_argument(
        "--type",
        choices=["morning", "afternoon", "weekly", "daytrade"],
        required=True,
        help="Type of digest to generate",
    )
    parser.add_argument(
        "--mode",
        choices=["facts", "full", "both"],
        default="facts",
        help="facts = data only, full = data + LLM analysis, both = send facts then full",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print digest to console instead of sending via Telegram",
    )
    parser.add_argument(
        "--action-items",
        action="store_true",
        help="Generate and send a separate Action Items message after the main digest",
    )
    args = parser.parse_args()

    # Warn if LLM mode requested but no keys configured
    settings = get_settings()
    if args.mode in ("full", "both") and not settings.has_llm_key():
        logger.warning(
            "No LLM API keys configured (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY). "
            "LLM analysis will be skipped — digest will contain facts only."
        )

    logger.info(f"Building {args.type} digest (mode={args.mode})...")

    try:
        builder = DigestBuilder()
        build_fn = DIGEST_BUILDERS[args.type]

        # Capture digest data for action items if requested
        digest_data = {} if args.action_items else None

        if args.mode == "both":
            facts_content = _build_digest(build_fn, builder, "facts", out_data=digest_data)
            full_content = _build_digest(build_fn, builder, "full", out_data=digest_data)
        elif args.mode == "full":
            full_content = _build_digest(build_fn, builder, "full", out_data=digest_data)
            facts_content = None
        else:
            facts_content = _build_digest(build_fn, builder, "facts", out_data=digest_data)
            full_content = None

        # Build action items if requested
        action_items_content = None
        if args.action_items and digest_data:
            from src.digest.action_items import build_action_items
            action_mode = "full" if args.mode in ("full", "both") else "facts"
            action_items_content = build_action_items(builder, args.type, action_mode, digest_data)
            if action_items_content:
                logger.info(f"Action items built ({len(action_items_content)} chars)")
            else:
                logger.warning("Action items generation returned no content")

    except Exception as e:
        logger.error(f"Failed to build {args.type} digest: {e}", exc_info=True)
        _save_history(args.type, args.mode, success=False)
        sys.exit(1)

    if args.dry_run:
        msg_count = 0
        if facts_content:
            msg_count += _print_dry_run(facts_content, f"{args.type.upper()} DIGEST (FACTS)")
        if full_content:
            msg_count += _print_dry_run(full_content, f"{args.type.upper()} DIGEST (FULL ANALYSIS)")
        if action_items_content:
            msg_count += _print_dry_run(action_items_content, f"{args.type.upper()} ACTION ITEMS")
        _save_history(args.type, args.mode, success=True, message_count=msg_count, dry_run=True)
        return

    try:
        delivery = TelegramDelivery()
        total_messages = 0

        if facts_content:
            logger.info(f"Sending {args.type} facts digest...")
            success = delivery.send_digest_sync(facts_content)
            if not success:
                logger.error(f"Some messages failed to send for {args.type} facts digest")
                _save_history(args.type, args.mode, success=False)
                sys.exit(1)
            from src.digest.formatter import split_message
            total_messages += len(split_message(facts_content))
            logger.info(f"{args.type.title()} facts digest sent successfully!")

        if full_content:
            logger.info(f"Sending {args.type} full analysis digest...")
            success = delivery.send_digest_sync(full_content)
            if not success:
                logger.error(f"Some messages failed to send for {args.type} full analysis digest")
                _save_history(args.type, args.mode, success=False)
                sys.exit(1)
            from src.digest.formatter import split_message
            total_messages += len(split_message(full_content))
            logger.info(f"{args.type.title()} full analysis digest sent successfully!")

        if action_items_content:
            logger.info("Sending action items (2s delay)...")
            time.sleep(2)
            success = delivery.send_digest_sync(action_items_content)
            if not success:
                logger.error("Some messages failed to send for action items")
                _save_history(args.type, args.mode, success=False)
                sys.exit(1)
            from src.digest.formatter import split_message
            total_messages += len(split_message(action_items_content))
            logger.info("Action items sent successfully!")

        _save_history(args.type, args.mode, success=True, message_count=total_messages)

    except Exception as e:
        logger.error(f"Failed to deliver {args.type} digest: {e}", exc_info=True)
        _save_history(args.type, args.mode, success=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
