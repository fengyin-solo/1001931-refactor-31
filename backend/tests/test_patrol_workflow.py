import unittest

from app.patrol_workflow import (
    DISPATCH_ACTION,
    INITIAL_STATUS,
    INSPECTING_STATUS,
    SUBMITTED_STATUS,
    SUBMIT_ACTION,
    VOID_ACTION,
    VOID_STATUS,
    ACTION_RULES,
    NEGATIVE_ACTIONS,
    STATUS_ORDER,
    apply_action,
    present_entry,
    target_status,
    workflow_rules,
)


class PatrolWorkflowTest(unittest.TestCase):
    def test_shared_order_and_action_table(self):
        self.assertEqual(STATUS_ORDER, ["待派发", "巡视中", "已提交", "已作废"])
        self.assertEqual(ACTION_RULES, {
            DISPATCH_ACTION: INSPECTING_STATUS,
            SUBMIT_ACTION: SUBMITTED_STATUS,
            VOID_ACTION: VOID_STATUS,
        })
        self.assertEqual(NEGATIVE_ACTIONS, (VOID_ACTION,))

        rules = workflow_rules()
        self.assertEqual(rules["status_order"], STATUS_ORDER)
        self.assertEqual(rules["initial_status"], INITIAL_STATUS)
        self.assertEqual(rules["negative_actions"], [VOID_ACTION])
        self.assertEqual(rules["actions"], [DISPATCH_ACTION, SUBMIT_ACTION, VOID_ACTION])

    def test_allowed_actions_follow_order(self):
        self.assertEqual(target_status(INITIAL_STATUS, DISPATCH_ACTION), INSPECTING_STATUS)
        self.assertEqual(target_status(INITIAL_STATUS, VOID_ACTION), VOID_STATUS)
        self.assertIsNone(target_status(INITIAL_STATUS, SUBMIT_ACTION))
        self.assertEqual(target_status(INSPECTING_STATUS, SUBMIT_ACTION), SUBMITTED_STATUS)
        self.assertEqual(target_status(SUBMITTED_STATUS, VOID_ACTION), VOID_STATUS)

    def test_voided_entry_cannot_move_back_to_inspecting(self):
        entry = {"status": VOID_STATUS}
        for action in (DISPATCH_ACTION, SUBMIT_ACTION, VOID_ACTION):
            self.assertIsNotNone(apply_action(entry, action))
            self.assertEqual(entry["status"], VOID_STATUS)

    def test_dispatch_resets_progress_flags_without_touching_history(self):
        entry = {
            "status": INITIAL_STATUS,
            "pending": False,
            "abnormal": True,
            "巡视路线": "海湾西线",
            "发现问题数": 5,
        }
        self.assertIsNone(apply_action(entry, DISPATCH_ACTION))
        self.assertEqual(entry["status"], INSPECTING_STATUS)
        self.assertTrue(entry["pending"])
        self.assertFalse(entry["abnormal"])
        self.assertEqual(entry["巡视路线"], "海湾西线")
        self.assertEqual(entry["发现问题数"], 5)

    def test_submitted_can_be_voided_and_duplicate_submit_runs_once(self):
        entry = {"status": INSPECTING_STATUS}
        self.assertIsNone(apply_action(entry, SUBMIT_ACTION))
        self.assertEqual(entry["status"], SUBMITTED_STATUS)
        self.assertFalse(entry["pending"])
        self.assertFalse(entry["abnormal"])

        self.assertIsNotNone(apply_action(entry, SUBMIT_ACTION))
        self.assertEqual(entry["status"], SUBMITTED_STATUS)

        self.assertIsNone(apply_action(entry, VOID_ACTION))
        self.assertEqual(entry["status"], VOID_STATUS)
        self.assertFalse(entry["pending"])
        self.assertTrue(entry["abnormal"])

    def test_presentation_uses_canonical_status_and_preserves_history(self):
        entry = {
            "status": INSPECTING_STATUS,
            "巡视状态": "旧展示值",
            "巡视路线": "1号风机环线",
            "发现问题数": 2,
        }
        presented = present_entry(entry)
        self.assertEqual(presented["status"], INSPECTING_STATUS)
        self.assertEqual(presented["巡视状态"], INSPECTING_STATUS)
        self.assertEqual(presented["巡视路线"], "1号风机环线")
        self.assertEqual(presented["发现问题数"], 2)
        self.assertEqual(entry["巡视状态"], "旧展示值")


if __name__ == "__main__":
    unittest.main()
