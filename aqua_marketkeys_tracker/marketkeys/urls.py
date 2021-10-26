from django.urls import path

from aqua_marketkeys_tracker.marketkeys.api import ListMarketKeyView, RetrieveMarketKeyView, SearchMarketKeyView


urlpatterns = [
    path('market-keys/<asset_string:asset1>-<asset_string:asset2>/', RetrieveMarketKeyView.as_view()),
    path('market-keys/search/', SearchMarketKeyView.as_view()),
    path('market-keys/', ListMarketKeyView.as_view()),
]
