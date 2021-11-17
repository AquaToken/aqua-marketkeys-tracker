from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class MarketKeyCursorPagination(CursorPagination):
    ordering = 'locked_at'
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 200

    def get_page_size(self, request):
        # Use max page size for multi get filter.
        # Dirty hack. But alternative is copy-paste 70-lines function to put view into arguments.
        if 'account_id' in request.query_params:
            return self.max_page_size

        return super(MarketKeyCursorPagination, self).get_page_size(request)

    def get_count(self, queryset):
        """
        Determine an object count, supporting either querysets or regular lists.
        """
        try:
            return queryset.count()
        except (AttributeError, TypeError):
            return len(queryset)

    def paginate_queryset(self, queryset, request, view=None):
        self.count = self.get_count(queryset)
        return super(MarketKeyCursorPagination, self).paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response({
            'count': self.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
