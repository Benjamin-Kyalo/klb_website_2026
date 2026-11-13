from django.test import TestCase
from rest_framework.test import APIClient


class ReproCBE(TestCase):
    def test_cbe(self):
        client = APIClient()
        r = client.get("/api/books/?collection=CBE&page_size=5")
        print("STATUS", r.status_code)
        print("COUNT", r.data.get("count"))
        print("RESULTS", len(r.data.get("results", [])))
