"""
backstage_client.py — Backstage API Client

Client giao tiếp với Backstage Catalog REST API.
Hỗ trợ:
  - Đăng ký Location (trỏ đến file YAML)
  - Query và list entities
  - Refresh entities
  - Validate entities
  - Health check

Docs:
  https://backstage.io/docs/features/software-catalog/software-catalog-api
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class BackstageConfig:
    """Cấu hình kết nối đến Backstage server."""

    base_url: str
    token: str = ""
    max_retries: int = 3
    request_delay: float = 0.2
    timeout: int = 30

    def catalog_url(self, path: str = "") -> str:
        """Tạo URL đầy đủ đến Catalog API."""
        base = self.base_url.rstrip("/")
        return f"{base}/api/catalog{path}"


@dataclass
class SeedResult:
    """Kết quả seed cho một entity/location."""

    name: str
    kind: str
    success: bool
    action: str = ""      # created, skipped, error
    message: str = ""
    entity_ref: str = ""


@dataclass
class SeedReport:
    """Báo cáo tổng kết quá trình seed."""

    results: list[SeedResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def add(self, result: SeedResult) -> None:
        self.results.append(result)
        icon = "✅" if result.success else "❌"
        logger.info(
            "%s [%s] %s — %s",
            icon,
            result.kind.upper(),
            result.name,
            result.message,
        )

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print(f"SEED SUMMARY: {self.succeeded}/{self.total} succeeded")
        print("=" * 60)
        failures = [r for r in self.results if not r.success]
        if failures:
            print("\nFailed:")
            for r in failures:
                print(f"  ❌ [{r.kind}] {r.name}: {r.message}")
        print()


class BackstageAPIError(Exception):
    """Lỗi từ Backstage API."""

    def __init__(self, status_code: int, message: str, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


class BackstageClient:
    """
    Client để giao tiếp với Backstage Catalog REST API.

    Sử dụng:
        config = BackstageConfig(base_url="https://backstage.example.com", token="...")
        client = BackstageClient(config)

        # Đăng ký location
        client.register_location("url", "https://github.com/.../catalog-info.yaml")

        # List entities
        entities = client.list_entities(kind="Component")
    """

    def __init__(self, config: BackstageConfig):
        self.config = config
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Tạo requests session với retry và headers."""
        session = requests.Session()

        # Retry strategy
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers
        session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        # Auth token
        if self.config.token:
            session.headers["Authorization"] = f"Bearer {self.config.token}"

        return session

    def _request(
        self,
        method: str,
        url: str,
        *,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        """Thực hiện HTTP request và xử lý lỗi."""
        try:
            logger.debug("%s %s", method.upper(), url)
            resp = self.session.request(
                method,
                url,
                json=json,
                params=params,
                timeout=self.config.timeout,
            )

            if resp.status_code in (200, 201):
                return resp.json() if resp.content else {}

            if resp.status_code == 204:
                return {}

            # Lỗi từ server
            try:
                error_body = resp.json()
                error_msg = error_body.get("error", {}).get(
                    "message", resp.text[:200]
                )
            except Exception:
                error_msg = resp.text[:200]

            raise BackstageAPIError(resp.status_code, error_msg, resp.text)

        except requests.exceptions.ConnectionError as e:
            raise BackstageAPIError(0, f"Connection error: {e}") from e
        except requests.exceptions.Timeout as e:
            raise BackstageAPIError(0, f"Request timeout: {e}") from e

    def health_check(self) -> bool:
        """Kiểm tra kết nối đến Backstage server."""
        try:
            url = self.config.base_url.rstrip("/") + "/healthcheck"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                logger.info("✅ Backstage server reachable at %s", self.config.base_url)
                return True
            # Thử catalog API
            entities = self.list_entities(limit=1)
            logger.info(
                "✅ Backstage Catalog API reachable (%d entities found)",
                len(entities.get("items", [])),
            )
            return True
        except Exception as e:
            logger.error("❌ Cannot reach Backstage at %s: %s", self.config.base_url, e)
            return False

    # ------------------------------------------------------------------ #
    # Location API
    # ------------------------------------------------------------------ #

    def register_location(
        self, loc_type: str, target: str, dry_run: bool = False
    ) -> dict:
        """
        Đăng ký một Location vào Backstage Catalog.

        Args:
            loc_type: Loại location — "url" hoặc "file"
            target: URL hoặc đường dẫn file
            dry_run: Nếu True, chỉ analyze mà không thực sự đăng ký

        Returns:
            Location object từ API
        """
        if dry_run:
            # Analyze trước để validate
            return self.analyze_location(loc_type, target)

        url = self.config.catalog_url("/locations")
        payload = {"type": loc_type, "target": target}
        logger.debug("Registering location: %s %s", loc_type, target)

        try:
            result = self._request("POST", url, json=payload)
            time.sleep(self.config.request_delay)
            return result
        except BackstageAPIError as e:
            if e.status_code == 409:
                # Location đã tồn tại — không phải lỗi nghiêm trọng
                logger.debug("Location already exists: %s", target)
                return {"exists": True, "target": target}
            raise

    def list_locations(self) -> list[dict]:
        """Lấy danh sách tất cả locations đã đăng ký."""
        url = self.config.catalog_url("/locations")
        result = self._request("GET", url)
        return result if isinstance(result, list) else []

    def delete_location(self, location_id: str) -> None:
        """Xóa location theo ID."""
        url = self.config.catalog_url(f"/locations/{location_id}")
        self._request("DELETE", url)
        logger.info("Deleted location: %s", location_id)

    def analyze_location(self, loc_type: str, target: str) -> dict:
        """
        Phân tích location mà không thực sự đăng ký (dry-run mode).
        Kiểm tra xem location có hợp lệ và entities nào sẽ được tạo.
        """
        url = self.config.catalog_url("/analyze-location")
        payload = {
            "location": {"type": loc_type, "target": target},
            "catalogFilename": "catalog-info.yaml",
        }
        return self._request("POST", url, json=payload)

    # ------------------------------------------------------------------ #
    # Entity API
    # ------------------------------------------------------------------ #

    def list_entities(
        self,
        kind: Optional[str] = None,
        namespace: str = "default",
        limit: int = 100,
        filter_str: Optional[str] = None,
    ) -> dict:
        """
        Lấy danh sách entities với optional filter.

        Args:
            kind: Filter theo Kind (Component, API, System, ...)
            namespace: Filter theo namespace
            limit: Số entities tối đa mỗi trang
            filter_str: Filter string theo Backstage format
                        (vd: "kind=Component,spec.type=service")

        Returns:
            Dict với "items" là danh sách entities
        """
        url = self.config.catalog_url("/entities/by-query")
        filters = []

        if kind:
            filters.append(f"kind={kind}")
        if filter_str:
            filters.append(filter_str)

        params: dict = {"limit": limit}
        if filters:
            params["filter"] = ",".join(filters)

        return self._request("GET", url, params=params)

    def get_entity(self, kind: str, namespace: str, name: str) -> Optional[dict]:
        """Lấy entity cụ thể theo kind/namespace/name."""
        url = self.config.catalog_url(f"/entities/by-name/{kind}/{namespace}/{name}")
        try:
            return self._request("GET", url)
        except BackstageAPIError as e:
            if e.status_code == 404:
                return None
            raise

    def get_entity_by_uid(self, uid: str) -> Optional[dict]:
        """Lấy entity theo UID."""
        url = self.config.catalog_url(f"/entities/by-uid/{uid}")
        try:
            return self._request("GET", url)
        except BackstageAPIError as e:
            if e.status_code == 404:
                return None
            raise

    def delete_entity(self, uid: str) -> None:
        """Xóa entity theo UID."""
        url = self.config.catalog_url(f"/entities/by-uid/{uid}")
        self._request("DELETE", url)

    def refresh_entity(self, entity_ref: str) -> None:
        """
        Trigger refresh cho một entity.

        Args:
            entity_ref: Entity ref dạng "kind:namespace/name"
                        (vd: "component:default/payment-service")
        """
        url = self.config.catalog_url("/refresh")
        self._request("POST", url, json={"entityRef": entity_ref})
        logger.debug("Refreshed entity: %s", entity_ref)

    def validate_entity(self, entity: dict) -> dict:
        """
        Validate entity data trước khi đăng ký.

        Returns:
            Dict với "valid": bool và "errors": list
        """
        url = self.config.catalog_url("/validate-entity")
        return self._request("POST", url, json=entity)

    def get_facets(self, facets: list[str], filter_str: Optional[str] = None) -> dict:
        """
        Lấy facets (aggregated metadata) của catalog.

        Args:
            facets: Danh sách facet fields (vd: ["kind", "spec.type", "metadata.tags"])
            filter_str: Optional filter

        Returns:
            Dict với "facets" là aggregated results
        """
        url = self.config.catalog_url("/entity-facets")
        params: dict = {"facet": facets}
        if filter_str:
            params["filter"] = filter_str
        return self._request("GET", url, params=params)
