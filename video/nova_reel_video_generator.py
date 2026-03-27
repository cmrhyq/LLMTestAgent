"""
AWS Bedrock Nova Reel 视频生成器

该模块提供了调用 AWS Bedrock Amazon Nova Reel 模型生成视频的功能。
支持以下三种视频生成模式：
1. TEXT_VIDEO - 文本到视频（单镜头，6秒）
2. MULTI_SHOT_AUTOMATED - 自动多镜头长视频（12-120秒）
3. MULTI_SHOT_MANUAL - 手动多镜头长视频（自定义每个镜头）

使用前请确保：
1. 已配置 AWS 凭证（通过环境变量、AWS CLI 或 IAM 角色）
2. 已创建用于存储输出视频的 S3 存储桶
3. Bedrock 服务已在目标区域启用 Nova Reel 模型访问权限

技术规格：
- 输出分辨率：1280x720（固定）
- 帧率：24fps（固定）
- 单镜头时长：6秒
- 长视频时长：12-120秒（6秒的倍数）
- 生成时间：约90秒（6秒视频）/ 14-17分钟（2分钟视频）
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """视频生成任务类型"""
    TEXT_VIDEO = "TEXT_VIDEO"
    MULTI_SHOT_AUTOMATED = "MULTI_SHOT_AUTOMATED"
    MULTI_SHOT_MANUAL = "MULTI_SHOT_MANUAL"


class JobStatus(str, Enum):
    """异步任务状态"""
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ImageFormat(str, Enum):
    """支持的图像格式"""
    PNG = "png"
    JPEG = "jpeg"


# 常量定义
DEFAULT_FPS = 24
DEFAULT_DIMENSION = "1280x720"
DEFAULT_SEED = 42
MIN_SEED = 0
MAX_SEED = 2147483646
SINGLE_SHOT_DURATION = 6
MIN_MULTI_SHOT_DURATION = 12
MAX_MULTI_SHOT_DURATION = 120
MAX_TEXT_PROMPT_LENGTH = 512
MAX_AUTOMATED_PROMPT_LENGTH = 4000
REQUIRED_IMAGE_WIDTH = 1280
REQUIRED_IMAGE_HEIGHT = 720


@dataclass
class NovaReelImageSource:
    """Nova Reel 图像源配置"""
    image_data: bytes
    image_format: ImageFormat = ImageFormat.JPEG

    def to_dict(self) -> dict:
        """转换为 API 请求格式（base64 编码）"""
        return {
            "format": self.image_format.value,
            "source": {
                "bytes": base64.b64encode(self.image_data).decode("utf-8")
            }
        }

    @classmethod
    def from_file(cls, file_path: str) -> "NovaReelImageSource":
        """
        从文件加载图像

        注意：图像必须是 1280x720 分辨率
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        suffix = path.suffix.lower()
        format_map = {
            ".jpg": ImageFormat.JPEG,
            ".jpeg": ImageFormat.JPEG,
            ".png": ImageFormat.PNG,
        }

        image_format = format_map.get(suffix)
        if not image_format:
            raise ValueError(f"Unsupported image format: {suffix}. Only PNG and JPEG are supported.")

        with open(path, "rb") as f:
            image_data = f.read()

        return cls(image_data=image_data, image_format=image_format)


