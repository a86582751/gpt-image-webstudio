import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from .config import should_stop
from .core import format_duration, is_remote_disconnected_error, normalize_image_request_delay
from .logging_utils import log_debug, log_error, log_event, log_warning


def run_with_retry(action, label, retries=1, delay_seconds=2, on_retry=None):
    """Retry a single API/download operation; callers decide whether a failed job is skipped."""
    started_at = time.perf_counter()
    last_error = None
    for attempt in range(retries + 1):
        attempt_number = attempt + 1
        log_debug("请求", "开始尝试", operation=label, attempt=attempt_number, max_attempts=retries + 1)
        try:
            result = action()
            log_debug(
                "请求",
                "完成",
                operation=label,
                attempt=attempt_number,
                elapsed=format_duration(time.perf_counter() - started_at),
            )
            return result
        except Exception as error:
            last_error = error
            if label in ("图片生成", "图片编辑") and is_remote_disconnected_error(error):
                log_error("请求", "远端断开，不自动重试", operation=label, error=error)
                raise RuntimeError(
                    f"{label}遇到 RemoteDisconnected，不再自动重试，避免 API 可能已生成并计费后重复请求：{error}"
                ) from error
            if attempt < retries:
                log_warning(
                    "请求",
                    "失败，准备重试",
                    operation=label,
                    attempt=attempt_number,
                    retry_in=f"{delay_seconds:g}s",
                    error=error,
                )
                if on_retry:
                    on_retry(label, attempt + 1, retries, error)
                time.sleep(delay_seconds)
    log_error(
        "请求",
        "最终失败",
        operation=label,
        attempts=retries + 1,
        elapsed=format_duration(time.perf_counter() - started_at),
        error=last_error,
    )
    raise RuntimeError(f"{label}失败，已自动重试 {retries} 次：{last_error}") from last_error


class ImageRequestLaunchGate:
    def __init__(self, interval_seconds=0):
        self.interval_seconds = normalize_image_request_delay(interval_seconds)
        self.lock = threading.Lock()
        self.next_launch_at = time.perf_counter()

    def wait(self, stop_mode=None):
        with self.lock:
            now = time.perf_counter()
            scheduled_at = max(now, self.next_launch_at)
            self.next_launch_at = scheduled_at + self.interval_seconds
        remaining = max(0, scheduled_at - time.perf_counter())
        while remaining > 0:
            if stop_mode and should_stop(stop_mode):
                raise RuntimeError("任务已停止。")
            time.sleep(min(0.1, remaining))
            remaining = max(0, scheduled_at - time.perf_counter())


def run_bounded_concurrent_jobs(jobs, concurrency, worker, index_getter, stop_mode=None):
    jobs = list(jobs)
    concurrency = max(1, min(int(concurrency), len(jobs) or 1))
    completed_count = 0
    log_event("并发池", "启动", jobs=len(jobs), concurrency=concurrency, mode=stop_mode or "default")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        pending_jobs = iter(jobs)
        future_to_index = {}

        def submit_next():
            try:
                job = next(pending_jobs)
            except StopIteration:
                return False
            if stop_mode and should_stop(stop_mode):
                return False
            future_to_index[executor.submit(worker, job)] = index_getter(job)
            return True

        for _ in range(concurrency):
            submit_next()

        while future_to_index:
            if stop_mode and should_stop(stop_mode):
                for future in future_to_index:
                    future.cancel()
                log_event("并发池", "停止排队任务", completed=completed_count, pending=len(future_to_index), mode=stop_mode)
                yield None, None, True
                return

            done, _pending = wait(set(future_to_index), return_when=FIRST_COMPLETED)
            completed = []
            for future in done:
                job_index = future_to_index.pop(future)
                completed.append((job_index, future))

            for _job_index, _future in completed:
                submit_next()

            for job_index, future in completed:
                completed_count += 1
                yield job_index, future, False
    log_event("并发池", "结束", completed=completed_count, jobs=len(jobs), mode=stop_mode or "default")
