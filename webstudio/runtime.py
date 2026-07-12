import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from .config import should_stop
from .core import format_duration, is_remote_disconnected_error, normalize_image_request_delay


def run_with_retry(action, label, retries=1, delay_seconds=2, on_retry=None):
    """Retry a single API/download operation; callers decide whether a failed job is skipped."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            return action()
        except Exception as error:
            last_error = error
            if label in ("图片生成", "图片编辑") and is_remote_disconnected_error(error):
                raise RuntimeError(
                    f"{label}遇到 RemoteDisconnected，不再自动重试，避免 API 可能已生成并计费后重复请求：{error}"
                ) from error
            if attempt < retries:
                if on_retry:
                    on_retry(label, attempt + 1, retries, error)
                time.sleep(delay_seconds)
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
                yield job_index, future, False
