from rest_framework import serializers

from .models import Book


class BookSerializer(serializers.ModelSerializer):
    cover_url = serializers.CharField(read_only=True)
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id", "slug", "title", "category", "categories", "collection", "level",
            "language", "subject", "price", "price_display", "currency", "isbn",
            "publisher", "cover", "cover_upload", "cover_url", "description",
            "store_url", "source_url", "featured", "new_arrival", "is_published",
            "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    def get_price_display(self, obj):
        if obj.price is None:
            return ""
        return f"{obj.currency} {obj.price:,.0f}"
