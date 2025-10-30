import unittest
from scripts.utils import retry


class RetryDecoratorTests(unittest.TestCase):
    def test_retry_succeeds_after_retries(self):
        call_counter = {"count": 0}

        @retry(max_attempts=3, delay=0)
        def flaky_function():
            call_counter["count"] += 1
            if call_counter["count"] < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_counter["count"], 3)

    def test_retry_raises_original_exception(self):
        call_counter = {"count": 0}

        @retry(max_attempts=2, delay=0)
        def always_fail():
            call_counter["count"] += 1
            raise RuntimeError("Permanent failure")

        with self.assertRaises(RuntimeError):
            always_fail()
        self.assertEqual(call_counter["count"], 2)


if __name__ == "__main__":
    unittest.main()
