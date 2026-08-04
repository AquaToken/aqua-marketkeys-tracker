from typing import Optional

from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny

from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.marketkeys.pagination import MarketKeyPagination
from aqua_marketkeys_tracker.marketkeys.serializers import MarketKeySerializer
from aqua_marketkeys_tracker.utils.drf.filters import MultiGetFilterBackend
from aqua_marketkeys_tracker.utils.stellar.asset import get_contract_id_for_asset_param


class BaseMarketKeyView(GenericAPIView):
    queryset = MarketKey.objects.order_by('id').filter_active().select_related('asset1', 'asset2')
    serializer_class = MarketKeySerializer
    permission_classes = (AllowAny, )
    pagination_class = MarketKeyPagination


class RetrieveMarketKeyView(RetrieveModelMixin, BaseMarketKeyView):
    def get_object(self):
        try:
            contract_id1 = get_contract_id_for_asset_param(self.kwargs['asset1'])
            contract_id2 = get_contract_id_for_asset_param(self.kwargs['asset2'])
        except ValueError as exc:
            raise Http404(str(exc))

        if contract_id1 == contract_id2:
            raise Http404('Assets in pair must be different.')

        obj = get_object_or_404(
            self.filter_queryset(self.get_queryset()).filter_for_contract_pair(contract_id1, contract_id2),
        )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


# TODO: Move this view to filter backend?
class SearchMarketKeyView(ListModelMixin, BaseMarketKeyView):
    SEARCH_PARAM_NAME = 'asset'

    def get_search_param(self) -> Optional[str]:
        try:
            return get_contract_id_for_asset_param(self.request.query_params.get(self.SEARCH_PARAM_NAME, ''))
        except ValueError:
            return None

    def get_queryset(self):
        search_contract_id = self.get_search_param()
        queryset = super(SearchMarketKeyView, self).get_queryset()

        if not search_contract_id:
            return queryset.none()

        return queryset.filter_for_contract(search_contract_id)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ListMarketKeyView(ListModelMixin, BaseMarketKeyView):
    filter_backends = [MultiGetFilterBackend]
    multiget_filter_fields = ['account_id']

    def get_queryset(self):
        queryset = super(ListMarketKeyView, self).get_queryset()

        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
