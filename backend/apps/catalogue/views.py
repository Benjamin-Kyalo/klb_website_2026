from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """Public catalogue. Supports search, filters and pagination."""

    serializer_class = BookSerializer
    lookup_field = "slug"
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["title", "price", "created_at", "sort_order", "featured", "new_arrival"]
    ordering = ["-featured", "sort_order", "title"]

    def get_queryset(self):
        qs = Book.objects.filter(is_published=True)
        params = self.request.query_params

        category = params.get("category")
        if category:
            # ``categories`` is a JSON list. The native contains lookup is
            # PostgreSQL-only, so SQLite (tests, local previews) falls back to
            # a text match instead of raising NotSupportedError.
            from django.db import connection

            if connection.vendor == "postgresql":
                qs = qs.filter(
                    Q(category__iexact=category) | Q(categories__contains=[category])
                )
            else:
                qs = qs.filter(
                    Q(category__iexact=category) | Q(categories__icontains=category)
                )
        collection = params.get("collection")
        if collection:
            # Allow a short tab label such as "CBE" or "Secondary" to match
            # every grade/form collection that starts with it (for example
            # "CBE Grade 1", "Secondary Form 2").
            qs = qs.filter(collection__istartswith=collection)
        level = params.get("level")
        if level:
            qs = qs.filter(level__iexact=level)
        language = params.get("language")
        if language:
            qs = qs.filter(language__iexact=language)
        if params.get("featured") in {"1", "true"}:
            qs = qs.filter(featured=True)
        if params.get("new") in {"1", "true"}:
            qs = qs.filter(new_arrival=True)

        search = (params.get("q") or "").strip()
        if search:
            # PostgreSQL gets true full-text ranking. SQLite (tests, local
            # previews) falls back to case-insensitive term matching. The
            # choice is made from the connection vendor because the PostgreSQL
            # expression only fails when the queryset is evaluated.
            from django.db import connection

            if connection.vendor == "postgresql":
                search_query = SearchQuery(search, search_type="websearch")
                qs = qs.annotate(
                    rank=SearchRank("search_vector", search_query)
                ).filter(search_vector=search_query)
                if not params.get("ordering"):
                    qs = qs.order_by("-rank", "-featured", "sort_order", "title")
            else:
                terms = [term for term in search.split() if term]
                for term in terms:
                    qs = qs.filter(
                        Q(title__icontains=term)
                        | Q(subject__icontains=term)
                        | Q(description__icontains=term)
                        | Q(isbn__icontains=term)
                        | Q(category__icontains=term)
                    )

        return qs


class CatalogueFiltersView(APIView):
    """Facet values for the catalogue sidebar."""

    def get(self, request):
        base = Book.objects.filter(is_published=True)

        def values(field):
            return list(
                base.exclude(**{f"{field}": ""})
                .values_list(field, flat=True)
                .distinct()
                .order_by(field)
            )

        return Response(
            {
                "categories": values("category"),
                "collections": values("collection"),
                "levels": values("level"),
                "languages": values("language"),
                "subjects": values("subject"),
            }
        )
