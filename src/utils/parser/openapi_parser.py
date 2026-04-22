"""
OpenAPI接口文档解析模块

负责解析 OpenAPI 3.x / Swagger 2.0 接口文档，支持：
- JSON / YAML 两种格式
- 文件路径、HTTP(S) URL、原始字符串、字典 四种输入源
- $ref 引用解析（组件/模式引用）
- servers / host+basePath 拼接 baseUrl
- 路径参数、查询参数、请求头、请求体（含 requestBody / parameters in: body）
- 将 OpenAPI operation 转换为项目内部的 APIInfo 模型
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import yaml

from src.core.logging import get_logger
from src.data.enum.models import APIInfo, HttpMethod, Priority, ValidationResult

logger = get_logger(__name__)

InputType = Union[Dict[str, Any], str, Path]

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
DEFAULT_REQUEST_TIMEOUT = 15
MAX_REF_RESOLVE_DEPTH = 32


class OpenAPIParser:
    """
    OpenAPI 接口文档解析器

    解析 OpenAPI 3.x / Swagger 2.0 文档，并将每个 operation 转换为 APIInfo。

    Attributes:
        spec: 原始规范数据（已解析为字典）
        spec_version: 规范版本（swagger 2.0 或 openapi 3.x）
        base_url: 推断出的 base URL（servers[0].url 或 scheme://host+basePath）
        api_infos: 转换后的 APIInfo 列表
        validation_result: 校验结果
    """

    def __init__(
        self,
        default_priority: Priority = Priority.P1,
        default_server_index: int = 0,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """
        初始化解析器

        Args:
            default_priority: 默认用例优先级
            default_server_index: 当文档中存在多个 servers 时使用的索引
            request_timeout: URL 加载时的网络超时（秒）
        """
        self.default_priority: Priority = default_priority
        self.default_server_index: int = default_server_index
        self.request_timeout: int = request_timeout

        self.spec: Dict[str, Any] = {}
        self.spec_version: str = ""
        self.base_url: str = ""
        self.api_infos: List[APIInfo] = []
        self.validation_result: ValidationResult = ValidationResult()

    def parse(
        self,
        input_data: InputType,
        base_url_override: Optional[str] = None,
    ) -> Tuple[str, List[APIInfo], ValidationResult]:
        """
        解析 OpenAPI 文档

        Args:
            input_data: 输入数据，可为字典、JSON/YAML 字符串、文件路径或 HTTP(S) URL
            base_url_override: 若提供则覆盖文档中推断出的 baseUrl

        Returns:
            Tuple[str, List[APIInfo], ValidationResult]: baseUrl、API列表、校验结果
        """
        self.spec = {}
        self.spec_version = ""
        self.base_url = ""
        self.api_infos = []
        self.validation_result = ValidationResult()

        try:
            self.spec = self._load_input(input_data)
        except Exception as exc:
            self.validation_result.add_error(f"加载 OpenAPI 文档失败: {exc}")
            return self.base_url, self.api_infos, self.validation_result

        if not isinstance(self.spec, dict) or not self.spec:
            self.validation_result.add_error("OpenAPI 文档内容为空或格式无效")
            return self.base_url, self.api_infos, self.validation_result

        self.spec_version = self._detect_version(self.spec)
        if not self.spec_version:
            self.validation_result.add_error(
                "无法识别文档版本，缺少 openapi / swagger 字段"
            )
            return self.base_url, self.api_infos, self.validation_result

        self.base_url = base_url_override or self._extract_base_url(self.spec)

        paths = self.spec.get("paths")
        if not isinstance(paths, dict) or not paths:
            self.validation_result.add_error("OpenAPI 文档缺少 paths 字段或为空")
            return self.base_url, self.api_infos, self.validation_result

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                self.validation_result.add_warning(f"跳过非法 path 项: {path}")
                continue
            try:
                resolved_item = self._resolve_refs(path_item)
            except Exception as exc:
                self.validation_result.add_warning(
                    f"解析 path {path} 的 $ref 失败: {exc}"
                )
                resolved_item = path_item

            common_params = resolved_item.get("parameters", []) or []
            for method_key, operation in resolved_item.items():
                method_lower = str(method_key).lower()
                if method_lower not in HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    self.validation_result.add_warning(
                        f"{path} [{method_lower}] 操作定义非法，已跳过"
                    )
                    continue
                try:
                    api_info = self._build_api_info(
                        path=path,
                        method=method_lower,
                        operation=operation,
                        common_parameters=common_params,
                    )
                    if api_info is not None:
                        self.api_infos.append(api_info)
                except Exception as exc:
                    self.validation_result.add_error(
                        f"转换接口失败 {method_lower.upper()} {path}: {exc}"
                    )

        logger.info(
            "OpenAPI 解析完成: 版本=%s, baseUrl=%s, API数=%d, 校验通过=%s",
            self.spec_version,
            self.base_url,
            len(self.api_infos),
            self.validation_result.is_valid,
        )
        return self.base_url, self.api_infos, self.validation_result

    def _load_input(self, input_data: InputType) -> Dict[str, Any]:
        """
        加载输入数据为字典

        支持字典、HTTP(S) URL、文件路径、JSON/YAML 字符串。
        """
        if isinstance(input_data, dict):
            return input_data

        if isinstance(input_data, Path):
            return self._load_from_file(input_data)

        if isinstance(input_data, str):
            stripped = input_data.strip()
            if not stripped:
                raise ValueError("输入字符串为空")

            if self._is_http_url(stripped):
                return self._load_from_url(stripped)

            candidate_path = Path(stripped)
            if len(stripped) < 512 and "\n" not in stripped and candidate_path.exists():
                return self._load_from_file(candidate_path)

            return self._load_from_text(stripped)

        raise TypeError(f"不支持的输入类型: {type(input_data).__name__}")

    @staticmethod
    def _is_http_url(value: str) -> bool:
        """判断字符串是否为 HTTP(S) URL"""
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _load_from_file(self, path: Path) -> Dict[str, Any]:
        """从文件加载文档"""
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if not path.is_file():
            raise ValueError(f"路径不是文件: {path}")

        suffix = path.suffix.lower()
        with open(path, "r", encoding="utf-8") as fp:
            content = fp.read()

        if suffix in {".yaml", ".yml"}:
            return self._safe_yaml_load(content)
        if suffix == ".json":
            return json.loads(content)
        return self._load_from_text(content)

    def _load_from_url(self, url: str) -> Dict[str, Any]:
        """从 HTTP(S) URL 加载文档（延迟导入 requests 避免硬依赖）"""
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("加载 URL 需要 requests 库，请先安装 requests") from exc

        try:
            response = requests.get(url, timeout=self.request_timeout)
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f"请求 OpenAPI 文档失败: {url}, 错误: {exc}") from exc

        content_type = response.headers.get("Content-Type", "").lower()
        text = response.text
        if "yaml" in content_type or url.lower().endswith((".yaml", ".yml")):
            return self._safe_yaml_load(text)
        if "json" in content_type or url.lower().endswith(".json"):
            return json.loads(text)
        return self._load_from_text(text)

    def _load_from_text(self, text: str) -> Dict[str, Any]:
        """按文本尝试解析：优先 JSON，失败则 YAML"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        return self._safe_yaml_load(text)

    @staticmethod
    def _safe_yaml_load(text: str) -> Dict[str, Any]:
        """使用 safe_load 解析 YAML，拒绝非字典顶层结构"""
        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("OpenAPI 文档顶层必须是对象 / 映射")
        return data

    @staticmethod
    def _detect_version(spec: Dict[str, Any]) -> str:
        """检测文档版本"""
        if isinstance(spec.get("openapi"), str):
            return f"openapi {spec['openapi']}"
        if isinstance(spec.get("swagger"), str):
            return f"swagger {spec['swagger']}"
        return ""

    def _extract_base_url(self, spec: Dict[str, Any]) -> str:
        """
        从文档中推断 baseUrl

        - OpenAPI 3.x: servers[default_server_index].url
        - Swagger 2.0: schemes[0] + host + basePath
        """
        servers = spec.get("servers")
        if isinstance(servers, list) and servers:
            index = min(self.default_server_index, len(servers) - 1)
            server = servers[index]
            if isinstance(server, dict):
                url = server.get("url", "")
                variables = server.get("variables") or {}
                if isinstance(variables, dict):
                    for var_name, var_def in variables.items():
                        if not isinstance(var_def, dict):
                            continue
                        default_value = var_def.get("default", "")
                        url = url.replace(f"{{{var_name}}}", str(default_value))
                return url.rstrip("/")

        host = spec.get("host")
        if isinstance(host, str) and host:
            schemes = spec.get("schemes") or ["https"]
            scheme = schemes[0] if isinstance(schemes, list) and schemes else "https"
            base_path = spec.get("basePath", "") or ""
            if base_path and not base_path.startswith("/"):
                base_path = f"/{base_path}"
            return f"{scheme}://{host}{base_path}".rstrip("/")

        return ""

    def _resolve_refs(
        self,
        node: Any,
        depth: int = 0,
        seen: Optional[set] = None,
    ) -> Any:
        """
        递归解析 $ref 引用

        仅支持文档内部引用（形如 #/components/schemas/Xxx），
        循环引用会被截断为空字典以避免无限递归。
        """
        if depth > MAX_REF_RESOLVE_DEPTH:
            logger.warning("$ref 解析深度超过上限 %d，已截断", MAX_REF_RESOLVE_DEPTH)
            return {}

        if seen is None:
            seen = set()

        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if not ref.startswith("#/"):
                    logger.warning("不支持的外部 $ref: %s", ref)
                    return {}
                if ref in seen:
                    return {}
                seen = seen | {ref}
                target = self._lookup_ref(ref)
                return self._resolve_refs(target, depth + 1, seen)
            return {
                key: self._resolve_refs(value, depth + 1, seen)
                for key, value in node.items()
            }

        if isinstance(node, list):
            return [self._resolve_refs(item, depth + 1, seen) for item in node]

        return node

    def _lookup_ref(self, ref: str) -> Any:
        """根据 #/a/b/c 形式查找文档中的节点"""
        parts = ref.lstrip("#/").split("/")
        current: Any = self.spec
        for part in parts:
            key = part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                logger.warning("$ref 指向的节点不存在: %s", ref)
                return {}
        return current

    def _build_api_info(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        common_parameters: List[Dict[str, Any]],
    ) -> Optional[APIInfo]:
        """将单个 OpenAPI operation 转换为 APIInfo"""
        try:
            http_method = HttpMethod(method.upper())
        except ValueError:
            self.validation_result.add_warning(
                f"{method.upper()} {path} 的方法不受支持，已跳过"
            )
            return None

        operation_id = operation.get("operationId") or ""
        summary = operation.get("summary") or ""
        description = operation.get("description") or summary
        tags = operation.get("tags") or []
        if not isinstance(tags, list):
            tags = []

        merged_params = self._merge_parameters(common_parameters, operation.get("parameters"))

        headers: Dict[str, str] = {}
        query_params: Dict[str, Any] = {}
        path_params: Dict[str, Any] = {}

        for param in merged_params:
            if not isinstance(param, dict):
                continue
            name = param.get("name")
            location = param.get("in")
            if not name or not location:
                continue
            example_value = self._example_from_parameter(param)

            if location == "header":
                headers[str(name)] = "" if example_value is None else str(example_value)
            elif location == "query":
                query_params[str(name)] = example_value
            elif location == "path":
                path_params[str(name)] = example_value
            elif location == "body":
                # Swagger 2.0 的 body 参数
                pass
            elif location == "formData":
                query_params[str(name)] = example_value

        body = self._extract_request_body(operation, merged_params, headers)

        final_url = self._build_url(path, path_params)

        name = operation_id or self._generate_name(method, path, summary)

        priority = self._infer_priority(tags)

        try:
            api_info = APIInfo(
                name=name,
                url=final_url,
                method=http_method,
                headers=headers,
                body=body,
                params=query_params or None,
                cache_rules=None,
                assert_rules=[],
                priority=priority,
                description=description.strip() if isinstance(description, str) else "",
                tags=[str(tag) for tag in tags],
            )
        except Exception as exc:
            self.validation_result.add_error(
                f"构造 APIInfo 失败 ({method.upper()} {path}): {exc}"
            )
            return None

        return api_info

    @staticmethod
    def _merge_parameters(
        common: List[Dict[str, Any]],
        operation_params: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """合并 path 级通用参数与 operation 级参数，operation 优先"""
        merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for param in common or []:
            if isinstance(param, dict) and param.get("name") and param.get("in"):
                merged[(param["name"], param["in"])] = param
        for param in operation_params or []:
            if isinstance(param, dict) and param.get("name") and param.get("in"):
                merged[(param["name"], param["in"])] = param
        return list(merged.values())

    def _example_from_parameter(self, param: Dict[str, Any]) -> Any:
        """从参数定义中提取示例值"""
        if "example" in param:
            return param["example"]

        examples = param.get("examples")
        if isinstance(examples, dict) and examples:
            first = next(iter(examples.values()))
            if isinstance(first, dict) and "value" in first:
                return first["value"]

        schema = param.get("schema")
        if isinstance(schema, dict):
            return self._example_from_schema(schema)

        # Swagger 2.0 直接将 type/default 放在参数上
        if "default" in param:
            return param["default"]
        if "type" in param:
            return self._default_value_for_type(param["type"], param.get("format"))
        return None

    def _example_from_schema(self, schema: Dict[str, Any], depth: int = 0) -> Any:
        """从 Schema 对象中生成示例值"""
        if depth > MAX_REF_RESOLVE_DEPTH:
            return None
        if not isinstance(schema, dict):
            return None

        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
        if isinstance(schema.get("enum"), list) and schema["enum"]:
            return schema["enum"][0]

        schema_type = schema.get("type")
        if schema_type == "object" or "properties" in schema:
            properties = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            obj: Dict[str, Any] = {}
            for prop_name, prop_schema in properties.items():
                if required and prop_name not in required:
                    # 非必填默认也填充，便于后续用例可以看到字段
                    pass
                obj[prop_name] = self._example_from_schema(prop_schema or {}, depth + 1)
            return obj

        if schema_type == "array":
            items = schema.get("items") or {}
            return [self._example_from_schema(items, depth + 1)]

        if schema_type:
            return self._default_value_for_type(schema_type, schema.get("format"))

        # 兼容 oneOf / anyOf / allOf
        for combinator in ("oneOf", "anyOf"):
            options = schema.get(combinator)
            if isinstance(options, list) and options:
                return self._example_from_schema(options[0], depth + 1)
        all_of = schema.get("allOf")
        if isinstance(all_of, list) and all_of:
            merged: Dict[str, Any] = {}
            for sub in all_of:
                value = self._example_from_schema(sub, depth + 1)
                if isinstance(value, dict):
                    merged.update(value)
            return merged or None

        return None

    @staticmethod
    def _default_value_for_type(schema_type: str, schema_format: Optional[str] = None) -> Any:
        """根据类型与格式返回默认示例值"""
        type_lower = (schema_type or "").lower()
        format_lower = (schema_format or "").lower()

        if type_lower == "string":
            if format_lower == "date":
                return "2024-01-01"
            if format_lower in {"date-time", "datetime"}:
                return "2024-01-01T00:00:00Z"
            if format_lower == "uuid":
                return "00000000-0000-0000-0000-000000000000"
            if format_lower == "email":
                return "user@example.com"
            if format_lower in {"binary", "byte"}:
                return ""
            return "string"
        if type_lower in {"integer", "number"}:
            return 0
        if type_lower == "boolean":
            return False
        if type_lower == "array":
            return []
        if type_lower == "object":
            return {}
        return None

    def _extract_request_body(
        self,
        operation: Dict[str, Any],
        merged_params: List[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        提取请求体

        - OpenAPI 3.x: 从 requestBody.content 中优先选择 application/json
        - Swagger 2.0: 从 parameters 中 in=body 的 schema 提取
        """
        request_body = operation.get("requestBody")
        if isinstance(request_body, dict):
            content = request_body.get("content")
            if isinstance(content, dict) and content:
                preferred_order = [
                    "application/json",
                    "application/*+json",
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                ]
                selected_media: Optional[str] = None
                for media_type in preferred_order:
                    if media_type in content:
                        selected_media = media_type
                        break
                if selected_media is None:
                    selected_media = next(iter(content.keys()))

                if "Content-Type" not in headers and "content-type" not in headers:
                    headers["Content-Type"] = selected_media

                media_obj = content.get(selected_media) or {}
                if "example" in media_obj:
                    example = media_obj["example"]
                elif isinstance(media_obj.get("examples"), dict) and media_obj["examples"]:
                    first_example = next(iter(media_obj["examples"].values()))
                    example = (
                        first_example.get("value")
                        if isinstance(first_example, dict)
                        else first_example
                    )
                else:
                    schema = media_obj.get("schema") or {}
                    example = self._example_from_schema(schema)
                if isinstance(example, dict):
                    return example
                if example is None:
                    return None
                return {"value": example}

        for param in merged_params:
            if not isinstance(param, dict):
                continue
            if param.get("in") == "body":
                schema = param.get("schema") or {}
                example = self._example_from_schema(schema)
                if isinstance(example, dict):
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    return example
                if example is not None:
                    return {"value": example}
        return None

    def _build_url(self, path: str, path_params: Dict[str, Any]) -> str:
        """
        构造最终 URL

        - 将 baseUrl 与 path 拼接
        - 若 path 中的参数有示例值则直接回填，保留 {placeholder} 以便后续用例生成
        """
        if not isinstance(path, str) or not path:
            raise ValueError("path 不能为空")

        final_path = path
        for name, value in (path_params or {}).items():
            if value is None or value == "":
                continue
            placeholder = "{" + str(name) + "}"
            if placeholder in final_path:
                final_path = final_path.replace(placeholder, str(value))

        if not self.base_url:
            return final_path if final_path.startswith("/") else f"/{final_path}"

        if final_path.startswith(("http://", "https://")):
            return final_path

        if not final_path.startswith("/"):
            final_path = f"/{final_path}"
        # return f"{self.base_url}{final_path}"
        return f"{final_path}"

    @staticmethod
    def _generate_name(method: str, path: str, summary: str) -> str:
        """在 operationId 缺失时生成 API 名称"""
        if summary:
            return summary.strip()
        normalized = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        normalized = normalized or "root"
        return f"{method.upper()}_{normalized}"

    def _infer_priority(self, tags: List[Any]) -> Priority:
        """
        根据 tags 推断优先级

        命中包含 smoke/p0 关键字的标签提升为 P0，critical/core 保持 P1，其它默认。
        """
        lower_tags = {str(tag).lower() for tag in tags if tag is not None}
        if any(keyword in tag for tag in lower_tags for keyword in ("smoke", "p0")):
            return Priority.P0
        if any(keyword in tag for tag in lower_tags for keyword in ("low", "p2", "optional")):
            return Priority.P2
        return self.default_priority


def parse_openapi(
    input_data: InputType,
    base_url_override: Optional[str] = None,
    default_priority: Priority = Priority.P1,
) -> Tuple[str, List[APIInfo], ValidationResult]:
    """
    解析 OpenAPI 文档的便捷函数

    Args:
        input_data: 输入数据（字典 / 字符串 / 路径 / URL）
        base_url_override: 可选的 baseUrl 覆盖
        default_priority: 默认用例优先级

    Returns:
        Tuple[str, List[APIInfo], ValidationResult]: baseUrl、API列表、校验结果
    """
    parser = OpenAPIParser(default_priority=default_priority)
    return parser.parse(input_data, base_url_override=base_url_override)




