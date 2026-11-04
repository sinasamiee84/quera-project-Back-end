from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APISimpleTestCase

from core.pagination import DefaultPagination


class PaginationAPIChecks(APISimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.items = list(range(250))

    def test_default_pagination_returns_ten_items(self):
        request = Request(self.factory.get("/items/"))
        page = DefaultPagination().paginate_queryset(self.items, request)

        self.assertEqual(len(page), 10)
        self.assertEqual(page, list(range(10)))

    def test_limit_parameter_controls_page_size(self):
        request = Request(self.factory.get("/items/", {"limit": 5}))
        page = DefaultPagination().paginate_queryset(self.items, request)

        self.assertEqual(page, list(range(5)))

    def test_offset_parameter_controls_start_position(self):
        request = Request(
            self.factory.get("/items/", {"limit": 5, "offset": 20})
        )
        page = DefaultPagination().paginate_queryset(self.items, request)

        self.assertEqual(page, list(range(20, 25)))

    def test_large_limit_is_limited_to_max_limit(self):
        request = Request(self.factory.get("/items/", {"limit": 1000}))
        page = DefaultPagination().paginate_queryset(self.items, request)

        self.assertEqual(len(page), 100)
        self.assertEqual(page, list(range(100)))

    def test_paginated_response_contains_standard_keys(self):
        request = Request(self.factory.get("/items/"))
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(self.items, request)
        response = paginator.get_paginated_response(page)

        self.assertEqual(
            set(response.data.keys()),
            {"count", "next", "previous", "results"},
        )
        self.assertEqual(response.data["count"], 250)
        self.assertEqual(response.data["results"], list(range(10)))