@dataclass
class NovaReelS3ImageSource:
    """Nova Reel S3 图像源配置"""
    s3_uri: str
    image_format: ImageFormat = ImageFormat.JPEG
    bucket_owner: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为 API 请求格式（S3 URI）"""
        s3_location = {"uri": self.s3_uri}
        if self.bucket_owner:
            s3_location["bucketOwner"] = self.bucket_owner

        return {
            "format": self.image_format.value,
            "source": {
                "s3Location": s3_location
            }
        }


@dataclass
class VideoGenerationConfig:
    """视频生成配置（通用）"""
    fps: int = DEFAULT_FPS
    dimension: str = DEFAULT_DIMENSION
    seed: Optional[int] = None

    def validate(self) -> None:
        """验证配置参数"""
        if self.fps != DEFAULT_FPS:
            raise ValueError(f"FPS must be {DEFAULT_FPS}, got {self.fps}")
        if self.dimension != DEFAULT_DIMENSION:
            raise ValueError(f"Dimension must be {DEFAULT_DIMENSION}, got {self.dimension}")
        if self.seed is not None and (self.seed < MIN_SEED or self.seed > MAX_SEED):
            raise ValueError(f"Seed must be between {MIN_SEED} and {MAX_SEED}, got {self.seed}")

    def to_dict(self) -> dict:
        """转换为 API 请求格式"""
        config = {
            "fps": self.fps,
            "dimension": self.dimension,
        }
        if self.seed is not None:
            config["seed"] = self.seed
        return config


@dataclass
class TextToVideoConfig:
    """文本到视频配置（TEXT_VIDEO 任务）"""
    text: str
    image: Optional[NovaReelImageSource] = None
    video_config: VideoGenerationConfig = field(default_factory=VideoGenerationConfig)

    def validate(self) -> None:
        """验证配置参数"""
        if not self.text or not self.text.strip():
            raise ValueError("Text prompt cannot be empty")
        if len(self.text) > MAX_TEXT_PROMPT_LENGTH:
            raise ValueError(
                f"Text prompt length {len(self.text)} exceeds maximum "
                f"{MAX_TEXT_PROMPT_LENGTH} characters"
            )
        self.video_config.validate()

    def to_model_input(self) -> dict:
        """转换为模型输入格式"""
        text_to_video_params = {"text": self.text}

        if self.image:
            text_to_video_params["images"] = [self.image.to_dict()]

        video_config = self.video_config.to_dict()
        video_config["durationSeconds"] = SINGLE_SHOT_DURATION

        return {
            "taskType": TaskType.TEXT_VIDEO.value,
            "textToVideoParams": text_to_video_params,
            "videoGenerationConfig": video_config
        }


@dataclass
class AutomatedMultiShotConfig:
    """自动多镜头配置（MULTI_SHOT_AUTOMATED 任务）"""
    text: str
    duration_seconds: int = MIN_MULTI_SHOT_DURATION
    video_config: VideoGenerationConfig = field(default_factory=VideoGenerationConfig)

    def validate(self) -> None:
        """验证配置参数"""
        if not self.text or not self.text.strip():
            raise ValueError("Text prompt cannot be empty")
        if len(self.text) > MAX_AUTOMATED_PROMPT_LENGTH:
            raise ValueError(
                f"Text prompt length {len(self.text)} exceeds maximum "
                f"{MAX_AUTOMATED_PROMPT_LENGTH} characters"
            )
        if self.duration_seconds < MIN_MULTI_SHOT_DURATION:
            raise ValueError(
                f"Duration must be at least {MIN_MULTI_SHOT_DURATION} seconds, "
                f"got {self.duration_seconds}"
            )
        if self.duration_seconds > MAX_MULTI_SHOT_DURATION:
            raise ValueError(
                f"Duration must be at most {MAX_MULTI_SHOT_DURATION} seconds, "
                f"got {self.duration_seconds}"
            )
        if self.duration_seconds % SINGLE_SHOT_DURATION != 0:
            raise ValueError(
                f"Duration must be a multiple of {SINGLE_SHOT_DURATION} seconds, "
                f"got {self.duration_seconds}"
            )
        self.video_config.validate()

    def to_model_input(self) -> dict:
        """转换为模型输入格式"""
        video_config = self.video_config.to_dict()
        video_config["durationSeconds"] = self.duration_seconds

        return {
            "taskType": TaskType.MULTI_SHOT_AUTOMATED.value,
            "multiShotAutomatedParams": {
                "text": self.text
            },
            "videoGenerationConfig": video_config
        }


@dataclass
class Shot:
    """单个镜头配置"""
    text: str
    image: Optional[NovaReelImageSource | NovaReelS3ImageSource] = None

    def validate(self) -> None:
        """验证镜头参数"""
        if not self.text or not self.text.strip():
            raise ValueError("Shot text prompt cannot be empty")
        if len(self.text) > MAX_TEXT_PROMPT_LENGTH:
            raise ValueError(
                f"Shot text length {len(self.text)} exceeds maximum "
                f"{MAX_TEXT_PROMPT_LENGTH} characters"
            )

    def to_dict(self) -> dict:
        """转换为 API 请求格式"""
        shot_dict = {"text": self.text}
        if self.image:
            shot_dict["image"] = self.image.to_dict()
        return shot_dict


@dataclass
class ManualMultiShotConfig:
    """手动多镜头配置（MULTI_SHOT_MANUAL 任务）"""
    shots: list[Shot]
    video_config: VideoGenerationConfig = field(default_factory=VideoGenerationConfig)

    def validate(self) -> None:
        """验证配置参数"""
        if not self.shots:
            raise ValueError("At least one shot is required")
        max_shots = MAX_MULTI_SHOT_DURATION // SINGLE_SHOT_DURATION
        if len(self.shots) > max_shots:
            raise ValueError(f"Maximum {max_shots} shots allowed, got {len(self.shots)}")

        for i, shot in enumerate(self.shots):
            try:
                shot.validate()
            except ValueError as e:
                raise ValueError(f"Shot {i + 1}: {e}") from e

        self.video_config.validate()

    def to_model_input(self) -> dict:
        """转换为模型输入格式"""
        return {
            "taskType": TaskType.MULTI_SHOT_MANUAL.value,
            "multiShotManualParams": {
                "shots": [shot.to_dict() for shot in self.shots]
            },
            "videoGenerationConfig": self.video_config.to_dict()
        }


@dataclass
class ShotResult:
    """单个镜头生成结果"""
    status: str
    location: Optional[str] = None
    failure_type: Optional[str] = None
    failure_message: Optional[str] = None


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    invocation_arn: str
    status: JobStatus
    output_s3_uri: Optional[str] = None
    failure_message: Optional[str] = None
    submit_time: Optional[str] = None
    end_time: Optional[str] = None
    shots: list[ShotResult] = field(default_factory=list)
    full_video_location: Optional[str] = None


class NovaReelVideoGenerator:
    """
    AWS Bedrock Nova Reel 视频生成器

    使用示例:
        generator = NovaReelVideoGenerator(
            s3_output_bucket="my-video-bucket",
            region_name="us-east-1"
        )

        # 文本到视频（6秒）
        config = TextToVideoConfig(
            text="A beautiful sunset over the ocean with waves crashing"
        )
        result = generator.generate_text_to_video(config)

        # 等待完成并下载
        final_result = generator.wait_for_completion(result.invocation_arn)
        if final_result.status == JobStatus.COMPLETED:
            generator.download_video(final_result.output_s3_uri, "output.mp4")
    """

    MODEL_ID = "amazon.nova-reel-v1:1"
    DEFAULT_POLL_INTERVAL_SECONDS = 30
    DEFAULT_MAX_WAIT_SECONDS = 1200

    def __init__(
        self,
        s3_output_bucket: str,
        s3_output_prefix: str = "nova-reel-videos",
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        初始化视频生成器

        Args:
            s3_output_bucket: 输出视频的 S3 存储桶名称
            s3_output_prefix: S3 对象前缀（可选）
            region_name: AWS 区域（可选，默认使用环境配置）
            aws_access_key_id: AWS 访问密钥 ID（可选）
            aws_secret_access_key: AWS 秘密访问密钥（可选）
            aws_session_token: AWS 会话令牌（可选）
        """
        self.s3_output_bucket = s3_output_bucket
        self.s3_output_prefix = s3_output_prefix

        session_kwargs = {}
        if region_name:
            session_kwargs["region_name"] = region_name
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            session_kwargs["aws_session_token"] = aws_session_token

        self.session = boto3.Session(**session_kwargs)
        self.bedrock_runtime = self.session.client("bedrock-runtime")
        self.s3_client = self.session.client("s3")

        self._s3_output_uri = f"s3://{s3_output_bucket}"

    def generate_text_to_video(
        self,
        config: TextToVideoConfig
    ) -> VideoGenerationResult:
        """
        生成文本到视频（6秒单镜头）

        Args:
            config: 文本到视频配置

        Returns:
            VideoGenerationResult: 包含任务 ARN 和初始状态的结果

        Raises:
            ValueError: 配置参数无效
            ClientError: AWS API 调用失败
        """
        config.validate()
        model_input = config.to_model_input()
        return self._start_async_invoke(model_input)

    def generate_automated_multi_shot(
        self,
        config: AutomatedMultiShotConfig
    ) -> VideoGenerationResult:
        """
        生成自动多镜头长视频（12-120秒）

        模型会自动将长提示分解为多个镜头。

        Args:
            config: 自动多镜头配置

        Returns:
            VideoGenerationResult: 包含任务 ARN 和初始状态的结果

        Raises:
            ValueError: 配置参数无效
            ClientError: AWS API 调用失败
        """
        config.validate()
        model_input = config.to_model_input()
        return self._start_async_invoke(model_input)

    def generate_manual_multi_shot(
        self,
        config: ManualMultiShotConfig
    ) -> VideoGenerationResult:
        """
        生成手动多镜头长视频

        可以为每个镜头指定独立的提示和可选的起始图像。

        Args:
            config: 手动多镜头配置

        Returns:
            VideoGenerationResult: 包含任务 ARN 和初始状态的结果

        Raises:
            ValueError: 配置参数无效
            ClientError: AWS API 调用失败
        """
        config.validate()
        model_input = config.to_model_input()
        return self._start_async_invoke(model_input)

    def _start_async_invoke(self, model_input: dict) -> VideoGenerationResult:
        """启动异步调用"""
        try:
            response = self.bedrock_runtime.start_async_invoke(
                modelId=self.MODEL_ID,
                modelInput=model_input,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": self._s3_output_uri
                    }
                }
            )

            invocation_arn = response["invocationArn"]
            logger.info(f"Started async invoke: {invocation_arn}")

            return VideoGenerationResult(
                invocation_arn=invocation_arn,
                status=JobStatus.IN_PROGRESS,
                submit_time=str(response.get("submitTime")) if response.get("submitTime") else None
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Failed to start async invoke: {error_code} - {error_message}")
            raise

    def get_job_status(self, invocation_arn: str) -> VideoGenerationResult:
        """
        获取任务状态

        Args:
            invocation_arn: 异步调用的 ARN

        Returns:
            VideoGenerationResult: 当前任务状态
        """
        try:
            response = self.bedrock_runtime.get_async_invoke(
                invocationArn=invocation_arn
            )

            status_str = response.get("status", "InProgress")
            status = JobStatus(status_str)

            result = VideoGenerationResult(
                invocation_arn=invocation_arn,
                status=status,
                submit_time=str(response.get("submitTime")) if response.get("submitTime") else None,
                end_time=str(response.get("endTime")) if response.get("endTime") else None
            )

            if status == JobStatus.COMPLETED:
                output_config = response.get("outputDataConfig", {})
                s3_config = output_config.get("s3OutputDataConfig", {})
                result.output_s3_uri = s3_config.get("s3Uri")

            elif status == JobStatus.FAILED:
                result.failure_message = response.get("failureMessage", "Unknown error")

            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Failed to get job status: {error_code} - {error_message}")
            raise

    def wait_for_completion(
        self,
        invocation_arn: str,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait_seconds: int = DEFAULT_MAX_WAIT_SECONDS
    ) -> VideoGenerationResult:
        """
        等待任务完成

        Args:
            invocation_arn: 异步调用的 ARN
            poll_interval_seconds: 轮询间隔（秒）
            max_wait_seconds: 最大等待时间（秒）

        Returns:
            VideoGenerationResult: 最终任务状态

        Raises:
            TimeoutError: 超过最大等待时间
        """
        start_time = time.time()
        logger.info(f"Waiting for job completion: {invocation_arn}")

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(
                    f"Job did not complete within {max_wait_seconds} seconds"
                )

            result = self.get_job_status(invocation_arn)

            if result.status == JobStatus.COMPLETED:
                logger.info(f"Job completed successfully: {invocation_arn}")
                return result

            if result.status == JobStatus.FAILED:
                logger.error(f"Job failed: {result.failure_message}")
                return result

            logger.info(
                f"Job in progress, elapsed: {elapsed:.0f}s, "
                f"next check in {poll_interval_seconds}s"
            )
            time.sleep(poll_interval_seconds)

    def get_generation_status(self, output_s3_uri: str) -> dict:
        """
        获取视频生成状态详情

        从 S3 读取 video-generation-status.json 文件。

        Args:
            output_s3_uri: 输出 S3 URI

        Returns:
            dict: 生成状态详情
        """
        if not output_s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {output_s3_uri}")

        parts = output_s3_uri[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        status_key = f"{prefix}/video-generation-status.json" if prefix else "video-generation-status.json"

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=status_key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            logger.error(f"Failed to get generation status: {e}")
            raise

    def download_video(
        self,
        s3_uri: str,
        local_path: str,
        video_filename: str = "output.mp4"
    ) -> str:
        """
        从 S3 下载生成的视频

        Args:
            s3_uri: S3 URI（输出目录）
            local_path: 本地保存路径
            video_filename: 视频文件名（默认 output.mp4）

        Returns:
            str: 本地文件路径
        """
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        parts = s3_uri[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        video_key = f"{prefix}/{video_filename}" if prefix else video_filename

        logger.info(f"Downloading video from s3://{bucket}/{video_key} to {local_path}")

        self.s3_client.download_file(bucket, video_key, local_path)

        logger.info(f"Video downloaded successfully: {local_path}")
        return local_path

    def download_shot(
        self,
        s3_uri: str,
        shot_number: int,
        local_path: str
    ) -> str:
        """
        下载单个镜头视频

        Args:
            s3_uri: S3 URI（输出目录）
            shot_number: 镜头编号（从 1 开始）
            local_path: 本地保存路径

        Returns:
            str: 本地文件路径
        """
        shot_filename = f"shot_{shot_number:04d}.mp4"
        return self.download_video(s3_uri, local_path, shot_filename)

    def list_jobs(
        self,
        max_results: int = 10,
        status_filter: Optional[JobStatus] = None
    ) -> list[VideoGenerationResult]:
        """
        列出异步任务

        Args:
            max_results: 最大返回数量
            status_filter: 状态过滤器（可选）

        Returns:
            list[VideoGenerationResult]: 任务列表
        """
        try:
            kwargs = {"maxResults": max_results}
            if status_filter:
                kwargs["statusEquals"] = status_filter.value

            response = self.bedrock_runtime.list_async_invokes(**kwargs)

            results = []
            for item in response.get("asyncInvokeSummaries", []):
                status = JobStatus(item.get("status", "InProgress"))
                result = VideoGenerationResult(
                    invocation_arn=item["invocationArn"],
                    status=status,
                    submit_time=str(item.get("submitTime")) if item.get("submitTime") else None,
                    end_time=str(item.get("endTime")) if item.get("endTime") else None
                )

                if status == JobStatus.FAILED:
                    result.failure_message = item.get("failureMessage")

                results.append(result)

            return results

        except ClientError as e:
            logger.error(f"Failed to list jobs: {e}")
            raise


def main():
    """示例用法"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    region = os.environ.get("AWS_REGION", "us-east-1")

    generator = NovaReelVideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=region
    )

    config = TextToVideoConfig(
        text="A majestic eagle soaring through clouds at sunset, "
             "golden light illuminating its wings, cinematic quality",
        video_config=VideoGenerationConfig(seed=12345)
    )

    print(f"Starting video generation with prompt: {config.text[:50]}...")

    result = generator.generate_text_to_video(config)
    print(f"Job started: {result.invocation_arn}")

    try:
        final_result = generator.wait_for_completion(
            result.invocation_arn,
            poll_interval_seconds=30,
            max_wait_seconds=300
        )

        if final_result.status == JobStatus.COMPLETED:
            print("Video generated successfully!")
            print(f"Output location: {final_result.output_s3_uri}")

            local_path = "generated_video.mp4"
            generator.download_video(final_result.output_s3_uri, local_path)
            print(f"Video downloaded to: {local_path}")

        else:
            print(f"Video generation failed: {final_result.failure_message}")

    except TimeoutError as e:
        print(f"Timeout: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
