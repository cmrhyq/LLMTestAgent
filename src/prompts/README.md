# Prompts 模块使用指南

本模块提供了一套灵活的 Prompt 管理系统，用于构建和渲染 LLM 提示词。

## 目录结构

```
src/prompts/
├── __init__.py          # 统一导出入口
├── case.py              # 向后兼容层
├── loader.py            # YAML 模板加载器
├── builders/            # Prompt 构建器
│   ├── base.py          # 基类
│   └── case_builder.py  # 用例生成构建器
├── formatters/          # 数据格式化工具
│   └── case_formatter.py
├── templates/           # YAML 模板文件
│   ├── case_system.yaml
│   └── case_user.yaml
└── configs/             # 配置文件
    └── team_config.py
```

## 快速开始

### 方式一：使用预定义常量（最简单）

```python
from src.prompts import (
    CASE_GENERATION_SYSTEM_PROMPT,
    CASE_GENERATION_USER_PROMPT_TEMPLATE,
)

# 直接使用系统提示词
print(CASE_GENERATION_SYSTEM_PROMPT)

# 使用用户提示词模板（需要格式化）
user_prompt = CASE_GENERATION_USER_PROMPT_TEMPLATE.format(
    name="用户登录",
    url="https://api.example.com/login",
    method="POST",
    headers='{"Content-Type": "application/json"}',
    body='{"username": "test", "password": "123"}',
    assert_rules='["$.code == 200"]',
    priority="P0",
    description="登录接口",
    scenario_types="- 正常场景 (normal)\n- 参数缺失场景 (param_missing)",
)
```

### 方式二：使用 Builder（推荐）

```python
from src.prompts import CasePromptBuilder, build_case_prompts

# 使用 Builder 类
builder = CasePromptBuilder()

# 构建系统提示词
system_prompt = builder.build_system_prompt()

# 构建用户提示词
api_info = {
    "name": "用户登录",
    "url": "https://api.example.com/login",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "body": {"username": "test", "password": "123"},
    "assert_rules": ["$.code == 200"],
    "priority": "P0",
    "description": "登录接口",
}
scenario_types = "- 正常场景 (normal)\n- 参数缺失场景 (param_missing)"

user_prompt = builder.build_user_prompt(api_info, scenario_types)

# 或者使用便捷函数一次性获取
system_prompt, user_prompt = build_case_prompts(api_info, scenario_types)
```

### 方式三：使用 Formatter 工具

```python
from src.prompts import format_api_info_for_prompt, format_scenario_types

# 格式化 API 信息
api_info = {
    "name": "用户登录",
    "url": "https://api.example.com/login",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "body": {"username": "test", "password": "123"},
}
formatted = format_api_info_for_prompt(api_info)
# 返回规范化的字典，headers/body 已转为 JSON 字符串

# 格式化场景类型
scenarios = {
    "normal": True,
    "param_missing": True,
    "param_type_error": False,
    "boundary_value": True,
    "permission_error": False,
}
scenario_text = format_scenario_types(scenarios)
# 输出：
# - 正常场景 (normal)
# - 参数缺失场景 (param_missing)
# - 边界值场景 (boundary_value)
```

### 方式四：直接使用 Loader

```python
from src.prompts.loader import get_loader, PromptLoader

# 获取全局单例
loader = get_loader()

# 或创建自定义实例
custom_loader = PromptLoader(templates_dir="/path/to/templates")

# 加载 YAML 文件
data = loader.load_yaml("case_system.yaml")

# 渲染模板（支持 Jinja2 语法）
prompt = loader.render(
    template_name="case_user.yaml",
    context={"name": "测试接口"},
    prompt_key="prompt",
)

# 简单加载（不渲染）
prompt = loader.load_simple_prompt_sync("case_system.yaml")
```

## 添加新的 Prompt 模板

### 1. 创建 YAML 模板

在 `templates/` 目录下创建新的 YAML 文件：

```yaml
# templates/my_template.yaml
prompt: |
  这是一个示例模板。
  
  变量示例: {{ variable_name }}
  
  支持 Jinja2 语法：
  {% for item in items %}
  - {{ item }}
  {% endfor %}
```

### 2. 创建 Builder（可选）

```python
# builders/my_builder.py
from .base import BasePromptBuilder

class MyPromptBuilder(BasePromptBuilder):
    TEMPLATE = "my_template.yaml"
    
    def build_prompt(self, context: dict) -> str:
        return self.render(self.TEMPLATE, context)
```

### 3. 导出（可选）

在 `__init__.py` 中添加导出：

```python
from .builders.my_builder import MyPromptBuilder
```

## 场景类型说明

| 场景类型 | 说明 |
|---------|------|
| `normal` | 正常场景，使用有效参数 |
| `param_missing` | 参数缺失，移除必填参数 |
| `param_type_error` | 参数类型错误，如字符串改为数字 |
| `boundary_value` | 边界值，如空字符串、极值 |
| `permission_error` | 权限异常，如无 token 或无效 token |

## 团队成员配置

`configs/team_config.py` 定义了团队成员的 LLM 描述：

```python
from src.prompts.configs.team_config import TEAM_MEMBER_CONFIGURATIONS

# 获取用例生成器的描述
desc = TEAM_MEMBER_CONFIGURATIONS["case_generator"]["desc_for_llm"]
```

## 测试

```bash
python -m pytest tests/test_prompt_module.py -v
```
