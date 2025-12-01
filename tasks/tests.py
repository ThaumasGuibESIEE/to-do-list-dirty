from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Task


def tc(case_id):
    """Attach a test case identifier for traceability with test_list.yaml."""
    def decorator(func):
        func.test_case_id = case_id
        return func

    return decorator


class TaskModelTest(TestCase):
    @tc("TA03")
    def test_str_returns_title(self):
        task = Task(title="My task")

        self.assertEqual(str(task), "My task")


class TaskViewsTest(TestCase):
    def setUp(self):
        self.task = Task.objects.create(title="Demo task")

    @tc("TA01")
    def test_homepage_renders(self):
        response = self.client.get(reverse("list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Version :")

    @tc("TA02")
    def test_create_task_via_post(self):
        response = self.client.post(reverse("list"), {"title": "New task"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title="New task").exists())

    @tc("TA04")
    def test_update_page_renders(self):
        response = self.client.get(reverse("update_task", args=[self.task.id]))
        self.assertEqual(response.status_code, 200)

    @tc("TA05")
    def test_update_task_via_post(self):
        response = self.client.post(
            reverse("update_task", args=[self.task.id]),
            {"title": "Updated title"},
        )

        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated title")

    @tc("TA06")
    def test_delete_page_renders(self):
        response = self.client.get(reverse("delete", args=[self.task.id]))
        self.assertEqual(response.status_code, 200)

    @tc("TA07")
    def test_delete_task_via_post(self):
        response = self.client.post(reverse("delete", args=[self.task.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())


class EntryPointModulesTest(TestCase):
    @tc("TA08")
    def test_wsgi_module_imports(self):
        from todo import wsgi

        self.assertIsNotNone(wsgi.application)

    @tc("TA09")
    def test_asgi_module_imports(self):
        from todo import asgi

        self.assertIsNotNone(asgi.application)


class TaskFixtureImportTest(TestCase):
    @tc("TA10")
    def test_dataset_fixture_imports_tasks(self):
        self.assertEqual(Task.objects.count(), 0)

        call_command("loaddata", "dataset.json", verbosity=0)

        self.assertEqual(Task.objects.count(), 3)
        titles = set(Task.objects.values_list("title", flat=True))
        self.assertSetEqual(
            titles,
            {"Configurer Ruff", "Ecrire des tests", "Preparer la release"},
        )
