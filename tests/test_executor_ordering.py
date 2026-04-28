import time
import unittest

from src.data.enum.workflow import HttpMethod, TestCase, TestResult, TestStatus
from src.graph.test_executor import TestExecutor


class TestExecutorOrderingTest(unittest.TestCase):
    def test_parallel_results_keep_case_order(self) -> None:
        executor = TestExecutor()
        executor.config.execution.concurrency.enabled = True
        executor.config.execution.concurrency.max_workers = 3

        domain = "https://a.test"

        cases = [
            TestCase(case_id="api_a_001", case_name="A-1", url="/api", method=HttpMethod.GET),
            TestCase(case_id="api_a_002", case_name="A-2", url="/api", method=HttpMethod.GET),
            TestCase(case_id="api_b_001", case_name="B-1", url="/api", method=HttpMethod.GET),
        ]

        delay_map = {
            "api_a_001": 0.20,
            "api_a_002": 0.05,
            "api_b_001": 0.10,
        }

        def fake_execute_single(case: TestCase) -> TestResult:
            time.sleep(delay_map[case.case_id])
            return TestResult(
                case_id=case.case_id,
                case_name=case.case_name,
                status=TestStatus.PASSED,
            )

        executor._execute_single = fake_execute_single  # type: ignore[method-assign]

        results = executor.execute(domain, cases)

        self.assertEqual(
            [r.case_id for r in results],
            [c.case_id for c in cases],
        )


if __name__ == "__main__":
    unittest.main()
