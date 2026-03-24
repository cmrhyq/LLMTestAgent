#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM API自动化测试工具 - 主入口

用法:
    python main.py --input <输入文件路径> [--output <输出目录>] [--config <配置文件路径>]
    
示例:
    python main.py --input examples/input_example.json
    python main.py --input examples/input_example.json --output output/
    python main.py --input examples/input_example.json --config config/config.yaml
"""

import argparse
import json
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import init_config
from src.workflows.workflow import run_workflow


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="LLM API自动化测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py --input examples/input_example.json
    python main.py --input examples/input_example.json --output output/
    python main.py --input examples/input_example.json --config config/config.yaml --mode simple
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入文件路径（JSON格式）"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="输出目录（默认: output）"
    )
    
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="配置文件路径（默认: config/config.yaml）"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    return parser.parse_args()


def load_input(input_path: str) -> dict:
    """
    加载输入文件
    
    Args:
        input_path: 输入文件路径
        
    Returns:
        dict: 输入数据
    """
    path = Path(input_path)
    
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 初始化配置
    config = init_config(args.config)
    
    # 设置日志级别
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("=" * 60)
    logger.info("🧪 LLM API自动化测试工具")
    logger.info("=" * 60)
    
    try:
        # 加载输入
        logger.info(f"📂 加载输入文件: {args.input}")
        input_data = load_input(args.input)
        
        # 设置输出目录
        config.output.base_dir = args.output
        config.output.test_cases_dir = f"{args.output}/test_cases"
        config.output.reports_dir = f"{args.output}/reports"
        config.output.logs_dir = f"{args.output}/logs"
        
        # 确保输出目录存在
        for dir_path in [config.output.test_cases_dir, config.output.reports_dir, config.output.logs_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        result = run_workflow(input_data, config)
        
        # 输出结果
        logger.info("=" * 60)
        logger.info("📊 执行结果")
        logger.info("=" * 60)
        
        if result.get("success") or result.get("report_paths"):
            summary = result.get("test_summary", {})
            logger.info(f"✅ 执行成功")
            logger.info(f"   总用例数: {summary.get('total', 0)}")
            logger.info(f"   通过: {summary.get('passed', 0)}")
            logger.info(f"   失败: {summary.get('failed', 0)}")
            logger.info(f"   跳过: {summary.get('skipped', 0)}")
            logger.info(f"   通过率: {summary.get('pass_rate', 0)}%")
            logger.info(f"   平均耗时: {summary.get('avg_response_time', 0):.2f}ms")
            
            if result.get("excel_path"):
                logger.info(f"📊 Excel用例: {result['excel_path']}")
            
            if result.get("report_paths"):
                logger.info(f"📝 测试报告:")
                for format_name, path in result["report_paths"].items():
                    logger.info(f"   - {format_name}: {path}")
        else:
            logger.error(f"❌ 执行失败: {result.get('error_message', '未知错误')}")
            sys.exit(1)
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ 执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
