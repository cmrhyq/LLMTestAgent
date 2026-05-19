import unittest
from pathlib import Path

from src.graph.api_doc_storage import ApiDocStorage


class TestApiDocParse(unittest.TestCase):
    def test_api_doc_parse(self):
        project_root = Path(__file__).parent.parent
        input_file = project_root / "input" / "test.json"
        api_storage = ApiDocStorage()
        api_storage.openapi_parse_storage(input_file)


if __name__ == '__main__':
    unittest.main()