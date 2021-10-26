from rest_framework.pagination import CursorPagination


class MarketKeyCursorPagination(CursorPagination):
    ordering = '-locked_at'
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 200

    def get_page_size(self, request):
        # Use max page size for multi get filter.
        # Dirty hack. But alternative is copy-paste 70-lines function to put view into arguments.
        if 'account_id' in request.query_params:
            return self.max_page_size

        return super(MarketKeyCursorPagination, self).get_page_size(request)
