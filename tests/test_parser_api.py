from pathlib import Path

from src.utils.parser import parse_openapi

if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    input_file = project_root / "input" / "httpbin_service.json"
    parsed_date = parse_openapi(input_file)
    for item in parsed_date[1]:
        print(item)