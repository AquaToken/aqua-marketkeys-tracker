import logging
import os
from types import SimpleNamespace

import django
from django.db.models import Q


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from aqua_marketkeys_tracker.marketkeys.loaders import asset_registry  # noqa: E402


MAX_PAGES = 50


class FakeResponse:
    ok = True
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FailingAssetManager:
    def filter(self, *args, **kwargs):
        raise AssertionError("Asset registry sync mutated the database")


class RecordingAssetManager:
    def __init__(self):
        self.calls = []

    def filter(self, *args, **kwargs):
        self.calls.append(("manager.filter", args, kwargs))
        return RecordingQuerySet(self.calls)


class RecordingQuerySet:
    def __init__(self, calls):
        self.calls = calls

    def filter(self, *args, **kwargs):
        self.calls.append(("queryset.filter", args, kwargs))
        return self

    def exclude(self, *args, **kwargs):
        self.calls.append(("queryset.exclude", args, kwargs))
        return self

    def update(self, *args, **kwargs):
        self.calls.append(("queryset.update", args, kwargs))
        return 1


def test_run_aborts_without_db_mutation_when_pagination_exceeds_max_pages(
    monkeypatch,
    caplog,
):
    next_url = (
        "https://governance-api.aqua.network/api/asset-tokens/?whitelisted=true&page=1"
    )
    requests_made = []

    def fake_get(url, **kwargs):
        requests_made.append((url, kwargs))
        if len(requests_made) > MAX_PAGES:
            raise AssertionError("pagination did not abort after MAX_PAGES pages")
        return FakeResponse(
            {
                "results": [
                    {
                        "asset_code": "USDC",
                        "asset_issuer": "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN",
                        "whitelisted": True,
                    },
                ],
                "next": next_url,
            }
        )

    monkeypatch.setattr(asset_registry.requests, "get", fake_get)
    monkeypatch.setattr(
        asset_registry,
        "Asset",
        SimpleNamespace(objects=FailingAssetManager()),
    )
    caplog.set_level(logging.WARNING, logger=asset_registry.__name__)

    asset_registry.AssetRegistryLoader().run()

    assert len(requests_made) == MAX_PAGES
    assert asset_registry.AssetRegistryLoader.MAX_PAGES == MAX_PAGES
    assert (
        "Asset registry sync aborted: pagination exceeded MAX_PAGES=50 "
        "(suspected upstream loop)"
    ) in caplog.text


def test_run_processes_legitimate_paginated_response(monkeypatch):
    next_url = (
        "https://governance-api.aqua.network/api/asset-tokens/?whitelisted=true&page=2"
    )
    requests_made = []
    manager = RecordingAssetManager()

    def fake_get(url, **kwargs):
        requests_made.append((url, kwargs))
        if len(requests_made) == 1:
            return FakeResponse(
                {
                    "results": [
                        {
                            "asset_code": "PYUSD",
                            "asset_issuer": "GDQE7IXJKSH7G5MGGK3GBC4PFK2JBL5YSA3H3CY4JWOE6JZXNJHCU2W6",
                            "whitelisted": True,
                        },
                        {
                            "asset_code": "BAD",
                            "asset_issuer": "GBADISSUER",
                            "whitelisted": False,
                        },
                    ],
                    "next": next_url,
                }
            )
        return FakeResponse(
            {
                "results": [
                    {
                        "asset_code": "XLM",
                        "asset_issuer": None,
                        "whitelisted": True,
                    },
                ],
                "next": None,
            }
        )

    monkeypatch.setattr(asset_registry.requests, "get", fake_get)
    monkeypatch.setattr(
        asset_registry,
        "Asset",
        SimpleNamespace(objects=manager),
    )

    asset_registry.AssetRegistryLoader().run()

    assert len(requests_made) == 2
    assert requests_made[0][1]["params"] == {"whitelisted": "true"}
    assert "params" not in requests_made[1][1]
    assert [call[0] for call in manager.calls] == [
        "manager.filter",
        "queryset.filter",
        "queryset.update",
        "manager.filter",
        "queryset.exclude",
        "queryset.update",
    ]
    assert manager.calls[0][2] == {"in_asset_registry": False}
    assert manager.calls[1][1] and isinstance(manager.calls[1][1][0], Q)
    assert manager.calls[2][2] == {"in_asset_registry": True}
    assert manager.calls[3][2] == {"in_asset_registry": True}
    assert manager.calls[4][1] and isinstance(manager.calls[4][1][0], Q)
    assert manager.calls[5][2] == {"in_asset_registry": False}
