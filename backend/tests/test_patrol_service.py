import threading
import unittest

from app import patrol_workflow as workflow
from app.services.patrol import PatrolService
from app.store import store


class PatrolServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = PatrolService()
        suffix = f"{id(self)}-{threading.get_ident()}"
        entry, missing = self.service.create_entry({
            "巡视单号": f"TEST-{suffix}",
            "巡视路线": "山脊北线",
            "巡视人员": "张三",
            "发现问题数": 3,
        })
        self.assertFalse(missing)
        assert entry is not None
        self.entry_id = entry["id"]

    def test_list_and_detail_use_same_progress(self):
        self.service.run_action(self.entry_id, workflow.DISPATCH_ACTION)
        detail = self.service.get_entry(self.entry_id)
        items, _ = self.service.list_entries(keyword=f"TEST-{id(self)}-{threading.get_ident()}")
        self.assertEqual(detail["status"], workflow.INSPECTING_STATUS)
        self.assertEqual(detail["巡视状态"], workflow.INSPECTING_STATUS)
        self.assertEqual(items[0]["status"], detail["status"])
        self.assertEqual(items[0]["巡视状态"], detail["巡视状态"])

    def test_submit_and_void_outputs_remain_unchanged(self):
        entry_id = 2
        original = store.find("patrol", entry_id)
        original_route = original["巡视路线"]
        original_count = original["发现问题数"]

        entry, message = self.service.run_action(entry_id, workflow.SUBMIT_ACTION)
        self.assertEqual(message, "巡视单已提交结果")
        self.assertEqual(entry["status"], workflow.SUBMITTED_STATUS)

        entry, message = self.service.run_action(entry_id, workflow.VOID_ACTION)
        self.assertEqual(message, "巡视单已作废巡视")
        self.assertEqual(entry["status"], workflow.VOID_STATUS)
        self.assertTrue(entry["abnormal"])
        self.assertFalse(entry["pending"])
        self.assertEqual(entry["巡视路线"], original_route)
        self.assertEqual(entry["发现问题数"], original_count)

    def test_duplicate_submit_does_not_advance_and_void_wins(self):
        self.service.run_action(self.entry_id, workflow.DISPATCH_ACTION)
        self.service.run_action(self.entry_id, workflow.SUBMIT_ACTION)

        entry, message = self.service.run_action(self.entry_id, workflow.SUBMIT_ACTION)
        self.assertIsNone(entry)
        self.assertIn("不能执行提交结果", message)
        self.assertEqual(store.find("patrol", self.entry_id)["status"], workflow.SUBMITTED_STATUS)

        entry, _ = self.service.run_action(self.entry_id, workflow.VOID_ACTION)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], workflow.VOID_STATUS)

    def test_voided_entry_cannot_be_pushed_back_to_inspecting(self):
        entry, _ = self.service.run_action(self.entry_id, workflow.VOID_ACTION)
        self.assertIsNotNone(entry)
        for action in (workflow.DISPATCH_ACTION, workflow.SUBMIT_ACTION, workflow.VOID_ACTION):
            blocked, _ = self.service.run_action(self.entry_id, action)
            self.assertIsNone(blocked)
            self.assertEqual(store.find("patrol", self.entry_id)["status"], workflow.VOID_STATUS)


if __name__ == "__main__":
    unittest.main()
