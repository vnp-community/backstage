"""
cleanup.py — Dọn dẹp Backstage Catalog

Script xóa entities và locations đã được seed để reset về trạng thái ban đầu.

Sử dụng:
  python cleanup.py                  # Preview những gì sẽ xóa
  python cleanup.py --confirm        # Xóa thật sự
  python cleanup.py --locations      # Chỉ xóa locations
  python cleanup.py --kind Component # Chỉ xóa một loại entity
  python cleanup.py --namespace test # Chỉ xóa trong namespace cụ thể

⚠️  CẢNH BÁO: Hành động này không thể hoàn tác!
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from backstage_client import BackstageAPIError, BackstageClient
from config import init

logger = logging.getLogger("cleanup")

# Các entity kinds được phép xóa
DELETABLE_KINDS = [
    "Component",
    "API",
    "System",
    "Domain",
    "Resource",
    "Template",
    # Group và User thường được quản lý bởi identity provider
    # nên không xóa mặc định
]


def delete_entities_by_kind(
    client: BackstageClient,
    kind: str,
    namespace: Optional[str] = None,
    dry_run: bool = True,
) -> int:
    """
    Xóa tất cả entities của một kind.

    Returns:
        Số entities đã xóa (hoặc sẽ xóa trong dry-run)
    """
    logger.info("Processing kind: %s ...", kind)

    try:
        filter_str = f"metadata.namespace={namespace}" if namespace else None
        result = client.list_entities(kind=kind, limit=500, filter_str=filter_str)
        items = result.get("items", [])
    except BackstageAPIError as e:
        logger.error("Cannot list %s: %s", kind, e)
        return 0

    if not items:
        logger.info("  (no %s entities found)", kind)
        return 0

    logger.info("  Found %d %s entities", len(items), kind)
    deleted = 0

    for item in items:
        meta = item.get("metadata", {})
        name = meta.get("name", "?")
        ns = meta.get("namespace", "default")
        uid = meta.get("uid", "")

        if not uid:
            logger.warning("  ⚠️  No UID for %s/%s, skipping", ns, name)
            continue

        if dry_run:
            logger.info("  [DRY-RUN] Would delete: %s [%s] %s/%s", kind, uid[:8], ns, name)
            deleted += 1
        else:
            try:
                client.delete_entity(uid)
                logger.info("  🗑  Deleted: %s/%s", ns, name)
                deleted += 1
                time.sleep(client.config.request_delay)
            except BackstageAPIError as e:
                if e.status_code == 403:
                    logger.warning(
                        "  ⚠️  Cannot delete %s/%s: managed by ingestion (expected)", ns, name
                    )
                elif e.status_code == 404:
                    logger.debug("  Already deleted: %s/%s", ns, name)
                    deleted += 1
                else:
                    logger.error("  ❌ Error deleting %s/%s: %s", ns, name, e)

    return deleted


def delete_all_locations(
    client: BackstageClient,
    dry_run: bool = True,
    filter_target: Optional[str] = None,
) -> int:
    """
    Xóa tất cả registered locations.

    Args:
        filter_target: Chỉ xóa locations có target chứa chuỗi này
    """
    logger.info("Processing locations...")

    try:
        locations = client.list_locations()
    except BackstageAPIError as e:
        logger.error("Cannot list locations: %s", e)
        return 0

    if not locations:
        logger.info("  (no locations found)")
        return 0

    if filter_target:
        locations = [l for l in locations if filter_target in l.get("target", "")]
        logger.info("  Found %d locations matching '%s'", len(locations), filter_target)
    else:
        logger.info("  Found %d locations total", len(locations))

    deleted = 0
    for loc in locations:
        loc_id = loc.get("id", "")
        loc_type = loc.get("type", "?")
        target = loc.get("target", "?")

        if not loc_id:
            continue

        if dry_run:
            logger.info("  [DRY-RUN] Would delete location: [%s] %s", loc_type, target[-60:])
            deleted += 1
        else:
            try:
                client.delete_location(loc_id)
                logger.info("  🗑  Deleted location: [%s] %s", loc_type, target[-60:])
                deleted += 1
                time.sleep(client.config.request_delay)
            except BackstageAPIError as e:
                logger.error("  ❌ Error deleting location %s: %s", loc_id, e)

    return deleted


def show_catalog_summary(client: BackstageClient) -> None:
    """Hiển thị tổng quan catalog trước khi xóa."""
    logger.info("\n📊 Current Catalog State:")
    logger.info("─" * 40)

    total = 0
    for kind in DELETABLE_KINDS + ["Group", "User"]:
        try:
            result = client.list_entities(kind=kind, limit=500)
            count = len(result.get("items", []))
            total += count
            if count > 0:
                logger.info("  %-12s: %3d entities", kind, count)
        except BackstageAPIError:
            pass

    try:
        locations = client.list_locations()
        logger.info("  %-12s: %3d locations", "Locations", len(locations))
    except BackstageAPIError:
        pass

    logger.info("─" * 40)
    logger.info("  TOTAL: %d entities", total)


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dọn dẹp (xóa) entities và locations từ Backstage Catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  CẢNH BÁO: Xóa entities không thể hoàn tác!
Mặc định chạy ở dry-run mode (preview only).
Thêm --confirm để thực sự xóa.

Examples:
  python cleanup.py                     # Preview — không xóa thật
  python cleanup.py --confirm           # Xóa tất cả entities và locations
  python cleanup.py --locations-only --confirm   # Chỉ xóa locations
  python cleanup.py --kind Component --confirm   # Chỉ xóa Component entities
  python cleanup.py --target-filter seed         # Xóa locations có "seed" trong target
        """,
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="⚠️  Thực sự xóa (mặc định là dry-run/preview)",
    )
    parser.add_argument(
        "--locations-only",
        action="store_true",
        help="Chỉ xóa registered locations (không xóa entities)",
    )
    parser.add_argument(
        "--kind",
        choices=DELETABLE_KINDS + ["Group", "User"],
        help="Chỉ xóa một loại entity",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help="Chỉ xóa entities trong namespace cụ thể",
    )
    parser.add_argument(
        "--target-filter",
        default=None,
        help="Chỉ xóa locations có target URL/path chứa chuỗi này",
    )
    parser.add_argument(
        "--no-healthcheck",
        action="store_true",
        help="Bỏ qua health check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config, _ = init()

    dry_run = not args.confirm

    client = BackstageClient(config)

    if not args.no_healthcheck:
        if not client.health_check():
            logger.error("❌ Cannot connect to Backstage. Aborting.")
            return 1

    if dry_run:
        logger.info("=" * 60)
        logger.info("⚠️  DRY-RUN MODE — No actual deletions will happen")
        logger.info("    Add --confirm to perform actual cleanup")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("⚠️  LIVE MODE — Entities will be permanently deleted!")
        logger.warning("=" * 60)

    show_catalog_summary(client)

    total_deleted = 0

    # Xóa locations
    if not args.kind:  # Nếu không chỉ định kind, xóa locations
        logger.info("\n🗑  Cleaning up locations...")
        total_deleted += delete_all_locations(
            client,
            dry_run=dry_run,
            filter_target=args.target_filter,
        )

    # Xóa entities
    if not args.locations_only:
        if args.kind:
            kinds_to_delete = [args.kind]
        else:
            # Xóa theo thứ tự reverse dependency
            kinds_to_delete = list(reversed(DELETABLE_KINDS))

        logger.info("\n🗑  Cleaning up entities...")
        for kind in kinds_to_delete:
            total_deleted += delete_entities_by_kind(
                client,
                kind=kind,
                namespace=args.namespace,
                dry_run=dry_run,
            )

    if dry_run:
        logger.info("\n📋 Preview: %d items would be deleted", total_deleted)
        logger.info("   Run with --confirm to actually delete them")
    else:
        logger.info("\n✅ Cleanup complete: %d items deleted", total_deleted)

    return 0


if __name__ == "__main__":
    sys.exit(main())
