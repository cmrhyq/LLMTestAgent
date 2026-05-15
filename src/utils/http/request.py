"""
API 测试基础服务类模块

该模块提供 API 测试的基础服务类，封装 HTTP 请求操作，支持：
- 所有标准 HTTP 方法（GET, POST, PUT, DELETE, PATCH）
- 请求和响应的自动日志记录
- 响应数据提取和缓存
- 多种认证方式（Bearer Token, Basic Auth, API Key）
- 错误处理和自动重试机制
"""

import random
import time
from typing import Any, Optional, Dict, Union
from urllib.parse import urljoin
import requests
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import (
    RequestException,
    ConnectionError,
    Timeout,
    HTTPError
)

from src.core.cache.data_cache import DataCache
from src.core.logging import get_logger


logger = get_logger(__name__)


def get_random_pc_ua():
    """
    随机生成PC端常见浏览器的User-Agent
    """
    # 浏览器名称和对应版本范围
    browsers = {
        "Chrome": {
            "versions": [f"{random.randint(90, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 999)}" for _ in range(5)],
            "template": "Mozilla/5.0 (Windows NT {windows_ver}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        },
        "Firefox": {
            "versions": [f"{random.randint(90, 110)}.0" for _ in range(5)],
            "template": "Mozilla/5.0 (Windows NT {windows_ver}; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
        },
        "Edge": {
            "versions": [f"{random.randint(90, 120)}.0.{random.randint(100, 999)}.{random.randint(10, 99)}" for _ in range(5)],
            "template": "Mozilla/5.0 (Windows NT {windows_ver}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
        },
        "Safari": {
            "versions": [f"{random.randint(10, 16)}.{random.randint(0, 3)}" for _ in range(5)],
            "template": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{mac_ver}_{mac_rev}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
        },
        "Opera": {
            "versions": [f"{random.randint(70, 100)}.0.{random.randint(1000, 9999)}.{random.randint(10, 999)}" for _ in range(5)],
            "template": "Mozilla/5.0 (Windows NT {windows_ver}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 OPR/{version}"
        }
    }

    # 随机选择操作系统版本
    windows_versions = ["10.0", "11.0", "6.3", "6.2", "6.1"]
    windows_ver = random.choice(windows_versions)

    # 随机Mac版本
    mac_ver = random.randint(10, 15)
    mac_rev = random.randint(0, 9)

    # 随机选择浏览器
    browser_name = random.choice(list(browsers.keys()))
    browser_data = browsers[browser_name]

    # 随机选择版本
    version = random.choice(browser_data["versions"])

    # 为Opera额外添加Chrome版本
    chrome_ver = f"{random.randint(80, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 999)}"

    # 生成User-Agent
    template = browser_data["template"]
    if browser_name == "Safari":
        user_agent = template.format(mac_ver=mac_ver, mac_rev=mac_rev, version=version)
    elif browser_name == "Opera":
        user_agent = template.format(windows_ver=windows_ver, chrome_ver=chrome_ver, version=version)
    else:
        user_agent = template.format(windows_ver=windows_ver, version=version)

    return user_agent


class HttpRequest:
    """
    API 测试基础服务类

    提供统一的 HTTP 请求接口，支持：
    - 所有标准 HTTP 方法
    - 自动日志记录
    - 响应数据提取和缓存
    - 多种认证方式
    - 错误处理和重试机制

    使用示例：
        service = BaseService("https://api.example.com")
        response = service.get("/users/1")
        user_id = service.extract_and_cache(response, "user_id", "id")
    """

    def __init__(
            self,
            base_url: str,
            connect_timeout: int = 30,
            read_timeout: int = 10,
            verify_ssl: bool = True,
            auth_type: Optional[str] = None,
            auth_credentials: Optional[Dict[str, str]] = None
    ):
        """
        初始化 BaseService 实例

        Args:
            base_url: API 基础 URL，如果为 None 则使用配置文件中的设置
            connect_timeout: API 连接超时时间（秒）
            read_timeout: API 读取超时时间（秒）
            verify_ssl: 是否验证 SSL 证书
            auth_type: 认证类型，可选值：'bearer', 'basic', 'api_key'
            auth_credentials: 认证凭证字典
        """
        self.base_url = base_url
        self.cache = DataCache.get_instance()

        # 创建 session 以复用连接
        self.session = requests.Session()

        # 设置默认超时
        self.timeout = (connect_timeout, read_timeout)

        # 设置 SSL 验证
        self.session.verify = verify_ssl

        # 设置认证
        self._setup_authentication(auth_type, auth_credentials)

        logger.info("HTTP客户端初始化", base_url=self.base_url)

    def _setup_authentication(
            self,
            auth_type: Optional[str],
            auth_credentials: Optional[Dict[str, str]]
    ) -> None:
        """
        设置认证方式

        Args:
            auth_type: 认证类型
            auth_credentials: 认证凭证
        """
        if auth_type == 'bearer':
            token = auth_credentials.get('token')
            if token:
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                logger.info("Bearer Token认证已配置")

        elif auth_type == 'basic':
            username = auth_credentials.get('username')
            password = auth_credentials.get('password')

            if username and password:
                self.session.auth = HTTPBasicAuth(username, password)
                logger.info("Basic认证已配置", username=username)

        elif auth_type == 'api_key':
            api_key = auth_credentials.get('api_key')
            header_name = auth_credentials.get('header_name')

            if api_key:
                self.session.headers.update({header_name: api_key})
                logger.info("API Key认证已配置", header_name=header_name)

    def _build_url(self, endpoint: str) -> str:
        """
        构建完整的 URL

        Args:
            endpoint: API 端点路径

        Returns:
            str: 完整的 URL
        """
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            return endpoint
        return urljoin(self.base_url, endpoint.lstrip('/'))

    def _log_request(
            self,
            method: str,
            url: str,
            **kwargs
    ) -> None:
        """
        记录请求信息

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他请求参数
        """
        log_data = {
            'method': method,
            'url': url,
        }

        # 记录请求参数（不记录敏感信息）
        if 'params' in kwargs:
            log_data['params'] = kwargs['params']

        if 'json' in kwargs:
            log_data['json_body'] = kwargs['json']

        if 'data' in kwargs:
            log_data['data'] = '***' if kwargs['data'] else None

        if "headers" in kwargs:
            log_data['headers'] = kwargs['headers']

        logger.debug("请求信息", **log_data)

    def _log_response(self, response: requests.Response) -> None:
        """
        记录响应信息

        Args:
            response: 响应对象
        """
        log_data = {
            'status_code': response.status_code,
            'response_time': response.elapsed.total_seconds(),
            'url': response.url,
        }

        # 尝试记录响应体（如果是 JSON）
        try:
            if response.headers.get('Content-Type', '').startswith('application/json'):
                log_data['response_body'] = response.json()
        except Exception:
            log_data['response_body'] = '(non-JSON or empty)'

        logger.debug("响应信息", **log_data)

    def _make_request_with_retry(
            self,
            method: str,
            url: str,
            enable_retry: bool = True,
            max_retries: int = 3,
            retry_interval: int = 1,
            **kwargs
    ) -> Response | None:
        """
        发送 HTTP 请求，支持自动重试

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他请求参数

        Returns:
            requests.Response: 响应对象

        Raises:
            RequestException: 请求失败且重试次数用尽
        """
        max_retries = max_retries if enable_retry else 0
        retry_delay = retry_interval

        last_exception = None

        for attempt in range(max_retries + 1):
            try:

                if "headers" in kwargs:
                    # 合并会话头和请求头
                    headers = kwargs['headers']
                    headers['Content-Type'] = 'application/json;charset=utf-8'
                    headers['User-Agent'] = get_random_pc_ua()
                    kwargs['headers'] = headers
                else:
                    headers = {'Content-Type': 'application/json;charset=utf-8', 'User-Agent': get_random_pc_ua()}
                    kwargs['headers'] = headers

                # 记录请求信息
                self._log_request(method, url, **kwargs)

                # 发送请求
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )

                # 记录响应信息
                self._log_response(response)

                # 检查 HTTP 错误
                response.raise_for_status()

                return response

            except (ConnectionError, Timeout) as e:
                last_exception = e
                logger.warning(
                    "网络错误",
                    attempt=attempt + 1, max_attempts=max_retries + 1, error=str(e),
                )

                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(
                        "请求重试耗尽",
                        attempts=max_retries + 1, error=str(e),
                    )

            except HTTPError as e:
                logger.error("HTTP错误", status_code=e.response.status_code, error=str(e))
                # 对于 5xx 错误可以重试，4xx 错误不重试
                if e.response.status_code >= 500 and attempt < max_retries:
                    last_exception = e
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

            except RequestException as e:
                logger.error("请求异常", error=str(e))
                raise

        # 如果所有重试都失败，抛出最后一个异常
        if last_exception:
            raise last_exception

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送 GET 请求

        Args:
            endpoint: API 端点路径
            **kwargs: 其他请求参数（params, headers 等）

        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(endpoint)
        return self._make_request_with_retry('GET', url, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送 POST 请求

        Args:
            endpoint: API 端点路径
            **kwargs: 其他请求参数（json, data, headers 等）

        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(endpoint)
        return self._make_request_with_retry('POST', url, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送 PUT 请求

        Args:
            endpoint: API 端点路径
            **kwargs: 其他请求参数（json, data, headers 等）

        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(endpoint)
        return self._make_request_with_retry('PUT', url, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送 DELETE 请求

        Args:
            endpoint: API 端点路径
            **kwargs: 其他请求参数（params, headers 等）

        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(endpoint)
        return self._make_request_with_retry('DELETE', url, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """
        发送 PATCH 请求

        Args:
            endpoint: API 端点路径
            **kwargs: 其他请求参数（json, data, headers 等）

        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(endpoint)
        return self._make_request_with_retry('PATCH', url, **kwargs)

    def extract_and_cache(
            self,
            response: requests.Response,
            cache_key: str,
            json_path: str = None
    ) -> Any:
        """
        从响应中提取数据并存储到缓存

        Args:
            response: 响应对象
            cache_key: 缓存键名
            json_path: JSON 路径，使用点号分隔（如 'data.user.id'）
                      如果为 None，则缓存整个响应体

        Returns:
            Any: 提取的数据

        Raises:
            ValueError: 如果响应不是 JSON 格式或路径无效
        """
        try:
            response_data = response.json()
        except Exception as e:
            logger.error("响应JSON解析失败", error=str(e))
            raise ValueError(f"Response is not valid JSON: {str(e)}")

        # 如果没有指定路径，缓存整个响应
        if json_path is None:
            self.cache.set(cache_key, response_data)
            logger.info("缓存完整响应", cache_key=cache_key)
            return response_data

        # 按照路径提取数据
        extracted_value = self._extract_by_path(response_data, json_path)

        if extracted_value is not None:
            self.cache.set(cache_key, extracted_value)
            logger.info("提取并缓存数据", json_path=json_path, cache_key=cache_key)
        else:
            logger.warning("路径未找到，缓存None", json_path=json_path, cache_key=cache_key)
            self.cache.set(cache_key, None)

        return extracted_value

    def _extract_by_path(self, data: Any, path: str) -> Any:
        """
        按照路径从数据中提取值

        Args:
            data: 数据对象（通常是字典或列表）
            path: 路径字符串，使用点号分隔（如 'data.user.id'）

        Returns:
            Any: 提取的值，如果路径无效则返回 None
        """
        if not path:
            return data

        keys = path.split('.')
        current = data

        for key in keys:
            try:
                # 处理列表索引
                if isinstance(current, list):
                    index = int(key)
                    current = current[index]
                # 处理字典键
                elif isinstance(current, dict):
                    current = current[key]
                else:
                    logger.warning("路径提取类型不匹配", key=key, actual_type=type(current).__name__)
                    return None
            except (KeyError, IndexError, ValueError, TypeError) as e:
                logger.warning("路径提取失败", path=path, error=str(e))
                return None

        return current

    def get_cached_value(self, cache_key: str, default: Any = None) -> Any:
        """
        从缓存中获取值

        Args:
            cache_key: 缓存键名
            default: 如果键不存在时返回的默认值

        Returns:
            Any: 缓存的值，如果不存在则返回 default
        """
        value = self.cache.get(cache_key, default)
        logger.debug("获取缓存值", cache_key=cache_key)
        return value

    def validate_status_code(
            self,
            response: requests.Response,
            expected_status: Union[int, list[int]]
    ) -> bool:
        """
        验证响应状态码

        Args:
            response: 响应对象
            expected_status: 期望的状态码，可以是单个整数或整数列表

        Returns:
            bool: 如果状态码匹配返回 True，否则返回 False
        """
        if isinstance(expected_status, int):
            expected_status = [expected_status]

        is_valid = response.status_code in expected_status

        if is_valid:
            logger.info("状态码验证通过", actual=response.status_code, expected=expected_status)
        else:
            logger.error("状态码验证失败", actual=response.status_code, expected=expected_status)

        return is_valid

    def close(self) -> None:
        """
        关闭 session，释放资源
        """
        if self.session:
            self.session.close()
            logger.debug("HTTP会话已关闭")

    def __enter__(self):
        """
        支持上下文管理器
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文时自动关闭 session
        """
        self.close()
