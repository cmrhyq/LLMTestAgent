"""
AWS Bedrock Luma Ray2 视频生成器

该模块提供了调用 AWS Bedrock Luma Ray2 模型生成视频的功能。
支持文本到视频（Text-to-Video）和图像到视频（Image-to-Video）两种模式。

使用前请确保：
1. 已配置 AWS 凭证（通过环境变量、AWS CLI 或 IAM 角色）
2. 已创建用于存储输出视频的 S3 存储桶
3. Bedrock 服务已在目标区域启用 Luma Ray2 模型访问权限
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


class AspectRatio(str, Enum):
    """支持的视频宽高比"""
    SQUARE = "1:1"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_3_4 = "3:4"
    ULTRAWIDE_21_9 = "21:9"
    ULTRAWIDE_9_21 = "9:21"


class Duration(str, Enum):
    """支持的视频时长"""
    SHORT = "5s"
    LONG = "9s"


class Resolution(str, Enum):
    """支持的视频分辨率"""
    SD = "540p"
    HD = "720p"


class JobStatus(str, Enum):
    """异步任务状态"""
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class VideoGenerationConfig:
    """视频生成配置"""
    prompt: str
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE_16_9
    duration: Duration = Duration.SHORT
    resolution: Resolution = Resolution.HD
    loop: bool = False

    def validate(self) -> None:
        """验证配置参数"""
        if not self.prompt or not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")
        if len(self.prompt) > 5000:
            raise ValueError(f"Prompt length {len(self.prompt)} exceeds maximum 5000 characters")
        if len(self.prompt) < 1:
            raise ValueError("Prompt must be at least 1 character")


@dataclass
class KeyframeImage:
    """关键帧图像配置"""
    image_data: bytes
    media_type: str = "image/jpeg"

    def to_dict(self) -> dict:
        """转换为 API 请求格式"""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": base64.b64encode(self.image_data).decode("utf-8")
            }
        }

    @classmethod
    def from_file(cls, file_path: str) -> "KeyframeImage":
        """从文件加载图像"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        suffix = path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }

        media_type = media_type_map.get(suffix)
        if not media_type:
            raise ValueError(f"Unsupported image format: {suffix}")

        with open(path, "rb") as f:
            image_data = f.read()

        return cls(image_data=image_data, media_type=media_type)


@dataclass
class ImageToVideoConfig(VideoGenerationConfig):
    """图像到视频生成配置"""
    start_frame: Optional[KeyframeImage] = None
    end_frame: Optional[KeyframeImage] = None

    def validate(self) -> None:
        """验证配置参数"""
        super().validate()
        if self.start_frame is None and self.end_frame is None:
            raise ValueError("At least one keyframe (start_frame or end_frame) must be provided")


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    invocation_arn: str
    status: JobStatus
    output_s3_uri: Optional[str] = None
    failure_message: Optional[str] = None
    submit_time: Optional[str] = None
    end_time: Optional[str] = None


class LumaRay2VideoGenerator:
    """
    AWS Bedrock Luma Ray2 视频生成器

    使用示例:
        generator = LumaRay2VideoGenerator(
            s3_output_bucket="my-video-bucket",
            region_name="us-east-1"
        )

        # 文本到视频
        config = VideoGenerationConfig(
            prompt="A beautiful sunset over the ocean with waves crashing",
            aspect_ratio=AspectRatio.LANDSCAPE_16_9,
            duration=Duration.SHORT,
            resolution=Resolution.HD
        )
        result = generator.generate_video(config)

        # 等待完成并下载
        final_result = generator.wait_for_completion(result.invocation_arn)
        if final_result.status == JobStatus.COMPLETED:
            generator.download_video(final_result.output_s3_uri, "output.mp4")
    """

    MODEL_ID = "luma.ray-v2:0"
    DEFAULT_POLL_INTERVAL_SECONDS = 30
    DEFAULT_MAX_WAIT_SECONDS = 600

    def __init__(
        self,
        s3_output_bucket: str,
        s3_output_prefix: str = "luma-ray2-videos",
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

    def generate_video(
        self,
        config: VideoGenerationConfig
    ) -> VideoGenerationResult:
        """
        生成视频（文本到视频）

        Args:
            config: 视频生成配置

        Returns:
            VideoGenerationResult: 包含任务 ARN 和初始状态的结果

        Raises:
            ValueError: 配置参数无效
            ClientError: AWS API 调用失败
        """
        config.validate()

        model_input = {
            "prompt": config.prompt,
            "aspect_ratio": config.aspect_ratio.value,
            "duration": config.duration.value,
            "resolution": config.resolution.value,
            "loop": config.loop
        }

        return self._start_async_invoke(model_input)

    def generate_video_from_image(
        self,
        config: ImageToVideoConfig
    ) -> VideoGenerationResult:
        """
        从图像生成视频（图像到视频）

        Args:
            config: 图像到视频生成配置

        Returns:
            VideoGenerationResult: 包含任务 ARN 和初始状态的结果

        Raises:
            ValueError: 配置参数无效
            ClientError: AWS API 调用失败
        """
        config.validate()

        model_input = {
            "prompt": config.prompt,
            "aspect_ratio": config.aspect_ratio.value,
            "duration": config.duration.value,
            "resolution": config.resolution.value,
            "loop": config.loop,
            "keyframes": {}
        }

        if config.start_frame:
            model_input["keyframes"]["frame0"] = config.start_frame.to_dict()
        if config.end_frame:
            model_input["keyframes"]["frame1"] = config.end_frame.to_dict()

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
                submit_time=response.get("submitTime")
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
                submit_time=response.get("submitTime"),
                end_time=response.get("endTime")
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

    def download_video(
        self,
        s3_uri: str,
        local_path: str
    ) -> str:
        """
        从 S3 下载生成的视频

        Args:
            s3_uri: S3 URI（例如 s3://bucket/path/video.mp4）
            local_path: 本地保存路径

        Returns:
            str: 本地文件路径
        """
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        parts = s3_uri[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")

        bucket = parts[0]
        key = parts[1]

        logger.info(f"Downloading video from {s3_uri} to {local_path}")

        self.s3_client.download_file(bucket, key, local_path)

        logger.info(f"Video downloaded successfully: {local_path}")
        return local_path

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
            kwargs = {
                "maxResults": max_results
            }
            if status_filter:
                kwargs["statusEquals"] = status_filter.value

            response = self.bedrock_runtime.list_async_invokes(**kwargs)

            results = []
            for item in response.get("asyncInvokeSummaries", []):
                status = JobStatus(item.get("status", "InProgress"))
                result = VideoGenerationResult(
                    invocation_arn=item["invocationArn"],
                    status=status,
                    submit_time=item.get("submitTime"),
                    end_time=item.get("endTime")
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
    s3_bucket = os.environ.get("LUMA_OUTPUT_BUCKET", "infrastructure-management-748154128199-us-east-1")
    region = os.environ.get("AWS_REGION", "us-west-2")

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=region
    )

    config = VideoGenerationConfig(
        prompt="A majestic eagle soaring through clouds at sunset, "
               "golden light illuminating its wings, cinematic quality",
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        duration=Duration.SHORT,
        resolution=Resolution.HD,
        loop=False
    )

    print(f"Starting video generation with prompt: {config.prompt[:50]}...")

    result = generator.generate_video(config)
    print(f"Job started: {result.invocation_arn}")

    try:
        final_result = generator.wait_for_completion(
            result.invocation_arn,
            poll_interval_seconds=30,
            max_wait_seconds=600
        )

        if final_result.status == JobStatus.COMPLETED:
            print(f"Video generated successfully!")
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
