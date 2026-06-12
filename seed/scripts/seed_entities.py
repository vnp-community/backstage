"""
seed_entities.py — Seed Backstage Entities theo feature groups

Hỗ trợ 3 mode (cấu hình qua SEED_MODE trong .env):

  SEED_MODE=file        — file:// paths (chỉ với local Backstage - localhost)
  SEED_MODE=github-raw  — raw.githubusercontent.com URLs (repo đã push lên GitHub)
  SEED_MODE=github-gist — Upload YAML lên GitHub Gist → register URL (cho remote server)

Mặc định: tự động chọn mode phù hợp
  - Nếu server là localhost → dùng "file"
  - Ngược lại → dùng "github-gist" (cần GITHUB_TOKEN trong .env)

Sử dụng:
  python seed_entities.py                           # Seed tất cả features
  python seed_entities.py --feature service-catalog # Seed một feature
  python seed_entities.py --dry-run                 # Preview không seed thật
  python seed_entities.py --status                  # Xem trạng thái catalog hiện tại
  python seed_entities.py --cleanup-gists           # Xóa các Gists đã tạo
  python seed_entities.py --mode github-gist        # Force mode cụ thể
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from backstage_client import BackstageAPIError, BackstageClient, SeedReport, SeedResult
from config import init, SCRIPTS_DIR

logger = logging.getLogger("seed_entities")

# ------------------------------------------------------------------ #
# Feature directory mapping (theo features.md)
# ------------------------------------------------------------------ #

FEATURE_MAP: dict[str, dict] = {
    "service-catalog": {
        "label": "Service Catalog — Catalog quản lý dịch vụ",
        "dirs": [
            "service-catalog/catalog-service-management",
            "service-catalog/metadata-and-ownership",
        ],
        "description": "Quản lý tập trung microservices, APIs, websites, libraries, data pipelines",
    },
    "apis": {
        "label": "APIs — API Catalog & Discovery",
        "dirs": [
            "apis/api-catalog",
            "apis/api-discovery",
        ],
        "description": "Quản lý API, schema OpenAPI, GraphQL, AsyncAPI",
    },
    "documentation": {
        "label": "Documentation — TechDocs",
        "dirs": [
            "documentation",
        ],
        "description": "Tài liệu kỹ thuật TechDocs",
    },
    "software-templates": {
        "label": "Software Templates — Scaffolder",
        "dirs": [
            "software-templates",
        ],
        "description": "Templates chuẩn hóa, Golden Path",
    },
    "ci-cd": {
        "label": "CI/CD — Pipeline Integration",
        "dirs": [
            "ci-cd",
        ],
        "description": "Pipeline, Build & Deployment Visibility",
    },
    "infrastructure": {
        "label": "Infrastructure — Kubernetes & Cloud",
        "dirs": [
            "infrastructure",
        ],
        "description": "Kubernetes Plugin, Cloud Integration",
    },
    "monitoring": {
        "label": "Monitoring — Observability",
        "dirs": [
            "monitoring",
        ],
        "description": "Prometheus, Grafana, Health Status",
    },
    "architecture": {
        "label": "Architecture — Dependency Visualization",
        "dirs": [
            "architecture",
        ],
        "description": "Quan hệ phụ thuộc giữa services",
    },
    "security": {
        "label": "Security — Permission & Auth",
        "dirs": [
            "security",
        ],
        "description": "Permission Framework, Authentication",
    },
    "collaboration": {
        "label": "Collaboration — Team Ownership",
        "dirs": [
            "collaboration",
        ],
        "description": "Team, User, Developer Portal",
    },
    "extensibility": {
        "label": "Extensibility — Plugins",
        "dirs": [
            "extensibility",
        ],
        "description": "Plugin Architecture, Custom Plugins",
    },
    "governance": {
        "label": "Governance — Standards & Compliance",
        "dirs": [
            "governance/software-standards",
            "governance/compliance-tracking",
        ],
        "description": "Software Standards, Compliance Tracking",
    },
    "developer-experience": {
        "label": "Developer Experience — Self-Service",
        "dirs": [
            "developer-experience",
        ],
        "description": "Self-Service Platform, Centralized View",
    },
    "search": {
        "label": "Search — Global Search",
        "dirs": [
            "search",
        ],
        "description": "Tìm kiếm toàn hệ thống",
    },
}

# File lưu danh sách gist IDs đã tạo (để cleanup sau)
GIST_REGISTRY_FILE = SCRIPTS_DIR / ".gist_registry.json"


# ------------------------------------------------------------------ #
# YAML helpers
# ------------------------------------------------------------------ #


def load_entities_from_file(path: Path) -> list[dict]:
    """Đọc tất cả Backstage entities từ file YAML."""
    try:
        with open(path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        return [
            d
            for d in docs
            if isinstance(d, dict)
            and d.get("apiVersion", "").startswith("backstage.io/")
            and "kind" in d
            and "metadata" in d
            and "name" in d.get("metadata", {})
        ]
    except yaml.YAMLError as e:
        logger.error("YAML error in %s: %s", path, e)
        return []
    except Exception as e:
        logger.error("Cannot read %s: %s", path, e)
        return []


def entity_to_ref(entity: dict) -> str:
    """Tạo entity ref string."""
    kind = entity.get("kind", "unknown").lower()
    ns = entity.get("metadata", {}).get("namespace", "default")
    name = entity.get("metadata", {}).get("name", "unknown")
    return f"{kind}:{ns}/{name}"


# ------------------------------------------------------------------ #
# GitHub Gist Manager
# ------------------------------------------------------------------ #


class GistManager:
    """
    Upload YAML files lên GitHub Gist (private) và trả về raw URL.

    GitHub Gist raw URLs là public-accessible URLs mà Backstage server
    có thể download, cho phép seed dữ liệu từ local lên remote server.

    Gist được tạo ở chế độ secret (không public, không xuất hiện trên profile)
    nhưng raw URL vẫn accessible với bất kỳ ai có URL.
    """

    GITHUB_API = "https://api.github.com"

    def __init__(self, github_token: str):
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN is required for github-gist mode.\n"
                "Add GITHUB_TOKEN=<your-token> to seed/scripts/.env"
            )
        self.token = github_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }
        )
        # Cache: file_path_str → raw_url
        self._cache: dict[str, str] = {}
        # Load gist registry từ disk
        self._registry: list[dict] = self._load_registry()

    def _load_registry(self) -> list[dict]:
        if GIST_REGISTRY_FILE.exists():
            try:
                with open(GIST_REGISTRY_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_registry(self) -> None:
        with open(GIST_REGISTRY_FILE, "w") as f:
            json.dump(self._registry, f, indent=2)

    def upload_yaml(self, file_path: Path) -> str:
        """
        Upload một file YAML lên GitHub Gist.

        Mỗi file YAML được đóng gói trong một Gist riêng với tên file gốc.
        Trả về raw URL của file trong Gist.

        Nếu đã upload rồi (trong session này), trả về URL từ cache.
        """
        cache_key = str(file_path.resolve())
        if cache_key in self._cache:
            logger.debug("Using cached Gist URL for: %s", file_path.name)
            return self._cache[cache_key]

        content = file_path.read_text(encoding="utf-8")
        filename = file_path.name

        payload = {
            "description": f"Backstage seed data — {file_path.parent.name}/{filename}",
            "public": False,  # Secret gist (URL accessible nhưng không hiển thị profile)
            "files": {
                filename: {"content": content}
            },
        }

        try:
            resp = self.session.post(
                f"{self.GITHUB_API}/gists",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            gist = resp.json()

            gist_id = gist["id"]
            # Raw URL format: https://gist.githubusercontent.com/<user>/<gist_id>/raw/<filename>
            raw_url = gist["files"][filename]["raw_url"]

            logger.debug("Uploaded to Gist: %s → %s", filename, gist_id[:8])

            # Lưu vào cache và registry
            self._cache[cache_key] = raw_url
            self._registry.append(
                {
                    "gist_id": gist_id,
                    "filename": filename,
                    "source_path": cache_key,
                    "raw_url": raw_url,
                }
            )
            self._save_registry()

            return raw_url

        except requests.HTTPError as e:
            error_body = ""
            try:
                error_body = e.response.json().get("message", "")
            except Exception:
                pass
            raise RuntimeError(
                f"Failed to upload {filename} to GitHub Gist: "
                f"HTTP {e.response.status_code} — {error_body}"
            ) from e

    def delete_all_registered_gists(self) -> int:
        """Xóa tất cả Gists đã được tạo bởi seed scripts."""
        if not self._registry:
            logger.info("No registered Gists to delete.")
            return 0

        deleted = 0
        for entry in self._registry:
            gist_id = entry.get("gist_id", "")
            if not gist_id:
                continue
            try:
                resp = self.session.delete(
                    f"{self.GITHUB_API}/gists/{gist_id}",
                    timeout=15,
                )
                if resp.status_code in (204, 404):
                    logger.info("  🗑  Deleted Gist: %s (%s)", gist_id[:8], entry.get("filename"))
                    deleted += 1
                else:
                    logger.warning("  ⚠️  Could not delete Gist %s: HTTP %d", gist_id[:8], resp.status_code)
            except Exception as e:
                logger.error("  ❌ Error deleting Gist %s: %s", gist_id[:8], e)

        # Xóa registry file
        if GIST_REGISTRY_FILE.exists():
            GIST_REGISTRY_FILE.unlink()
            self._registry = []

        return deleted

    @staticmethod
    def build_raw_github_url(base_url: str, data_dir: Path, file_path: Path) -> str:
        """
        Tạo raw.githubusercontent.com URL cho mode 'github-raw'.

        base_url: "https://raw.githubusercontent.com/vnp-community/backstage/main"
        """
        rel_path = file_path.relative_to(data_dir.parent.parent)
        return f"{base_url.rstrip('/')}/{rel_path}"


# ------------------------------------------------------------------ #
# Seed mode detection
# ------------------------------------------------------------------ #


def detect_seed_mode(base_url: str, github_token: str) -> str:
    """
    Tự động chọn seed mode phù hợp:
    - localhost → file
    - remote + no token → error
    - remote + token → github-gist
    """
    is_local = any(
        x in base_url
        for x in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    )
    if is_local:
        return "file"
    if github_token:
        return "github-gist"
    return "file"  # sẽ fail ở remote, nhưng log warning


# ------------------------------------------------------------------ #
# Entity Seeder
# ------------------------------------------------------------------ #


class EntitySeeder:
    """
    Seed Backstage entities từ feature-organized YAML files.

    Hỗ trợ 3 modes:
    - file: Register file:// locations (local server only)
    - github-raw: Register raw.githubusercontent.com URLs
    - github-gist: Upload to GitHub Gist → register Gist raw URLs
    """

    REGISTER_ORDER = [
        "Domain",
        "Group",
        "User",
        "System",
        "Resource",
        "Component",
        "API",
        "Template",
        "Location",
    ]

    def __init__(
        self,
        client: BackstageClient,
        data_dir: Path,
        dry_run: bool = False,
        seed_mode: str = "auto",
        github_token: str = "",
        github_raw_base: str = "",
    ):
        self.client = client
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.github_token = github_token
        self.github_raw_base = github_raw_base
        self.report = SeedReport()

        # Resolve seed mode
        if seed_mode == "auto":
            self.mode = detect_seed_mode(client.config.base_url, github_token)
        else:
            self.mode = seed_mode

        # Khởi tạo GistManager nếu cần
        self.gist_manager: Optional[GistManager] = None
        if self.mode == "github-gist" and not dry_run:
            self.gist_manager = GistManager(github_token)

        logger.info("   Seed mode: %s", self.mode.upper())

    def _get_location_url(self, file_path: Path) -> tuple[str, str]:
        """
        Tạo location type + target URL tùy theo mode.

        Returns:
            (loc_type, target) — vd: ("url", "https://gist.githubusercontent.com/...")
        """
        if self.mode == "file":
            return "file", str(file_path.resolve())

        if self.mode == "github-raw":
            url = GistManager.build_raw_github_url(
                self.github_raw_base, self.data_dir, file_path
            )
            return "url", url

        if self.mode == "github-gist":
            if self.gist_manager:
                url = self.gist_manager.upload_yaml(file_path)
                return "url", url
            # dry-run mode: trả về placeholder URL
            return "url", f"https://gist.githubusercontent.com/placeholder/{file_path.name}"

        raise ValueError(f"Unknown seed mode: {self.mode}")

    def _register_entity_file(self, file_path: Path) -> None:
        """
        Đăng ký các entities trong một file YAML.
        Tự động chọn location type phù hợp với seed mode.
        """
        entities = load_entities_from_file(file_path)
        if not entities:
            return

        logger.debug(
            "  File: %s — %d entities",
            file_path.name,
            len(entities),
        )

        if self.dry_run:
            for entity in entities:
                self.report.add(
                    SeedResult(
                        name=entity.get("metadata", {}).get("name", "?"),
                        kind=entity.get("kind", "?"),
                        success=True,
                        action="dry-run",
                        message=f"Would register [{self.mode}] {file_path.name}",
                        entity_ref=entity_to_ref(entity),
                    )
                )
            return

        # Lấy location URL theo mode
        try:
            loc_type, target = self._get_location_url(file_path)
        except Exception as e:
            for entity in entities:
                self.report.add(
                    SeedResult(
                        name=entity.get("metadata", {}).get("name", "?"),
                        kind=entity.get("kind", "?"),
                        success=False,
                        action="error",
                        message=f"Failed to get URL: {e}",
                        entity_ref=entity_to_ref(entity),
                    )
                )
            return

        # Đăng ký Location với Backstage
        try:
            result = self.client.register_location(loc_type, target)
            time.sleep(self.client.config.request_delay)

            is_existing = result.get("exists", False)
            loc_id = result.get("location", {}).get("id", "")

            for entity in entities:
                action = "skipped" if is_existing else "created"
                if is_existing:
                    msg = "Location already registered"
                elif self.mode == "github-gist":
                    msg = f"Gist uploaded → Location registered"
                else:
                    msg = f"Location registered" + (f" (id: {loc_id[:8]}...)" if loc_id else "")

                self.report.add(
                    SeedResult(
                        name=entity.get("metadata", {}).get("name", "?"),
                        kind=entity.get("kind", "?"),
                        success=True,
                        action=action,
                        message=msg,
                        entity_ref=entity_to_ref(entity),
                    )
                )

        except BackstageAPIError as e:
            for entity in entities:
                self.report.add(
                    SeedResult(
                        name=entity.get("metadata", {}).get("name", "?"),
                        kind=entity.get("kind", "?"),
                        success=False,
                        action="error",
                        message=str(e),
                        entity_ref=entity_to_ref(entity),
                    )
                )

    def _seed_feature_dir(self, subdir: str) -> None:
        """Seed tất cả entities trong một feature directory."""
        dir_path = self.data_dir / subdir
        if not dir_path.exists():
            logger.debug("  Directory does not exist: %s", dir_path)
            return

        yaml_files = sorted(
            p
            for p in dir_path.rglob("*.yaml")
            if not p.name.startswith(".")
            and p.name != "mkdocs.yml"
        )

        if not yaml_files:
            logger.debug("  No YAML files in: %s", subdir)
            return

        logger.info("  📂 %s: %d files", subdir, len(yaml_files))

        # Ưu tiên catalog-info.yaml (Location aggregator) trước
        location_files = [f for f in yaml_files if f.name == "catalog-info.yaml"]
        other_files = [f for f in yaml_files if f.name != "catalog-info.yaml"]

        # Phân loại other files theo kind để seed đúng thứ tự
        kind_ordered_files: list[Path] = []
        classified: set[Path] = set()
        for kind in self.REGISTER_ORDER:
            for f in other_files:
                if f in classified:
                    continue
                entities = load_entities_from_file(f)
                if any(e.get("kind") == kind for e in entities):
                    kind_ordered_files.append(f)
                    classified.add(f)

        for f in other_files:
            if f not in classified:
                kind_ordered_files.append(f)

        # Seed location files trước, rồi entity files
        for f in location_files:
            self._register_entity_file(f)
        for f in kind_ordered_files:
            self._register_entity_file(f)

    def seed_feature(self, feature: str) -> SeedReport:
        """Seed một feature cụ thể."""
        feature_config = FEATURE_MAP.get(feature)
        if not feature_config:
            logger.error("Unknown feature: '%s'", feature)
            return self.report

        logger.info("\n🏷  %s", feature_config["label"])
        logger.info("    %s", feature_config["description"])

        for subdir in feature_config["dirs"]:
            self._seed_feature_dir(subdir)

        return self.report

    def seed_all(self) -> SeedReport:
        """Seed tất cả features."""
        mode = "DRY-RUN" if self.dry_run else f"LIVE [{self.mode.upper()}]"
        logger.info("=" * 60)
        logger.info("🚀 Seeding all %d features [%s]", len(FEATURE_MAP), mode)
        logger.info("   Server: %s", self.client.config.base_url)
        logger.info("   Data:   %s", self.data_dir)
        logger.info("=" * 60)

        for feature in FEATURE_MAP:
            self.seed_feature(feature)

        return self.report

    def show_status(self) -> None:
        """Hiển thị trạng thái catalog hiện tại."""
        logger.info("\n📊 Current Catalog Status")
        logger.info("=" * 40)

        kinds = ["Domain", "Group", "User", "System", "Component", "API", "Resource", "Template"]
        grand_total = 0

        for kind in kinds:
            try:
                result = self.client.list_entities(kind=kind, limit=500)
                items = result.get("items", [])
                count = len(items)
                grand_total += count

                if count > 0:
                    logger.info("  %-12s: %3d entities", kind, count)
                    for item in items[:3]:
                        meta = item.get("metadata", {})
                        spec = item.get("spec", {})
                        name = meta.get("name", "?")
                        ns = meta.get("namespace", "default")
                        owner = spec.get("owner", "-")
                        logger.info("    • %s/%s (owner: %s)", ns, name, owner)
                    if count > 3:
                        logger.info("    ... và %d nữa", count - 3)
                else:
                    logger.info("  %-12s: (empty)", kind)

            except BackstageAPIError as e:
                logger.warning("  %-12s: ERROR — %s", kind, e)

        logger.info("─" * 40)
        logger.info("  %-12s: %3d entities total", "TOTAL", grand_total)

        try:
            locations = self.client.list_locations()
            logger.info("\n📍 Registered Locations: %d", len(locations))
            for loc in locations[:5]:
                loc_type = loc.get("type", "?")
                target = loc.get("target", "?")
                logger.info("  [%s] %s", loc_type, target[-70:] if len(target) > 70 else target)
            if len(locations) > 5:
                logger.info("  ... và %d nữa", len(locations) - 5)
        except BackstageAPIError as e:
            logger.warning("Cannot list locations: %s", e)

    def cleanup_gists(self) -> None:
        """Xóa tất cả GitHub Gists đã tạo bởi seed scripts."""
        logger.info("🗑  Cleaning up GitHub Gists...")
        try:
            gm = GistManager(self.github_token)
            deleted = gm.delete_all_registered_gists()
            logger.info("✅ Deleted %d Gists", deleted)
        except ValueError as e:
            logger.error("Cannot cleanup Gists: %s", e)


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Backstage entities theo feature groups (features.md)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Seed modes:
  auto         — Tự động chọn (file cho localhost, github-gist cho remote)
  file         — file:// paths (chỉ với local Backstage)
  github-gist  — Upload YAML lên GitHub Gist → register URL (cần GITHUB_TOKEN)
  github-raw   — raw.githubusercontent.com URLs (cần GITHUB_RAW_BASE_URL)

Feature groups:
  service-catalog, apis, documentation, software-templates, ci-cd,
  infrastructure, monitoring, architecture, security, collaboration,
  extensibility, governance, developer-experience, search

Examples:
  python seed_entities.py                          # Seed tất cả (auto mode)
  python seed_entities.py --feature service-catalog
  python seed_entities.py --feature apis --dry-run
  python seed_entities.py --status
  python seed_entities.py --cleanup-gists          # Xóa Gists đã tạo
        """,
    )
    parser.add_argument(
        "--feature",
        choices=list(FEATURE_MAP.keys()),
        help="Chỉ seed một feature cụ thể",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "file", "github-gist", "github-raw"],
        default="auto",
        help="Seed mode (default: auto)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mà không seed thật",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Hiển thị trạng thái catalog hiện tại",
    )
    parser.add_argument(
        "--cleanup-gists",
        action="store_true",
        help="Xóa tất cả GitHub Gists đã tạo bởi seed scripts",
    )
    parser.add_argument(
        "--no-healthcheck",
        action="store_true",
        help="Bỏ qua health check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config, data_dir = init()

    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_raw_base = os.environ.get("GITHUB_RAW_BASE_URL", "")

    client = BackstageClient(config)

    if not args.no_healthcheck:
        if not client.health_check():
            logger.error("❌ Cannot connect to Backstage. Aborting.")
            return 1

    seeder = EntitySeeder(
        client,
        data_dir,
        dry_run=args.dry_run,
        seed_mode=args.mode,
        github_token=github_token,
        github_raw_base=github_raw_base,
    )

    if args.status:
        seeder.show_status()
        return 0

    if args.cleanup_gists:
        seeder.cleanup_gists()
        return 0

    if args.feature:
        report = seeder.seed_feature(args.feature)
    else:
        report = seeder.seed_all()

    report.print_summary()
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
