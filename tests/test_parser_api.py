from pathlib import Path

from src.utils.parser import OpenAPIParser

if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    input_file = project_root / "input" / "test.json"
    parser = OpenAPIParser(input_file)
    for item in parser.endpoints:
        print(item)