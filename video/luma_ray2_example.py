"""
AWS Bedrock Luma Ray2 视频生成示例

本示例展示如何使用 LumaRay2VideoGenerator 生成视频。

使用前准备：
1. 设置 AWS 凭证（通过环境变量或 AWS CLI）
2. 创建 S3 存储桶用于存储输出视频
3. 在 AWS Bedrock 控制台启用 Luma Ray2 模型访问权限

环境变量：
- AWS_ACCESS_KEY_ID: AWS 访问密钥 ID
- AWS_SECRET_ACCESS_KEY: AWS 秘密访问密钥
- AWS_REGION: AWS 区域（默认 us-east-1）
- LUMA_OUTPUT_BUCKET: S3 输出存储桶名称
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video import (
    AspectRatio,
    Duration,
    ImageToVideoConfig,
    JobStatus,
    KeyframeImage,
    LumaRay2VideoGenerator,
    Resolution,
    VideoGenerationConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_text_to_video_basic():
    """
    示例 1: 基础文本到视频生成

    使用简单的文本提示生成视频。
    """
    from dotenv import load_dotenv

    load_dotenv()
    logger.info("=== 示例 1: 基础文本到视频 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    config = VideoGenerationConfig(
        prompt="A serene mountain lake at dawn, mist rising from the water, "
               "surrounded by pine trees, peaceful and cinematic"
    )

    result = generator.generate_video(config)
    logger.info(f"任务已提交: {result.invocation_arn}")

    final_result = generator.wait_for_completion(result.invocation_arn)

    if final_result.status == JobStatus.COMPLETED:
        logger.info(f"视频生成成功: {final_result.output_s3_uri}")
        generator.download_video(final_result.output_s3_uri, "example1_basic.mp4")
    else:
        logger.error(f"视频生成失败: {final_result.failure_message}")


def example_text_to_video_advanced():
    """
    示例 2: 高级文本到视频生成

    使用完整参数配置生成视频。
    """
    logger.info("=== 示例 2: 高级文本到视频 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        s3_output_prefix="luma-videos/advanced",
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    config = VideoGenerationConfig(
        prompt="A futuristic city at night with flying cars, neon lights reflecting "
               "on wet streets, cyberpunk aesthetic, highly detailed, 4K quality",
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        duration=Duration.LONG,
        resolution=Resolution.HD,
        loop=True
    )

    result = generator.generate_video(config)
    logger.info(f"任务已提交: {result.invocation_arn}")

    final_result = generator.wait_for_completion(
        result.invocation_arn,
        poll_interval_seconds=30,
        max_wait_seconds=900
    )

    if final_result.status == JobStatus.COMPLETED:
        logger.info(f"视频生成成功: {final_result.output_s3_uri}")
        generator.download_video(final_result.output_s3_uri, "example2_advanced.mp4")
    else:
        logger.error(f"视频生成失败: {final_result.failure_message}")


def example_image_to_video():
    """
    示例 3: 图像到视频生成

    使用起始图像生成视频。
    """
    logger.info("=== 示例 3: 图像到视频 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    start_image_path = "input_image.jpg"
    if not os.path.exists(start_image_path):
        logger.warning(f"示例图像文件不存在: {start_image_path}")
        logger.info("请提供一个 JPEG 图像文件作为起始帧")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    start_frame = KeyframeImage.from_file(start_image_path)

    config = ImageToVideoConfig(
        prompt="The scene comes to life with gentle movement, "
               "leaves rustling in the wind, birds flying across the sky",
        start_frame=start_frame,
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        duration=Duration.SHORT,
        resolution=Resolution.HD
    )

    result = generator.generate_video_from_image(config)
    logger.info(f"任务已提交: {result.invocation_arn}")

    final_result = generator.wait_for_completion(result.invocation_arn)

    if final_result.status == JobStatus.COMPLETED:
        logger.info(f"视频生成成功: {final_result.output_s3_uri}")
        generator.download_video(final_result.output_s3_uri, "example3_image_to_video.mp4")
    else:
        logger.error(f"视频生成失败: {final_result.failure_message}")


def example_image_to_video_with_keyframes():
    """
    示例 4: 使用起始和结束关键帧生成视频

    指定起始帧和结束帧，让模型生成过渡动画。
    """
    logger.info("=== 示例 4: 关键帧到视频 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    start_image_path = "start_frame.jpg"
    end_image_path = "end_frame.jpg"

    if not os.path.exists(start_image_path) or not os.path.exists(end_image_path):
        logger.warning("示例图像文件不存在")
        logger.info("请提供 start_frame.jpg 和 end_frame.jpg 作为关键帧")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    start_frame = KeyframeImage.from_file(start_image_path)
    end_frame = KeyframeImage.from_file(end_image_path)

    config = ImageToVideoConfig(
        prompt="Smooth transition between the two scenes, "
               "morphing and blending naturally",
        start_frame=start_frame,
        end_frame=end_frame,
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        duration=Duration.SHORT,
        resolution=Resolution.HD,
        loop=False
    )

    result = generator.generate_video_from_image(config)
    logger.info(f"任务已提交: {result.invocation_arn}")

    final_result = generator.wait_for_completion(result.invocation_arn)

    if final_result.status == JobStatus.COMPLETED:
        logger.info(f"视频生成成功: {final_result.output_s3_uri}")
        generator.download_video(final_result.output_s3_uri, "example4_keyframes.mp4")
    else:
        logger.error(f"视频生成失败: {final_result.failure_message}")


def example_list_jobs():
    """
    示例 5: 列出历史任务

    查看最近的视频生成任务状态。
    """
    logger.info("=== 示例 5: 列出历史任务 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    logger.info("所有任务:")
    jobs = generator.list_jobs(max_results=10)
    for job in jobs:
        logger.info(
            f"  ARN: {job.invocation_arn[:50]}... | "
            f"状态: {job.status.value} | "
            f"提交时间: {job.submit_time}"
        )

    logger.info("\n已完成的任务:")
    completed_jobs = generator.list_jobs(max_results=5, status_filter=JobStatus.COMPLETED)
    for job in completed_jobs:
        logger.info(f"  ARN: {job.invocation_arn[:50]}...")


def example_different_aspect_ratios():
    """
    示例 6: 不同宽高比的视频

    生成不同宽高比的视频，适用于不同平台。
    """
    logger.info("=== 示例 6: 不同宽高比 ===")

    s3_bucket = "infrastructure-management-748154128199-us-east-1"
    if not s3_bucket:
        logger.error("请设置环境变量 LUMA_OUTPUT_BUCKET")
        return

    generator = LumaRay2VideoGenerator(
        s3_output_bucket=s3_bucket,
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )

    aspect_ratio_configs = [
        (AspectRatio.SQUARE, "instagram_square.mp4", "Instagram 正方形"),
        (AspectRatio.PORTRAIT_9_16, "tiktok_vertical.mp4", "TikTok/Reels 竖屏"),
        (AspectRatio.LANDSCAPE_16_9, "youtube_horizontal.mp4", "YouTube 横屏"),
    ]

    base_prompt = "A beautiful butterfly landing on a colorful flower, macro shot, detailed"

    for aspect_ratio, filename, description in aspect_ratio_configs:
        logger.info(f"生成 {description} 视频...")

        config = VideoGenerationConfig(
            prompt=base_prompt,
            aspect_ratio=aspect_ratio,
            duration=Duration.SHORT,
            resolution=Resolution.HD
        )

        result = generator.generate_video(config)
        logger.info(f"  任务已提交: {result.invocation_arn}")


def main():
    """运行所有示例"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     AWS Bedrock Luma Ray2 视频生成示例                       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  1. 基础文本到视频                                           ║
    ║  2. 高级文本到视频（完整参数）                               ║
    ║  3. 图像到视频（单个起始帧）                                 ║
    ║  4. 关键帧到视频（起始帧 + 结束帧）                          ║
    ║  5. 列出历史任务                                             ║
    ║  6. 不同宽高比视频                                           ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # required_env_vars = ["LUMA_OUTPUT_BUCKET"]
    # missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    #
    # if missing_vars:
    #     print(f"错误: 缺少必需的环境变量: {', '.join(missing_vars)}")
    #     print("\n请设置以下环境变量:")
    #     print("  export LUMA_OUTPUT_BUCKET=your-s3-bucket-name")
    #     print("  export AWS_REGION=us-east-1  # 可选")
    #     return

    print("请选择要运行的示例 (1-6), 或输入 'all' 运行所有示例:")
    choice = input("> ").strip().lower()

    examples = {
        "1": example_text_to_video_basic,
        "2": example_text_to_video_advanced,
        "3": example_image_to_video,
        "4": example_image_to_video_with_keyframes,
        "5": example_list_jobs,
        "6": example_different_aspect_ratios,
    }

    if choice == "all":
        for name, func in examples.items():
            try:
                func()
            except Exception as e:
                logger.error(f"示例 {name} 执行失败: {e}")
            print("\n" + "=" * 60 + "\n")
    elif choice in examples:
        try:
            examples[choice]()
        except Exception as e:
            logger.error(f"示例执行失败: {e}")
    else:
        print(f"无效的选择: {choice}")


if __name__ == "__main__":
    main()
