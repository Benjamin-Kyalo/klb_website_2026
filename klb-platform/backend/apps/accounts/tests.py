from django.test import TestCase
from rest_framework.test import APIClient

from apps.content.models import DropdownOption, News, Page, SiteSetting

from .models import ActivityLog, User
from .rbac import effective_permissions, has_permission, normalise_permissions


class PermissionRegistryTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super",
            email="super@example.com",
            password="StrongPass!2026",
            role=User.Role.SUPER_ADMIN,
        )
        self.admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPass!2026",
            role=User.Role.ADMINISTRATOR,
        )
        self.editor = User.objects.create_user(
            username="editor2",
            email="editor2@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )

    def test_super_admin_has_every_module(self):
        perms = effective_permissions(self.super_admin)
        self.assertIn("users", perms)
        self.assertIn("publish", perms["pages"])

    def test_editor_cannot_receive_system_modules(self):
        self.editor.permissions = {
            "news": ["view", "edit", "publish"],
            "users": ["view", "create", "edit", "delete"],
            "settings": ["view", "edit"],
            "options": ["view", "create", "edit", "delete"],
        }
        self.editor.save()
        perms = effective_permissions(self.editor)
        self.assertEqual(perms["news"], ["view", "edit", "publish"])
        self.assertEqual(perms["users"], [])
        self.assertEqual(perms["settings"], [])
        self.assertEqual(perms["options"], [])
        self.assertFalse(has_permission(self.editor, "users", "view"))

    def test_editor_defaults_are_least_privilege(self):
        perms = effective_permissions(self.editor)
        self.assertEqual(perms["news"], ["view", "create", "edit"])
        self.assertNotIn("delete", perms["news"])
        self.assertNotIn("publish", perms["news"])
        self.assertEqual(perms["enquiries"], ["view"])
        self.assertEqual(perms["options"], [])
        self.assertEqual(perms["media"], ["view", "create"])

    def test_editor_matrix_is_clamped_on_save(self):
        cleaned = normalise_permissions(
            {"users": ["view"], "books": ["view", "delete", "invented"]},
            User.Role.EDITOR,
        )
        self.assertEqual(cleaned["users"], [])
        self.assertEqual(cleaned["books"], ["view", "delete"])

    def test_empty_matrix_falls_back_to_role_defaults(self):
        cleaned = normalise_permissions({}, User.Role.EDITOR)
        self.assertEqual(cleaned, {})
        self.editor.permissions = cleaned
        self.editor.save()
        self.assertEqual(effective_permissions(self.editor)["news"], ["view", "create", "edit"])

    def test_suspended_user_has_no_permissions(self):
        self.editor.is_suspended = True
        self.editor.save()
        self.assertEqual(effective_permissions(self.editor), {})


class AdminPermissionApiTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super",
            email="super@example.com",
            password="StrongPass!2026",
            role=User.Role.SUPER_ADMIN,
        )
        self.admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPass!2026",
            role=User.Role.ADMINISTRATOR,
        )
        self.editor = User.objects.create_user(
            username="editor2",
            email="editor2@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )
        self.editor_limited = User.objects.create_user(
            username="limited",
            email="limited@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
            permissions={"news": ["view", "edit"], "options": ["view"]},
        )
        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def test_anonymous_cannot_reach_dashboard_api(self):
        response = self.client.get("/api/admin/pages/")
        self.assertIn(response.status_code, (401, 403))

    def test_editor_is_limited_to_content_modules(self):
        self.as_user(self.editor)
        self.assertEqual(self.client.get("/api/admin/pages/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/options/groups/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/options/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/users/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/activity/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/settings/").status_code, 403)

    def test_editor_can_create_news_but_not_publish_by_default(self):
        self.as_user(self.editor)
        response = self.client.post(
            "/api/admin/news/",
            {
                "title": "Permission test article",
                "published_at": "2026-11-06",
                "status": "published",
                "summary": "Created by an editor",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        article = News.objects.get(title="Permission test article")
        self.assertEqual(article.status, News.Status.DRAFT)
        self.assertTrue(
            ActivityLog.objects.filter(module="news", action=ActivityLog.Action.CREATE).exists()
        )
        self.assertFalse(
            ActivityLog.objects.filter(module="news", action=ActivityLog.Action.PUBLISH).exists()
        )

    def test_editor_without_create_or_publish_is_blocked(self):
        self.as_user(self.editor_limited)
        blocked = self.client.post(
            "/api/admin/news/",
            {"title": "Blocked article", "published_at": "2026-11-06"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)

        draft = News.objects.create(
            title="Draft article",
            slug="draft-article",
            published_at="2026-11-06",
            status=News.Status.DRAFT,
        )
        response = self.client.patch(
            f"/api/admin/news/{draft.slug}/",
            {"status": "published", "title": "Draft article edited"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        draft.refresh_from_db()
        self.assertEqual(draft.status, News.Status.DRAFT)
        self.assertEqual(draft.title, "Draft article edited")

    def test_editor_cannot_change_page_template_or_section_settings(self):
        page = Page.objects.create(slug="guarded", title="Guarded page")
        page.sections.create(label="Body", kind="html", html="<p>Original</p>")
        self.as_user(self.editor)
        response = self.client.patch(
            "/api/admin/pages/guarded/",
            {
                "title": "Guarded page edited",
                "template": "catalogue",
                "sections": [
                    {"label": "Body", "kind": "html", "html": "<p>Changed</p>", "settings": {"x": 1}}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        page.refresh_from_db()
        self.assertEqual(page.title, "Guarded page edited")
        self.assertEqual(page.template, Page.Template.PAGE)
        self.assertEqual(page.sections.first().settings, {})

    def test_admin_cannot_create_or_edit_super_administrators(self):
        self.as_user(self.admin)
        response = self.client.post(
            "/api/admin/users/",
            {
                "full_name": "Rogue Super",
                "email": "rogue@example.com",
                "role": "super_admin",
                "password": "StrongPass!2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.patch(
            f"/api/admin/users/{self.super_admin.pk}/",
            {"full_name": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_can_create_an_editor(self):
        self.as_user(self.admin)
        response = self.client.post(
            "/api/admin/users/",
            {
                "full_name": "New Editor",
                "email": "new.editor@example.com",
                "role": "editor",
                "password": "StrongPass!2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(email="new.editor@example.com")
        self.assertEqual(created.role, User.Role.EDITOR)
        self.assertTrue(created.is_staff)

    def test_admin_cannot_change_critical_settings(self):
        self.as_user(self.admin)
        response = self.client.patch(
            "/api/admin/settings/",
            {"tagline": "A safe operational change"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.patch(
            "/api/admin/settings/",
            {"navigation": [{"label": "Home", "href": "/"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_change_navigation(self):
        self.as_user(self.super_admin)
        response = self.client.patch(
            "/api/admin/settings/",
            {"navigation": [{"label": "Home", "href": "/"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(SiteSetting.load().navigation[0]["href"], "/")

    def test_last_super_admin_cannot_be_demoted_or_deleted(self):
        self.as_user(self.super_admin)
        response = self.client.patch(
            f"/api/admin/users/{self.super_admin.pk}/",
            {"role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.delete(f"/api/admin/users/{self.super_admin.pk}/")
        self.assertEqual(response.status_code, 400)

    def test_suspended_account_is_signed_out_of_the_session(self):
        self.editor.is_suspended = True
        self.editor.save()
        self.as_user(self.editor)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["user"])

    def test_page_duplication_requires_view_permission(self):
        page = Page.objects.create(slug="source-page", title="Source page")
        creator_only = User.objects.create_user(
            username="creatoronly",
            email="creatoronly@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
            permissions={"pages": ["create"]},
        )
        self.as_user(creator_only)
        response = self.client.post(f"/api/admin/pages/{page.slug}/duplicate/")
        self.assertEqual(response.status_code, 403)

    def test_activity_log_records_publishing(self):
        self.as_user(self.super_admin)
        news = News.objects.create(
            title="Draft for audit",
            slug="draft-for-audit",
            published_at="2026-11-06",
            status=News.Status.DRAFT,
        )
        response = self.client.patch(
            f"/api/admin/news/{news.slug}/",
            {"status": "published"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ActivityLog.objects.filter(
                module="news", action=ActivityLog.Action.PUBLISH, object_id=str(news.pk)
            ).exists()
        )
        response = self.client.get("/api/admin/activity/")
        self.assertEqual(response.status_code, 200)


class DropdownOptionTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="super",
            email="super@example.com",
            password="StrongPass!2026",
            role=User.Role.SUPER_ADMIN,
        )
        self.editor = User.objects.create_user(
            username="editor2",
            email="editor2@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )
        self.client = APIClient()

    def test_options_are_seeded_by_migration(self):
        self.assertGreater(DropdownOption.objects.count(), 0)

    def test_editor_can_read_but_not_manage_options(self):
        self.client.force_authenticate(user=self.editor)
        self.assertEqual(self.client.get("/api/admin/options/groups/").status_code, 200)
        response = self.client.post(
            "/api/admin/options/",
            {"group": "news_category", "value": "Test", "label": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_manage_options(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            "/api/admin/options/",
            {"group": "news_category", "value": "Innovation", "label": "Innovation"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_blank_value_is_generated_from_label(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(
            "/api/admin/options/",
            {"group": "news_category", "value": "", "label": "Research Notes"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["value"], "research-notes")
