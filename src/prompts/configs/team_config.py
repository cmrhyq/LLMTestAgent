"""团队成员提示词配置。"""

TEAM_MEMBER_CONFIGURATIONS = {
    "case_generator": {
        "desc_for_llm": "测试用例专家，负责根据接口信息生成高质量测试用例。"
    },
    "executor": {
        "desc_for_llm": "测试执行专家，负责稳定执行用例并收集结果。"
    },
    "reporter": {
        "desc_for_llm": "报告专家，负责汇总执行结果并输出结构化测试报告。"
    },
}

