"""中继 Worker 连接池 — 注册、调度、心跳监控，线程安全。"""

from __future__ import annotations

import json
import threading
import time
import traceback
from typing import Any

from sustech_rag.relay.models import WorkerInfo, build_registered_msg


class WorkerPool:
    """管理所有已连接 Worker 的生命周期与任务调度。

    所有公共方法均为线程安全。
    """

    def __init__(self) -> None:
        self._workers: dict[str, WorkerInfo] = {}
        self._lock = threading.Lock()
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop: threading.Event | None = None

    # ------------------------------------------------------------------
    # Worker 生命周期
    # ------------------------------------------------------------------

    def register(
        self, worker_id: str, capabilities: dict[str, Any], websocket: Any
    ) -> None:
        """注册（或覆盖）一个 Worker 并返回注册确认消息的序列化文本。

        调用方应通过返回的 JSON 文本回复 Worker。
        """
        now = time.time()
        with self._lock:
            existing = self._workers.get(worker_id)
            if existing is not None:
                # 同一 worker_id 重连：替换旧的连接信息
                existing.websocket = websocket
                existing.capabilities = capabilities
                existing.last_heartbeat = now
                existing.connected_at = now
                existing.is_busy = False
                existing.current_task_id = None
            else:
                self._workers[worker_id] = WorkerInfo(
                    worker_id=worker_id,
                    capabilities=capabilities,
                    websocket=websocket,
                    connected_at=now,
                    last_heartbeat=now,
                )
            print(
                f"[relay] worker registered: {worker_id} "
                f"(total: {len(self._workers)})",
                flush=True,
            )

    def unregister(self, worker_id: str) -> WorkerInfo | None:
        """移除 Worker 并返回其信息，不存在则返回 None。"""
        with self._lock:
            worker = self._workers.pop(worker_id, None)
            if worker is not None:
                print(
                    f"[relay] worker unregistered: {worker_id} "
                    f"(total: {len(self._workers)})",
                    flush=True,
                )
            return worker

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_available_worker(self) -> WorkerInfo | None:
        """返回最优先的空闲 Worker（按生成速度降序），没有则返回 None。"""
        with self._lock:
            idle = [w for w in self._workers.values() if not w.is_busy]
            if not idle:
                return None
            # 按 tokens_per_second 降序（快的优先），无数据排最后
            idle.sort(
                key=lambda w: w.capabilities.get("tokens_per_second", 0),
                reverse=True,
            )
            return idle[0]

    def get_worker(self, worker_id: str) -> WorkerInfo | None:
        """获取指定 Worker。"""
        with self._lock:
            return self._workers.get(worker_id)

    def get_all_workers(self) -> list[WorkerInfo]:
        """返回所有 Worker 的快照列表。"""
        with self._lock:
            return list(self._workers.values())

    # ------------------------------------------------------------------
    # 状态管理
    # ------------------------------------------------------------------

    def mark_busy(self, worker_id: str, task_id: str) -> bool:
        """标记 Worker 为忙碌。返回 True 表示成功标记。"""
        with self._lock:
            worker = self._workers.get(worker_id)
            if worker is None:
                return False
            if worker.is_busy:
                return False
            worker.is_busy = True
            worker.current_task_id = task_id
            return True

    def mark_idle(self, worker_id: str) -> bool:
        """标记 Worker 为空闲。返回 True 表示成功标记。"""
        with self._lock:
            worker = self._workers.get(worker_id)
            if worker is None:
                return False
            worker.is_busy = False
            worker.current_task_id = None
            return True

    def update_heartbeat(self, worker_id: str) -> None:
        """更新 Worker 最近心跳时间。"""
        with self._lock:
            worker = self._workers.get(worker_id)
            if worker is not None:
                worker.last_heartbeat = time.time()

    # ------------------------------------------------------------------
    # 心跳检查（后台线程）
    # ------------------------------------------------------------------

    def start_heartbeat_checker(self, interval: float = 30, timeout: float = 90) -> None:
        """启动后台线程，定期检查心跳超时并断开僵死连接。

        Args:
            interval: 检查间隔（秒）。
            timeout: 心跳超时阈值（秒）。超过此时间未收到心跳即断开。
        """
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return  # already running

        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval, timeout),
            daemon=True,
            name="relay-heartbeat-checker",
        )
        self._heartbeat_thread.start()
        print(
            f"[relay] heartbeat checker started (interval={interval}s, timeout={timeout}s)",
            flush=True,
        )

    def stop_heartbeat_checker(self) -> None:
        """停止心跳检查后台线程。"""
        if self._heartbeat_stop is not None:
            self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=5)

    def _heartbeat_loop(self, interval: float, timeout: float) -> None:
        assert self._heartbeat_stop is not None
        while not self._heartbeat_stop.wait(interval):
            self._check_heartbeats(timeout)

    def _check_heartbeats(self, timeout: float) -> None:
        now = time.time()
        timed_out: list[str] = []
        with self._lock:
            for worker_id, worker in list(self._workers.items()):
                if now - worker.last_heartbeat > timeout:
                    timed_out.append(worker_id)

        for worker_id in timed_out:
            print(
                f"[relay] heartbeat timeout for {worker_id}, removing",
                flush=True,
            )
            worker = self.unregister(worker_id)
            if worker is not None:
                try:
                    # 尝试异步关闭 WebSocket；在同步线程中只能尽力而为
                    import asyncio

                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
                # 无法在后台线程优雅关闭 WebSocket，仅清理引用。
                # 下一轮事件循环会检测到断开。
