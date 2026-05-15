#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM API自动化测试工具 - 主入口

用法:
    python main.py "<自然语言指令>" [--api-doc <OpenAPI文档路径>] [--config <配置文件路径>]

示例:
    python main.py "解析这份API文档" --api-doc docs/openapi.yaml
    python main.py "对用户模块执行测试" --api-doc docs/openapi.json
    python main.py "解析API文档并存储" --api-doc docs/petstore.yaml --config config/config.yaml
"""

import argparse
import sys
from pathlib import Path

from src.core.logging import get_logger

logger = get_logger(__name__)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import init_config
from src.workflow import TestWorkflow


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="LLM API自动化测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py "解析这份API文档" --api-doc docs/openapi.yaml
    python main.py "对用户模块执行测试" --api-doc docs/openapi.json
        """,
    )

    parser.add_argument(
        "instruction",
        help="自然语言指令（LLM 根据指令判断意图）",
    )

    parser.add_argument(
        "--api-doc", "-a",
        default=None,
        help="OpenAPI 文档文件路径（YAML/JSON）",
    )

    parser.add_argument(
        "--config", "-c",
        default=None,
        help="配置文件路径（默认: config/config.yaml）",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    config = init_config(args.config)

    logger.info("=" * 60)
    logger.info("LLM API 自动化测试工具")
    logger.info("=" * 60)

    api_doc_path: Path | None = None
    if args.api_doc:
        api_doc_path = Path(args.api_doc)
        if not api_doc_path.exists():
            logger.error(f"API 文档文件不存在: {api_doc_path}")
            sys.exit(1)
        logger.info(f"API 文档: {api_doc_path}")

    try:
        workflow = TestWorkflow(config)
        result = workflow.run(
            raw_input=args.instruction,
            api_doc_file_path=api_doc_path,
        )

        logger.info("=" * 60)
        logger.info("执行结果")
        logger.info("=" * 60)

        error_message = result.get("error_message", "")
        if error_message:
            logger.error(f"执行过程中出现错误: {error_message}")
            sys.exit(1)

        user_intent = result.get("user_intent", "")
        logger.info(f"识别意图: {user_intent}")

        if user_intent == "parse_openapi":
            logger.info("OpenAPI 文档解析并存储完成")
        elif user_intent == "run_test":
            summary = result.get("test_summary", {})
            report_path = result.get("report_path", "")
            if summary:
                logger.info(f"总用例数: {summary.get('total', 0)}")
                logger.info(f"通过: {summary.get('passed', 0)}")
                logger.info(f"失败: {summary.get('failed', 0)}")
                logger.info(f"通过率: {summary.get('pass_rate', 0)}%")
            if report_path:
                logger.info(f"测试报告: {report_path}")
        else:
            logger.info("工作流已完成")

        logger.info("执行成功")

    except ImportError as e:
        logger.error(f"依赖缺失: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
