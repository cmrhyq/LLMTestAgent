import unittest

from src.workflow import TestWorkflow


class TestWorkflowTest(unittest.TestCase):

    def test_workflow(self):
        input_data = f"帮我测试‘JSONPlaceholder API’这个项目的用户列表接口"
        workflow = TestWorkflow()
        workflow.run(input_data)


if __name__ == '__main__':
    unittest.main()