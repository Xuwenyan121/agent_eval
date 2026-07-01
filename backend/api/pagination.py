from rest_framework.pagination import PageNumberPagination


class FlexiblePageNumberPagination(PageNumberPagination):
    """Pagination that allows clients to specify page_size via query parameter."""
    page_size_query_param = "page_size"
    max_page_size = 10000