import json
import logging

import requests
from django.conf import settings
from django.db.models import Q

from aqua_marketkeys_tracker.marketkeys.models import Asset


logger = logging.getLogger(__name__)


class AssetRegistryLoader:
    def run(self):
        url = settings.GOVERNANCE_API_URL + settings.ASSET_REGISTRY_ENDPOINT
        all_results = []
        first_page = True
        next_url = url

        while next_url:
            try:
                if first_page:
                    response = requests.get(
                        next_url, params={"whitelisted": "true"}, timeout=30
                    )
                    first_page = False
                else:
                    response = requests.get(next_url, timeout=30)
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
            next_url = data.get("next")

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
