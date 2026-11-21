import unittest
from aurel.fingerprint import fingerprint, require_same_config


class FingerprintTests(unittest.TestCase):
    def test_mapping_order_does_not_change_identity(self):
        require_same_config({"model": "v1", "decode": {"a": 1, "b": 2}},
                            {"decode": {"b": 2, "a": 1}, "model": "v1"})

    def test_each_supplied_field_changes_identity(self):
        spec = {"model": "v1", "data": "d1", "noise": 20, "seed": 42}
        for key in spec:
            changed = dict(spec)
            changed[key] = "changed"
            with self.assertRaises(ValueError):
                require_same_config(spec, changed)
        self.assertNotEqual(fingerprint({"ids": ["a", "b"]}),
                            fingerprint({"ids": ["b", "a"]}))

    def test_invalid_values_rejected(self):
        for spec in ({}, [], {"x": float("nan")}, {"x": float("inf")},
                     {1: "value"}, {"nested": {2: "value"}}, {"x": (1, 2)}):
            with self.assertRaises(ValueError):
                fingerprint(spec)

    def test_types_remain_distinct(self):
        values = [1, "1", True, 1.0, None]
        self.assertEqual(len({fingerprint({"x": x}) for x in values}), len(values))
