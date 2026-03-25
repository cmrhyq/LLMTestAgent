#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例运行脚本

演示如何使用LLM API自动化测试工具的各个模块。
"""

import sys
from pathlib import Path

from src import run_workflow
from src.core.logging import get_logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = get_logger(__name__)


def example_parse_input():
    """示例：解析输入"""
    print("\n" + "=" * 60)
    print("[STEP1] 示例1: 解析输入")
    print("=" * 60)
    
    from src.utils.parser.input_parser import InputParser
    
    # 示例输入数据
    input_data = {
        "apis": [
            {
                "name": "示例API",
                "api_url": "https://httpbin.org/get",
                "method": "GET",
                "headers": {"Content-Type": "application/json"},
                "assert_rules": ["$.url contains httpbin.org"],
                "priority": "P0"
            }
        ]
    }
    
    parser = InputParser()
    api_infos, validation = parser.parse(input_data)
    
    print(f"解析结果: {len(api_infos)}个API")
    print(f"校验结果: {'通过' if validation.is_valid else '失败'}")
    
    for api in api_infos:
        print(f"  - {api.name}: {api.api_url} [{api.method.value}]")
    
    return api_infos


def example_generate_cases(api_infos):
    """示例：生成测试用例"""
    print("\n" + "=" * 60)
    print("[STEP2] 示例2: 生成测试用例")
    print("=" * 60)
    
    from src.graph.case_generator import CaseGenerator
    from src.core.config import get_config
    
    config = get_config()
    generator = CaseGenerator(config)
    
    test_cases = generator.generate(api_infos)
    test_cases = generator.validate_cases(test_cases)
    
    print(f"生成用例: {len(test_cases)}个")
    
    for case in test_cases[:5]:  # 只显示前5个
        print(f"  - [{case.priority.value}] {case.case_name}")
    
    if len(test_cases) > 5:
        print(f"  ... 还有{len(test_cases) - 5}个用例")
    
    return test_cases


def example_export_excel(test_cases):
    """示例：导出Excel"""
    print("\n" + "=" * 60)
    print("[STEP3] 示例3: 导出Excel")
    print("=" * 60)
    
    from src.utils.excel.exporter import ExcelExporter
    from src.core.config import get_config
    
    config = get_config()
    exporter = ExcelExporter(config)
    
    # 确保输出目录存在
    output_dir = Path("output/test_cases")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    excel_path = exporter.export_test_cases(test_cases)
    
    print(f"Excel文件: {excel_path}")
    
    return excel_path


def example_execute_tests(test_cases):
    """示例：执行测试"""
    print("\n" + "=" * 60)
    print("[STEP4] 示例4: 执行测试")
    print("=" * 60)
    
    from src.graph.test_executor import TestExecutor
    from src.core.config import get_config
    
    config = get_config()
    executor = TestExecutor(config)
    
    # 只执行前3个用例作为示例
    cases_to_execute = test_cases[:3]
    print(f"执行{len(cases_to_execute)}个用例...")
    
    test_results = executor.execute(cases_to_execute)
    
    for result in test_results:
        status_emoji = "[PASS]" if result.status.value == "passed" else "[FAIL]"
        print(f"  {status_emoji} {result.case_name}: {result.status.value} ({result.response_time:.2f}ms)")
    
    return test_results


def example_generate_report(test_results):
    """示例：生成报告"""
    print("\n" + "=" * 60)
    print("[STEP5] 示例5: 生成报告")
    print("=" * 60)
    
    from src.graph.report_generator import ReportGenerator
    from src.core.config import get_config
    
    config = get_config()
    generator = ReportGenerator(config)
    
    # 确保输出目录存在
    output_dir = Path("output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_paths = generator.generate(test_results, str(output_dir))
    
    print("生成的报告:")
    for format_name, path in report_paths.items():
        print(f"  - {format_name}: {path}")
    
    return report_paths


def example_full_workflow():
    """示例：完整工作流"""
    print("\n" + "=" * 60)
    print("[STEP6] 示例6: 完整工作流")
    print("=" * 60)

    from src.core.config import init_config
    
    # 初始化配置
    init_config()
    
    # 输入数据
    input_data = {
        "apis": [
            {
                "name": "HTTPBin GET",
                "api_url": "https://httpbin.org/get",
                "method": "GET",
                "headers": {"User-Agent": "LLMTestAgent"},
                "assert_rules": ["$.url contains httpbin.org"],
                "priority": "P0"
            },
            {
                "name": "HTTPBin POST",
                "api_url": "https://httpbin.org/post",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"message": "Hello, World!"},
                "assert_rules": ["$.json.message == Hello, World!"],
                "priority": "P0"
            }
        ]
    }
    
    # 运行工作流
    result = run_workflow(input_data)
    
    if result.get("success"):
        summary = result.get("test_summary", {})
        print(f"[OK] 工作流执行成功")
        print(f"   总用例数: {summary.get('total', 0)}")
        print(f"   通过: {summary.get('passed', 0)}")
        print(f"   失败: {summary.get('failed', 0)}")
        print(f"   通过率: {summary.get('pass_rate', 0)}%")
    else:
        print(f"[ERROR] 工作流执行失败: {result.get('error_message')}")
    
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("LLM API自动化测试工具 - 示例脚本")
    print("=" * 60)
    
    try:
        # 示例1: 解析输入
        api_infos = example_parse_input()
        
        # 示例2: 生成测试用例
        test_cases = example_generate_cases(api_infos)
        
        # 示例3: 导出Excel
        excel_path = example_export_excel(test_cases)
        
        # 示例4: 执行测试
        test_results = example_execute_tests(test_cases)
        
        # 示例5: 生成报告
        report_paths = example_generate_report(test_results)
        
        # 示例6: 完整工作流
        workflow_result = example_full_workflow()
        
        print("\n" + "=" * 60)
        print("[OK] 所有示例执行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 示例执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
