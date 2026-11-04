from rest_framework.pagination import PageNumberPagination ,LimitOffsetPagination
from rest_framework.response import Response
class DefaultPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100

    limit_query_param = 'limit'
    offset_query_param = 'offset'

    def get_paginated_response(self,data):

        return Response({
            'count':self.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
