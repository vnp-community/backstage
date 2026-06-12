#!/usr/bin/env python3
"""
run_all.py — Script điều phối chạy toàn bộ pipeline seed

Quy trình:
  1. Health check kết nối đến Backstage
  2. Seed catalog entities từ seed/data/
  3. Chờ Backstage xử lý (ingestion pipeline)
  4. Verify kết quả
  5. Xuất báo cáo

Sử dụng:
  python run_all.py                    # Chạy đầy đủ pipeline
  python run_all.py --dry-run          # Dry run toàn bộ
  python run_all.py --feature service-catalog  # Chỉ một feature
  python run_all.py --skip-verify      # Seed mà không verify
  python run_all.py --wait 30          # Chờ 30s trước khi verify

Quy trình nếu chỉ muốn test server:
  python run_all.py --health-only
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backstage_client import BackstageClient
from config import init
from seed_entities import FEATURE_MAP, EntitySeeder
from verify import CatalogVerifier

logger = logging.getLogger("run_all")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chạy toàn bộ seed pipeline: health-check → seed → verify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py                          # Full pipeline
  python run_all.py --dry-run               # Preview mode
  python run_all.py --feature service-catalog  # Một feature
  python run_all.py --wait 60 --verify      # Seed rồi chờ 60s verify
  python run_all.py --health-only           # Chỉ kiểm tra kết nối
  python run_all.py --skip-verify           # Seed không verify

Feature groups:
  """ + ", ".join(FEATURE_MAP.keys()),
    )
    parser.add_argument(
        "--feature",
        choices=list(FEATURE_MAP.keys()),
        help="Chỉ chạy một feature group",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode — không thực sự seed",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Bỏ qua bước verify sau khi seed",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=10,
        metavar="SECONDS",
        help="Số giây chờ sau khi seed trước khi verify (default: 10)",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Chỉ kiểm tra kết nối, không seed",
    )
    parser.add_argument(
        "--export-report",
        metavar="FILE",
        default="",
        help="Xuất báo cáo verify ra file JSON",
    )
    return parser.parse_args()


def run_health_check(client: BackstageClient) -> bool:
    """Chạy health check và hiển thị thông tin server."""
    logger.info("─" * 60)
    logger.info("🏥 STEP 1: Health Check")
    logger.info("─" * 60)

    if not client.health_check():
        logger.error("❌ Server không phản hồi. Dừng lại.")
        return False

    # Lấy thêm thông tin catalog
    try:
        result = client.list_entities(limit=1)
        total = result.get("totalItems", "?")
        logger.info("   Catalog hiện có: %s entities", total)
    except Exception:
        pass

    return True


def run_seed(
    client: BackstageClient,
    data_dir: Path,
    feature: str = "",
    dry_run: bool = False,
    seed_mode: str = "auto",
    github_token: str = "",
    github_raw_base: str = "",
) -> bool:
    """Chạy seed và trả về True nếu thành công."""
    mode = "DRY-RUN" if dry_run else "LIVE"
    logger.info("─" * 60)
    logger.info("🌱 STEP 2: Seed Catalog [%s]", mode)
    logger.info("─" * 60)

    seeder = EntitySeeder(
        client,
        data_dir,
        dry_run=dry_run,
        seed_mode=seed_mode,
        github_token=github_token,
        github_raw_base=github_raw_base,
    )

    if feature:
        report = seeder.seed_feature(feature)
    else:
        report = seeder.seed_all()

    report.print_summary()

    success_rate = (report.succeeded / report.total * 100) if report.total > 0 else 0
    logger.info(
        "Seed result: %d/%d succeeded (%.0f%%)",
        report.succeeded,
        report.total,
        success_rate,
    )

    return report.failed == 0


def run_verify(
    client: BackstageClient,
    data_dir: Path,
    feature: str = "",
    export_file: str = "",
) -> bool:
    """Chạy verify và trả về True nếu healthy."""
    logger.info("─" * 60)
    logger.info("🔍 STEP 3: Verify Catalog")
    logger.info("─" * 60)

    verifier = CatalogVerifier(client, data_dir)
    report = verifier.generate_report(feature=feature or None)
    verifier.print_report(report)

    if export_file:
        import json
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("📄 Report saved to: %s", export_file)

    return report["summary"]["errors"] == 0


def main() -> int:
    args = parse_args()
    config, data_dir = init()

    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_raw_base = os.environ.get("GITHUB_RAW_BASE_URL", "")
    seed_mode = os.environ.get("SEED_MODE", "auto")

    logger.info("=" * 60)
    logger.info("🚀 Backstage Seed Pipeline")
    logger.info("   Server:  %s", config.base_url)
    logger.info("   Data:    %s", data_dir)
    logger.info("   Feature: %s", args.feature or "ALL")
    if args.dry_run:
        logger.info("   Mode:    DRY-RUN")
    logger.info("=" * 60)

    client = BackstageClient(config)

    # Step 1: Health check
    if not run_health_check(client):
        return 1

    if args.health_only:
        logger.info("✅ Health check passed. Server is reachable.")
        return 0

    # Step 2: Seed
    if not args.dry_run:
        seed_ok = run_seed(
            client,
            data_dir,
            feature=args.feature,
            dry_run=False,
            seed_mode=seed_mode,
            github_token=github_token,
            github_raw_base=github_raw_base,
        )
    else:
        seed_ok = run_seed(
            client,
            data_dir,
            feature=args.feature,
            dry_run=True,
            seed_mode=seed_mode,
            github_token=github_token,
            github_raw_base=github_raw_base,
        )
        logger.info("Dry-run complete. No actual changes made.")
        return 0

    if not seed_ok:
        logger.warning("⚠️  Seed có một số lỗi, tiếp tục verify...")

    # Chờ Backstage xử lý ingestion pipeline
    if not args.skip_verify and args.wait > 0:
        logger.info("\n⏳ Waiting %ds for Backstage to process entities...", args.wait)
        for i in range(args.wait, 0, -5 if args.wait > 5 else -1):
            logger.info("   %ds remaining...", i)
            time.sleep(min(5, i))

    # Step 3: Verify
    if not args.skip_verify:
        verify_ok = run_verify(
            client,
            data_dir,
            feature=args.feature,
            export_file=args.export_report,
        )
    else:
        logger.info("⏭  Skipping verify step")
        verify_ok = True

    # Final result
    logger.info("=" * 60)
    if seed_ok and verify_ok:
        logger.info("✅ Pipeline completed successfully!")
        return 0
    else:
        logger.warning("⚠️  Pipeline completed with issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
