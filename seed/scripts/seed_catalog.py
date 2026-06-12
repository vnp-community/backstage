"""
seed_catalog.py — Seed Service Catalog Entities

Script triển khai dữ liệu từ seed/data/ lên Backstage Catalog thông qua REST API.

Tính năng:
  - Đăng ký toàn bộ entities từ các file YAML trong seed/data/
  - Hỗ trợ Location, Component, API, System, Domain, Resource, Group, User
  - Idempotent: chạy lại không gây lỗi (locations đã tồn tại sẽ được bỏ qua)
  - Dry-run mode: kiểm tra trước khi seed thật
  - Bộ lọc theo feature group

Sử dụng:
  python seed_catalog.py                       # Seed tất cả
  python seed_catalog.py --dry-run             # Kiểm tra không seed thật
  python seed_catalog.py --group service-catalog  # Chỉ seed một nhóm feature
  python seed_catalog.py --verify              # Chỉ verify không seed
  python seed_catalog.py --list               # Liệt kê tất cả data files

Cấu trúc seed/data theo features.md:
  service-catalog/
    catalog-service-management/ — Catalog quản lý dịch vụ
    metadata-and-ownership/     — Metadata & Ownership
  apis/
    api-catalog/                — API Catalog
    api-discovery/              — API Discovery
  documentation/
    techdocs/                   — TechDocs components
  software-templates/ (nếu có)
  security/
  governance/
  ...
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

# Thêm thư mục scripts vào sys.path
sys.path.insert(0, str(Path(__file__).parent))

from backstage_client import BackstageAPIError, BackstageClient, SeedReport, SeedResult
from config import init

logger = logging.getLogger("seed_catalog")


# ------------------------------------------------------------------ #
# Feature groups — ánh xạ theo features.md
# ------------------------------------------------------------------ #

FEATURE_GROUPS: dict[str, list[str]] = {
    "service-catalog": [
        "service-catalog/catalog-service-management",
        "service-catalog/metadata-and-ownership",
    ],
    "apis": [
        "apis/api-catalog",
        "apis/api-discovery",
    ],
    "documentation": [
        "documentation",
    ],
    "software-templates": [
        "software-templates",
    ],
    "ci-cd": [
        "ci-cd",
    ],
    "infrastructure": [
        "infrastructure",
    ],
    "monitoring": [
        "monitoring",
    ],
    "architecture": [
        "architecture",
    ],
    "security": [
        "security",
    ],
    "collaboration": [
        "collaboration",
    ],
    "extensibility": [
        "extensibility",
    ],
    "governance": [
        "governance",
    ],
    "developer-experience": [
        "developer-experience",
    ],
    "search": [
        "search",
    ],
}


# ------------------------------------------------------------------ #
# YAML helpers
# ------------------------------------------------------------------ #


def load_yaml_file(path: Path) -> list[dict]:
    """
    Đọc file YAML, hỗ trợ multi-document (phân cách bởi ---).
    Trả về danh sách các documents.
    """
    try:
        with open(path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        return [d for d in docs if d is not None]
    except yaml.YAMLError as e:
        logger.error("YAML parse error in %s: %s", path, e)
        return []
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
        return []


def is_backstage_entity(doc: dict) -> bool:
    """Kiểm tra xem document có phải Backstage entity không."""
    return (
        isinstance(doc, dict)
        and "apiVersion" in doc
        and doc.get("apiVersion", "").startswith("backstage.io/")
        and "kind" in doc
        and "metadata" in doc
    )


def entity_ref(doc: dict) -> str:
    """Tạo entity ref dạng 'kind:namespace/name'."""
    kind = doc.get("kind", "Unknown").lower()
    namespace = doc.get("metadata", {}).get("namespace", "default")
    name = doc.get("metadata", {}).get("name", "unknown")
    return f"{kind}:{namespace}/{name}"


# ------------------------------------------------------------------ #
# Seeder class
# ------------------------------------------------------------------ #


class CatalogSeeder:
    """Seed Backstage Catalog từ các file YAML trong data directory."""

    def __init__(
        self,
        client: BackstageClient,
        data_dir: Path,
        dry_run: bool = False,
    ):
        self.client = client
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.report = SeedReport()

    def _collect_yaml_files(self, subdir: Optional[str] = None) -> list[Path]:
        """Thu thập tất cả file YAML trong data_dir (hoặc subdir cụ thể)."""
        search_root = self.data_dir
        if subdir:
            search_root = self.data_dir / subdir

        if not search_root.exists():
            logger.warning("Directory not found: %s", search_root)
            return []

        yaml_files = sorted(
            p
            for p in search_root.rglob("*.yaml")
            if not p.name.startswith(".")
            # Bỏ qua mkdocs.yml vì không phải Backstage entity
            and p.name != "mkdocs.yml"
        )
        return yaml_files

    def _seed_location_for_file(self, yaml_path: Path) -> None:
        """
        Đăng ký một file YAML như là một Location vào Backstage.

        Backstage sẽ tự động read và process entities từ file đó.
        """
        # Tạo URL dạng file:// hoặc dùng đường dẫn tuyệt đối
        target = str(yaml_path.resolve())
        loc_type = "file"

        # Đọc file để lấy thông tin cho report
        docs = load_yaml_file(yaml_path)
        if not docs:
            return

        for doc in docs:
            if not is_backstage_entity(doc):
                continue

            kind = doc.get("kind", "Unknown")
            name = doc.get("metadata", {}).get("name", "unknown")
            ref = entity_ref(doc)

            try:
                if self.dry_run:
                    logger.debug("[DRY-RUN] Would register: %s", ref)
                    self.report.add(
                        SeedResult(
                            name=name,
                            kind=kind,
                            success=True,
                            action="dry-run",
                            message=f"Would register from {yaml_path.name}",
                            entity_ref=ref,
                        )
                    )
                else:
                    result = self.client.register_location(loc_type, target)

                    if result.get("exists"):
                        self.report.add(
                            SeedResult(
                                name=name,
                                kind=kind,
                                success=True,
                                action="skipped",
                                message="Location already registered",
                                entity_ref=ref,
                            )
                        )
                    else:
                        location_id = result.get("location", {}).get("id", "")
                        self.report.add(
                            SeedResult(
                                name=name,
                                kind=kind,
                                success=True,
                                action="created",
                                message=f"Location registered (id: {location_id[:8]}...)"
                                if location_id
                                else "Location registered",
                                entity_ref=ref,
                            )
                        )

                    # Nhỏ delay để tránh overwhelm server
                    time.sleep(self.client.config.request_delay)

            except BackstageAPIError as e:
                self.report.add(
                    SeedResult(
                        name=name,
                        kind=kind,
                        success=False,
                        action="error",
                        message=str(e),
                        entity_ref=ref,
                    )
                )

    def _seed_directory(self, subdir: str) -> None:
        """Seed tất cả YAML files trong một thư mục con."""
        yaml_files = self._collect_yaml_files(subdir)
        if not yaml_files:
            logger.info("  No YAML files found in: %s/%s", self.data_dir.name, subdir)
            return

        # Ưu tiên đăng ký catalog-info.yaml (Location files) trước
        location_files = [f for f in yaml_files if f.name == "catalog-info.yaml"]
        other_files = [f for f in yaml_files if f.name != "catalog-info.yaml"]

        # Đăng ký Location files trước
        for f in location_files:
            logger.debug("Processing Location file: %s", f.relative_to(self.data_dir))
            self._seed_location_for_file(f)

        # Sau đó các entity files khác (nếu cần đăng ký trực tiếp)
        for f in other_files:
            docs = load_yaml_file(f)
            has_entities = any(is_backstage_entity(d) for d in docs)
            if has_entities:
                logger.debug("Processing entity file: %s", f.relative_to(self.data_dir))
                self._seed_location_for_file(f)

    def seed_feature_group(self, group: str) -> SeedReport:
        """Seed một feature group cụ thể."""
        subdirs = FEATURE_GROUPS.get(group)
        if not subdirs:
            logger.error("Unknown feature group: '%s'", group)
            logger.info("Available groups: %s", ", ".join(FEATURE_GROUPS.keys()))
            return self.report

        logger.info("🚀 Seeding feature group: %s", group)
        for subdir in subdirs:
            logger.info("  📂 Processing: %s", subdir)
            self._seed_directory(subdir)

        return self.report

    def seed_all(self) -> SeedReport:
        """Seed tất cả feature groups."""
        dry_label = " [DRY-RUN]" if self.dry_run else ""
        logger.info("🚀 Starting full catalog seed%s", dry_label)
        logger.info("   Data directory: %s", self.data_dir)
        logger.info("   Server: %s", self.client.config.base_url)

        for group in FEATURE_GROUPS:
            logger.info("\n📦 Feature group: %s", group)
            subdirs = FEATURE_GROUPS[group]
            for subdir in subdirs:
                logger.info("  📂 %s", subdir)
                self._seed_directory(subdir)

        return self.report

    def list_data_files(self) -> None:
        """Liệt kê tất cả file YAML sẽ được seed."""
        print("\n📋 Data files to be seeded:")
        print("=" * 60)

        total = 0
        for group, subdirs in FEATURE_GROUPS.items():
            group_files = []
            for subdir in subdirs:
                files = self._collect_yaml_files(subdir)
                group_files.extend(files)

            if group_files:
                print(f"\n🏷  {group}:")
                for f in group_files:
                    docs = load_yaml_file(f)
                    entities = [d for d in docs if is_backstage_entity(d)]
                    entity_list = ", ".join(
                        f"{d.get('kind')}:{d.get('metadata', {}).get('name')}"
                        for d in entities
                    )
                    rel_path = f.relative_to(self.data_dir)
                    print(f"   📄 {rel_path}")
                    if entity_list:
                        print(f"      → {entity_list}")
                    total += len(entities)

        print(f"\n📊 Total entities: {total}")

    def verify_entities(self) -> None:
        """Verify xem entities đã được seed thành công chưa."""
        logger.info("🔍 Verifying seeded entities...")

        all_kinds = ["Component", "API", "System", "Domain", "Resource", "Group", "User"]
        total_found = 0

        for kind in all_kinds:
            try:
                result = self.client.list_entities(kind=kind, limit=200)
                items = result.get("items", [])
                if items:
                    total_found += len(items)
                    logger.info("  ✅ %s: %d entities", kind, len(items))
                    for item in items[:5]:  # Hiển thị tối đa 5
                        name = item.get("metadata", {}).get("name", "?")
                        namespace = item.get("metadata", {}).get("namespace", "default")
                        logger.info("     • %s/%s", namespace, name)
                    if len(items) > 5:
                        logger.info("     ... và %d nữa", len(items) - 5)
            except BackstageAPIError as e:
                logger.warning("  ⚠️  Could not list %s: %s", kind, e)

        logger.info("\n📊 Total entities in catalog: %d", total_found)


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Backstage Service Catalog from YAML data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_catalog.py                          # Seed tất cả
  python seed_catalog.py --dry-run               # Kiểm tra không seed thật
  python seed_catalog.py --group service-catalog # Chỉ seed Service Catalog
  python seed_catalog.py --group apis            # Chỉ seed APIs
  python seed_catalog.py --verify               # Verify sau khi seed
  python seed_catalog.py --list                 # Liệt kê data files

Available feature groups:
  """ + "  \n  ".join(FEATURE_GROUPS.keys()),
    )
    parser.add_argument(
        "--group",
        choices=list(FEATURE_GROUPS.keys()),
        help="Chỉ seed một feature group cụ thể",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Kiểm tra mà không thực sự seed",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify entities sau khi seed",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Liệt kê tất cả data files sẽ được seed",
    )
    parser.add_argument(
        "--no-healthcheck",
        action="store_true",
        help="Bỏ qua health check kết nối",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Khởi tạo config và logging
    config, data_dir = init()

    logger.info("=" * 60)
    logger.info("Backstage Catalog Seeder")
    logger.info("Server:   %s", config.base_url)
    logger.info("Data dir: %s", data_dir)
    if args.dry_run:
        logger.info("Mode:     DRY-RUN (no actual changes)")
    logger.info("=" * 60)

    client = BackstageClient(config)

    # Health check
    if not args.no_healthcheck:
        if not client.health_check():
            logger.error("❌ Cannot connect to Backstage. Aborting.")
            return 1

    seeder = CatalogSeeder(client, data_dir, dry_run=args.dry_run)

    # Mode: list
    if args.list:
        seeder.list_data_files()
        return 0

    # Mode: verify only
    if args.verify and not args.group:
        seeder.verify_entities()
        return 0

    # Mode: seed
    if args.group:
        report = seeder.seed_feature_group(args.group)
    else:
        report = seeder.seed_all()

    report.print_summary()

    # Verify sau khi seed
    if args.verify:
        seeder.verify_entities()

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
