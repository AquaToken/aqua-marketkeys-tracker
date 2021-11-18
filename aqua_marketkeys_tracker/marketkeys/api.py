from typing import Optional

from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny

from stellar_sdk import Asset

from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.marketkeys.pagination import MarketKeyCursorPagination
from aqua_marketkeys_tracker.marketkeys.pair import MarketPair
from aqua_marketkeys_tracker.marketkeys.serializers import MarketKeySerializer
from aqua_marketkeys_tracker.utils.drf.filters import MultiGetFilterBackend
from aqua_marketkeys_tracker.utils.stellar.urls import AssetStringConverter


class BaseMarketKeyView(GenericAPIView):
    queryset = MarketKey.objects.filter_active()
    serializer_class = MarketKeySerializer
    permission_classes = (AllowAny, )
    pagination_class = MarketKeyCursorPagination


class RetrieveMarketKeyView(RetrieveModelMixin, BaseMarketKeyView):
    def get_object(self):
        asset1 = self.kwargs['asset1']
        asset2 = self.kwargs['asset2']

        try:
            market_pair = MarketPair(asset1, asset2)
        except ValueError as exc:
            raise Http404(str(exc))

        obj = get_object_or_404(self.filter_queryset(self.get_queryset()).filter_for_market_pair(market_pair))

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


# TODO: Move this view to filter backend?
class SearchMarketKeyView(ListModelMixin, BaseMarketKeyView):
    SEARCH_PARAM_NAME = 'asset'

    def get_search_param(self) -> Optional[Asset]:
        try:
            return AssetStringConverter().to_python(self.request.query_params.get(self.SEARCH_PARAM_NAME, ''))
        except ValueError:
            return None

    def get_queryset(self):
        search_asset = self.get_search_param()
        queryset = super(SearchMarketKeyView, self).get_queryset()

        if not search_asset:
            return queryset.none()

        return queryset.filter_for_asset(search_asset)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ListMarketKeyView(ListModelMixin, BaseMarketKeyView):
    filter_backends = [MultiGetFilterBackend]
    multiget_filter_fields = ['account_id']

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
