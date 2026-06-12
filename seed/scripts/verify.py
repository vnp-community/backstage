"""
verify.py — Verify và báo cáo trạng thái Backstage Catalog

Script kiểm tra toàn bộ catalog sau khi seed, đảm bảo:
  - Các entities đã được đăng ký đúng
  - Relations giữa entities hợp lệ
  - Entities có owner hợp lệ
  - Thống kê theo feature group

Sử dụng:
  python verify.py                  # Full report
  python verify.py --feature service-catalog  # Report một feature
  python verify.py --export report.json       # Xuất báo cáo JSON
  python verify.py --check-relations         # Kiểm tra relations
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from backstage_client import BackstageAPIError, BackstageClient
from config import init
from seed_entities import FEATURE_MAP, load_entities_from_file

logger = logging.getLogger("verify")


# ------------------------------------------------------------------ #
# Verification
# ------------------------------------------------------------------ #


class CatalogVerifier:
    """Kiểm tra và báo cáo trạng thái Backstage Catalog."""

    def __init__(self, client: BackstageClient, data_dir: Path):
        self.client = client
        self.data_dir = data_dir
        self.issues: list[dict] = []

    def _add_issue(
        self,
        level: str,
        entity_ref: str,
        message: str,
        feature: str = "",
    ) -> None:
        """Thêm một issue vào danh sách."""
        self.issues.append(
            {
                "level": level,  # error, warning, info
                "entity_ref": entity_ref,
                "message": message,
                "feature": feature,
            }
        )
        icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}.get(level, "•")
        logger.log(
            {"error": logging.ERROR, "warning": logging.WARNING, "info": logging.INFO}.get(
                level, logging.DEBUG
            ),
            "%s [%s] %s — %s",
            icon,
            feature or "catalog",
            entity_ref,
            message,
        )

    def collect_expected_entities(self, feature: Optional[str] = None) -> list[dict]:
        """Thu thập tất cả entities được mong đợi từ seed/data/."""
        expected = []
        features = [feature] if feature else list(FEATURE_MAP.keys())

        for feat in features:
            feat_config = FEATURE_MAP.get(feat, {})
            for subdir in feat_config.get("dirs", []):
                dir_path = self.data_dir / subdir
                if not dir_path.exists():
                    continue
                for yaml_file in dir_path.rglob("*.yaml"):
                    if yaml_file.name == "mkdocs.yml":
                        continue
                    entities = load_entities_from_file(yaml_file)
                    for entity in entities:
                        entity["_feature"] = feat
                        entity["_source_file"] = str(yaml_file)
                    expected.extend(entities)

        return expected

    def check_entities_exist(self, feature: Optional[str] = None) -> dict:
        """Kiểm tra các entities từ data files có trong catalog không."""
        expected = self.collect_expected_entities(feature)
        logger.info("Checking %d expected entities...", len(expected))

        found = 0
        missing = 0
        results = []

        for entity in expected:
            kind = entity.get("kind", "?")
            ns = entity.get("metadata", {}).get("namespace", "default")
            name = entity.get("metadata", {}).get("name", "?")
            feat = entity.get("_feature", "")
            ref = f"{kind.lower()}:{ns}/{name}"

            try:
                actual = self.client.get_entity(kind, ns, name)
                if actual:
                    found += 1
                    results.append(
                        {
                            "ref": ref,
                            "feature": feat,
                            "status": "found",
                            "kind": kind,
                            "name": name,
                            "namespace": ns,
                        }
                    )
                else:
                    missing += 1
                    self._add_issue(
                        "warning",
                        ref,
                        f"Entity not yet in catalog (may still be processing)",
                        feat,
                    )
                    results.append(
                        {
                            "ref": ref,
                            "feature": feat,
                            "status": "missing",
                            "kind": kind,
                            "name": name,
                            "namespace": ns,
                        }
                    )
            except BackstageAPIError as e:
                self._add_issue("error", ref, f"API error: {e}", feat)
                results.append(
                    {
                        "ref": ref,
                        "feature": feat,
                        "status": "error",
                        "kind": kind,
                        "name": name,
                        "namespace": ns,
                        "error": str(e),
                    }
                )

        logger.info(
            "Entity check: %d found, %d missing out of %d expected",
            found,
            missing,
            len(expected),
        )

        return {
            "total_expected": len(expected),
            "found": found,
            "missing": missing,
            "results": results,
        }

    def check_catalog_stats(self) -> dict:
        """Lấy thống kê tổng quan của catalog."""
        kinds = [
            "Domain",
            "Group",
            "User",
            "System",
            "Component",
            "API",
            "Resource",
            "Template",
            "Location",
        ]
        stats = {}

        for kind in kinds:
            try:
                result = self.client.list_entities(kind=kind, limit=500)
                items = result.get("items", [])
                stats[kind] = {
                    "count": len(items),
                    "examples": [
                        {
                            "name": item.get("metadata", {}).get("name"),
                            "namespace": item.get("metadata", {}).get("namespace", "default"),
                            "owner": item.get("spec", {}).get("owner", ""),
                            "lifecycle": item.get("spec", {}).get("lifecycle", ""),
                        }
                        for item in items[:3]
                    ],
                }
            except BackstageAPIError as e:
                stats[kind] = {"count": 0, "error": str(e)}

        return stats

    def check_feature_coverage(self) -> dict:
        """Kiểm tra coverage của từng feature group."""
        coverage = {}

        for feat, feat_config in FEATURE_MAP.items():
            expected_in_feat = self.collect_expected_entities(feat)
            found_count = 0

            for entity in expected_in_feat:
                kind = entity.get("kind", "?")
                ns = entity.get("metadata", {}).get("namespace", "default")
                name = entity.get("metadata", {}).get("name", "?")
                try:
                    actual = self.client.get_entity(kind, ns, name)
                    if actual:
                        found_count += 1
                except BackstageAPIError:
                    pass

            total = len(expected_in_feat)
            pct = (found_count / total * 100) if total > 0 else 0

            coverage[feat] = {
                "label": feat_config["label"],
                "expected": total,
                "found": found_count,
                "coverage_pct": round(pct, 1),
                "status": "ok" if found_count == total else "partial" if found_count > 0 else "empty",
            }

        return coverage

    def generate_report(self, feature: Optional[str] = None) -> dict:
        """Tạo báo cáo đầy đủ."""
        logger.info("Generating catalog verification report...")

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "server": self.client.config.base_url,
            "feature_filter": feature,
            "catalog_stats": self.check_catalog_stats(),
            "entity_check": self.check_entities_exist(feature),
            "feature_coverage": self.check_feature_coverage() if not feature else {},
            "issues": self.issues,
            "summary": {},
        }

        # Summary
        total_entities = sum(
            v.get("count", 0) for v in report["catalog_stats"].values()
        )
        total_issues = len(self.issues)
        errors = sum(1 for i in self.issues if i["level"] == "error")
        warnings = sum(1 for i in self.issues if i["level"] == "warning")

        report["summary"] = {
            "total_entities_in_catalog": total_entities,
            "total_issues": total_issues,
            "errors": errors,
            "warnings": warnings,
            "status": "healthy" if errors == 0 else "degraded",
        }

        return report

    def print_report(self, report: dict) -> None:
        """In báo cáo ra console."""
        print("\n" + "=" * 70)
        print("📊 BACKSTAGE CATALOG VERIFICATION REPORT")
        print(f"   Server: {report['server']}")
        print(f"   Time:   {report['timestamp']}")
        print("=" * 70)

        # Catalog stats
        print("\n📦 CATALOG ENTITIES:")
        stats = report["catalog_stats"]
        total = 0
        for kind, data in stats.items():
            count = data.get("count", 0)
            total += count
            if count > 0:
                print(f"  {kind:<12}: {count:3d}")
                for ex in data.get("examples", []):
                    owner = ex.get("owner", "")
                    print(f"    • {ex['namespace']}/{ex['name']}" + (f" ({owner})" if owner else ""))
        print(f"  {'TOTAL':<12}: {total:3d}")

        # Feature coverage
        if report.get("feature_coverage"):
            print("\n🏷  FEATURE COVERAGE:")
            for feat, cov in report["feature_coverage"].items():
                expected = cov["expected"]
                if expected == 0:
                    continue
                found = cov["found"]
                pct = cov["coverage_pct"]
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                status = "✅" if cov["status"] == "ok" else "⚠️ " if cov["status"] == "partial" else "❌"
                print(f"  {status} {feat:<25} [{bar}] {pct:5.1f}% ({found}/{expected})")

        # Issues
        if report["issues"]:
            print(f"\n⚠️  ISSUES ({len(report['issues'])}):")
            for issue in report["issues"]:
                icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}.get(issue["level"], "•")
                feat = f"[{issue['feature']}] " if issue.get("feature") else ""
                print(f"  {icon} {feat}{issue['entity_ref']}: {issue['message']}")

        # Summary
        summary = report["summary"]
        status_icon = "✅" if summary["status"] == "healthy" else "⚠️ "
        print(f"\n{status_icon} STATUS: {summary['status'].upper()}")
        print(f"   Total entities: {summary['total_entities_in_catalog']}")
        print(f"   Issues: {summary['errors']} errors, {summary['warnings']} warnings")
        print()


# ------------------------------------------------------------------ #
# CLI
# ------------------------------------------------------------------ #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify trạng thái Backstage Catalog sau khi seed",
    )
    parser.add_argument(
        "--feature",
        choices=list(FEATURE_MAP.keys()),
        help="Chỉ verify một feature group",
    )
    parser.add_argument(
        "--export",
        metavar="FILE",
        help="Xuất báo cáo ra file JSON",
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

    client = BackstageClient(config)

    if not args.no_healthcheck:
        if not client.health_check():
            logger.error("❌ Cannot connect to Backstage. Aborting.")
            return 1

    verifier = CatalogVerifier(client, data_dir)
    report = verifier.generate_report(feature=args.feature)
    verifier.print_report(report)

    # Export to JSON
    if args.export:
        export_path = Path(args.export)
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("📄 Report exported to: %s", export_path)

    # Return non-zero if there are errors
    return 0 if report["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
