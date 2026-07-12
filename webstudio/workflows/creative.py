import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from ..config import *
from ..core import *
from ..image_tasks import *
from ..runtime import ImageRequestLaunchGate, format_duration
from ..text_tasks import *

def generate_creative_images(
    save_dir,
    creative_count,
    creative_random_enhance,
    text_concurrency,
    image_concurrency,
    retry_count,
    retry_delay,
    image_request_delay,
    image_model_provider,
    aspect_ratio,
    resolution,
    image_base_url,
    image_model_id,
    quality,
    image_api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    random_base_url,
    random_model_id,
    random_api_key,
    random_protocol,
    random_reasoning_effort,
    random_preference,
):
    reset_stop_flag("creative")
    image_model_provider, _selected_base_url, selected_model_id, selected_api_key = resolve_selected_image_config(
        image_model_provider,
        image_base_url,
        image_model_id,
        image_api_key,
        seedream_base_url,
        seedream_model_id,
        seedream_api_key,
    )
    validation_error = validate_selected_image_config(image_model_provider, selected_model_id, selected_api_key)
    if validation_error:
        yield "", [], validation_error
        return

    creative_count = int(creative_count)
    creative_random_enhance = bool(creative_random_enhance) and creative_count > 1
    text_concurrency = 1 if creative_random_enhance else max(1, int(text_concurrency))
    image_concurrency = max(1, int(image_concurrency))
    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    launch_gate = ImageRequestLaunchGate(image_request_delay)
    total_started_at = time.perf_counter()
    prompts = []
    saved_paths = []
    image_records = []
    save_dir = get_save_dir(save_dir)
    os.makedirs(save_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    request_size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, selected_model_id)
    quality = normalize_quality(quality)
    seedream_model_id = normalize_seedream_model_id(seedream_model_id)
    seedream_response_format = normalize_seedream_response_format(seedream_response_format)
    seedream_output_format = normalize_seedream_output_format(seedream_output_format)
    seedream_watermark = normalize_seedream_watermark(seedream_watermark)
    random_protocol = normalize_protocol(random_protocol)
    random_reasoning_effort = normalize_reasoning_effort(random_reasoning_effort)

    persist_config(
        {
            "save_dir": save_dir,
            "creative_count": creative_count,
            "creative_random_enhance": creative_random_enhance,
            "text_concurrency": text_concurrency,
            "image_concurrency": image_concurrency,
            "retry_count": retry_count,
            "retry_delay": retry_delay,
            "image_request_delay": image_request_delay,
            "image_model_provider": image_model_provider,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "base_url": image_base_url,
            "model_id": image_model_id,
            "quality": quality,
            "api_key": image_api_key,
            "seedream_base_url": seedream_base_url,
            "seedream_model_id": seedream_model_id,
            "seedream_api_key": seedream_api_key,
            "seedream_response_format": seedream_response_format,
            "seedream_output_format": seedream_output_format,
            "seedream_watermark": seedream_watermark,
            "random_base_url": random_base_url,
            "random_model_id": random_model_id,
            "random_api_key": random_api_key,
            "random_protocol": random_protocol,
            "random_reasoning_effort": random_reasoning_effort,
            "random_preference": random_preference,
        },
    )

    retry_events = []
    failed_prompts = []
    failed_images = []
    used_scenes = []
    enhance_status = "；随机增强开启，文本生成已强制串行" if creative_random_enhance else ""
    yield "", [], f"正在生成 {creative_count} 段随机提示词并流水线出图；图片模型 {image_model_provider}；文本并发 {text_concurrency}，图片并发 {image_concurrency}；生图并发间隔 {image_request_delay:g} 秒；请求尺寸 {request_size}；品质 {quality}{enhance_status}。"

    def prompt_worker(index, used_scenes_snapshot=None):
        return generate_random_prompt_job(
            index,
            "段",
            "提示词",
            random_base_url,
            random_model_id,
            random_api_key,
            random_preference,
            random_protocol,
            retry_count,
            retry_delay,
            random_reasoning_effort,
            used_scenes=used_scenes_snapshot,
            summarize_scene=creative_random_enhance,
        )

    def image_worker(index, prompt):
        launch_gate.wait("creative")
        started_at = time.perf_counter()
        events = []
        image_path = generate_one_image(
            prompt,
            save_dir,
            aspect_ratio,
            resolution,
            image_model_provider,
            image_base_url,
            image_model_id,
            quality,
            image_api_key,
            seedream_base_url,
            seedream_model_id,
            seedream_api_key,
            seedream_response_format,
            seedream_output_format,
            seedream_watermark,
            f"{timestamp}_creative{index:02d}",
            retry_count,
            retry_delay,
            lambda label, attempt, retries, error: events.append(
                f"第 {index} 张图片触发重试 {attempt}/{retries}：{error}"
            ),
        )
        return index, image_path, time.perf_counter() - started_at, events

    try:
        prompt_workers = 1 if creative_random_enhance else min(text_concurrency, creative_count)
        with ThreadPoolExecutor(max_workers=prompt_workers) as prompt_executor, ThreadPoolExecutor(
            max_workers=min(image_concurrency, creative_count)
        ) as image_executor:
            prompt_futures = {}
            image_futures = {}
            next_prompt_index = creative_count + 1

            if creative_random_enhance:
                next_prompt_index = submit_sequential_prompt_job(
                    prompt_executor,
                    prompt_futures,
                    1,
                    creative_count,
                    prompt_worker,
                    used_scenes,
                )
            else:
                prompt_futures.update(
                    {
                        prompt_executor.submit(prompt_worker, index): index
                        for index in range(1, creative_count + 1)
                    }
                )

            while prompt_futures or image_futures:
                if should_stop("creative"):
                    for future in set(prompt_futures) | set(image_futures):
                        future.cancel()
                    prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
                    scene_status = f"；已经用过场景：{format_used_scenes(used_scenes) or '暂无'}" if creative_random_enhance else ""
                    yield (
                        prompt_text,
                        build_gallery_items(saved_paths),
                        f"已停止：已生成提示词 {len(prompts)}/{creative_count} 段，已保存图片 {len(saved_paths)}/{creative_count} 张{scene_status}。",
                    )
                    return

                done, _pending = wait(set(prompt_futures) | set(image_futures), return_when=FIRST_COMPLETED)
                for future in done:
                    if future in prompt_futures:
                        index = prompt_futures.pop(future)
                        prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
                        try:
                            index, prompt, scene, events = future.result()
                            retry_events.extend(events)
                            prompts.append((index, prompt))
                            if scene:
                                used_scenes.append(scene)
                            image_futures[image_executor.submit(image_worker, index, prompt)] = index
                            prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
                            status_extra = f"\n{retry_events[-1]}" if retry_events else ""
                            scene_status = f"；已经用过场景：{format_used_scenes(used_scenes) or '暂无'}" if creative_random_enhance else ""
                            yield (
                                prompt_text,
                                build_gallery_items(saved_paths),
                                f"已生成 {len(prompts)}/{creative_count} 段提示词；已启动第 {index} 张生图；已完成 {len(saved_paths)}/{creative_count} 张{scene_status}。{status_extra}",
                            )
                        except Exception as e:
                            failed_prompts.append((index, str(e)))
                            yield (
                                prompt_text,
                                build_gallery_items(saved_paths),
                                f"提示词失败 {len(failed_prompts)} 段；跳过第 {index} 段提示词：{e}；已完成图片 {len(saved_paths)}/{creative_count} 张。",
                            )

                        if creative_random_enhance and not should_stop("creative"):
                            next_prompt_index = submit_sequential_prompt_job(
                                prompt_executor,
                                prompt_futures,
                                next_prompt_index,
                                creative_count,
                                prompt_worker,
                                used_scenes,
                            )
                    else:
                        index = image_futures.pop(future)
                        prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
                        try:
                            index, image_path, elapsed, events = future.result()
                            retry_events.extend(events)
                            saved_paths.append(image_path)
                            image_records.append((index, image_path, elapsed))
                            dimensions = get_image_dimensions(image_path) or request_size
                            status_extra = f"\n{retry_events[-1]}" if events else ""
                            scene_status = f"；已经用过场景：{format_used_scenes(used_scenes) or '暂无'}" if creative_random_enhance else ""
                            yield (
                                prompt_text,
                                build_gallery_items(saved_paths),
                                f"已完成 {len(saved_paths)}/{creative_count} 张；刚完成第 {index} 张，分辨率 {dimensions}，耗时 {format_duration(elapsed)}；累计耗时 {format_duration(time.perf_counter() - total_started_at)}{scene_status}{status_extra}",
                            )
                        except Exception as e:
                            failed_images.append((index, str(e)))
                            yield (
                                prompt_text,
                                build_gallery_items(saved_paths),
                                f"第 {index} 张图片失败并已跳过：{e}；已保存 {len(saved_paths)}/{creative_count} 张，失败 {len(failed_images)} 张。",
                            )

            if prompts:
                persist_config({"prompt": sorted(prompts)[-1][1]})

    except Exception as e:
        prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
        yield (
            prompt_text,
            build_gallery_items(saved_paths),
            f"创意模式调度中断：{e}；已生成提示词 {len(prompts)}/{creative_count} 段，已保存图片 {len(saved_paths)}/{creative_count} 张。",
        )
        return

    prompt_text = "\n\n".join(f"第 {i} 段提示词：\n{text}" for i, text in sorted(prompts))
    prompt_failure_summary = format_failed_jobs_summary(failed_prompts, item_label="段")
    image_failure_summary = format_failed_jobs_summary(failed_images, item_label="张")
    yield (
        prompt_text,
        build_gallery_items(saved_paths),
        f"创意模式完成：图片模型 {image_model_provider}；共生成 {len(prompts)} 段提示词，保存 {len(saved_paths)} 张图片，提示词失败 {len(failed_prompts)} 段，图片失败 {len(failed_images)} 张；{format_generation_stats(image_records, creative_count, time.perf_counter() - total_started_at, request_size)}；品质 {quality}；目录 {save_dir}{prompt_failure_summary}{image_failure_summary}",
    )
