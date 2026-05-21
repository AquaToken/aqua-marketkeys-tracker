import json
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db.models import Q

from aqua_marketkeys_tracker.marketkeys.models import Asset


logger = logging.getLogger(__name__)


class AssetRegistryLoader:
    def _is_valid_next(self, raw_next, expected_base):
        if not isinstance(raw_next, str):
            return False
        parsed = urlparse(raw_next)
        base = urlparse(expected_base)
        if parsed.scheme != "https":
            return False
        if parsed.netloc != base.netloc:
            return False
        # Reject path-traversal escapes before normalization.
        if ".." in parsed.path.split("/"):
            return False
        # Exact path match (after stripping trailing slash on both sides).
        # DRF pagination's `next` URL preserves the original endpoint path verbatim,
        # so an exact match is correct and rejects all sibling-endpoint escapes.
        return parsed.path.rstrip("/") == base.path.rstrip("/")

    def run(self):
        url = settings.GOVERNANCE_API_URL + settings.ASSET_REGISTRY_ENDPOINT
        all_results = []
        first_page = True
        next_url = url

        while next_url:
            try:
                if first_page:
                    response = requests.get(
                        next_url,
                        params={"whitelisted": "true"},
                        timeout=30,
                        allow_redirects=False,
                    )
                    first_page = False
                else:
                    response = requests.get(next_url, timeout=30, allow_redirects=False)
            except requests.RequestException:
                logger.warning("Asset registry fetch failed.", exc_info=True)
                return

            if not response.ok:
                logger.warning(
                    "Asset registry returned non-2xx status: %s", response.status_code
                )
                return

            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning("Asset registry response is not valid JSON.")
                return

            if (
                not isinstance(data, dict)
                or "results" not in data
                or not isinstance(data["results"], list)
            ):
                logger.warning("Asset registry response has unexpected shape.")
                return

            for record in data["results"]:
                if (
                    not isinstance(record, dict)
                    or "asset_code" not in record
                    or "asset_issuer" not in record
                    or "whitelisted" not in record
                    or not isinstance(record["asset_code"], str)
                    or not record["asset_code"]
                    or not (
                        record["asset_issuer"] is None
                        or isinstance(record["asset_issuer"], str)
                    )
                    or not isinstance(record["whitelisted"], bool)
                ):
                    logger.warning(
                        "Asset registry record has unexpected shape: %s", record
                    )
                    return

            all_results.extend(data["results"])
            raw_next = data.get("next")
            if raw_next is None:
                next_url = None
            elif self._is_valid_next(
                raw_next,
                settings.GOVERNANCE_API_URL + settings.ASSET_REGISTRY_ENDPOINT,
            ):
                next_url = raw_next
            else:
                logger.warning(
                    "Asset registry next URL rejected (off-host or malformed): %s",
                    raw_next,
                )
                return

        desired_set = {
            (r["asset_code"], r["asset_issuer"] or "")
            for r in all_results
            if r["whitelisted"] is True
        }

        if not desired_set:
            logger.warning(
                "Asset registry desired set is empty after filtering; aborting to preserve local state."
            )
            return

        membership_q = Q()
        for code, issuer in desired_set:
            membership_q |= Q(code=code, issuer=issuer)

        added = (
            Asset.objects.filter(in_asset_registry=False)
            .filter(membership_q)
            .update(in_asset_registry=True)
        )
        removed = (
            Asset.objects.filter(in_asset_registry=True)
            .exclude(membership_q)
            .update(in_asset_registry=False)
        )

        logger.info(
            f"added={added} removed={removed} desired_set_size={len(desired_set)}"
        )
