"""ServiceRegistry — 类型安全的服务定位器，解决 Service 层循环依赖问题。

所有延迟导入的服务/函数通过 Sentinel 类型注册到此注册表，
消费者通过 ``service_registry.get(SentinelType)`` 获取实例。

Sentinel 类型定义在此模块中，避免消费者模块直接导入服务模块，
从而打破循环依赖。
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


# =============================================================================
# Sentinel 类型 — 每个延迟依赖对应一个空 Sentinel
# =============================================================================

class RunGenTaskSentinel:
    """Sentinel for Celery task ``run_generation_task`` (app.worker.tasks)."""
    pass


class HealthMonitorServiceSentinel:
    """Sentinel for ``health_monitor_service`` (app.service.health_monitor)."""
    pass


class Phase4SchedulerSentinel:
    """Sentinel for ``phase4_scheduler`` (app.service.phase4_scheduler)."""
    pass


class CoherenceServiceSentinel:
    """Sentinel for ``coherence_service`` (app.service.coherence_service)."""
    pass


# =============================================================================
# ServiceRegistry
# =============================================================================

class ServiceRegistry:
    """类型安全的服务注册表。

    用法::

        # 注册（在服务模块底部）
        from app.core.service_registry import service_registry, HealthMonitorServiceSentinel
        health_monitor_service = HealthMonitorService()
        service_registry.register(HealthMonitorServiceSentinel, health_monitor_service)

        # 获取（在消费模块中）
        from app.core.service_registry import service_registry, HealthMonitorServiceSentinel
        svc = service_registry.get(HealthMonitorServiceSentinel)
    """

    _registry: dict[type, Any] = {}

    @classmethod
    def register(cls, service_type: type, instance: Any) -> None:
        """注册一个服务实例。

        Args:
            service_type: Sentinel 类型（作为键）
            instance: 服务实例

        Raises:
            ValueError: 如果该类型已经注册过
        """
        if service_type in cls._registry:
            raise ValueError(
                f"Service {service_type.__name__} is already registered"
            )
        cls._registry[service_type] = instance

    @classmethod
    def get(cls, service_type: type[T]) -> T:
        """获取已注册的服务实例。

        Args:
            service_type: Sentinel 类型

        Returns:
            已注册的服务实例

        Raises:
            RuntimeError: 如果服务未注册
        """
        if service_type not in cls._registry:
            raise RuntimeError(
                f"Service {service_type.__name__} not registered. "
                f"Ensure the service module is imported before this call."
            )
        return cls._registry[service_type]

    @classmethod
    def is_registered(cls, service_type: type) -> bool:
        """检查服务是否已注册。"""
        return service_type in cls._registry

    @classmethod
    def reset(cls) -> None:
        """清空注册表（仅用于测试）。"""
        cls._registry.clear()


# 全局单例
service_registry = ServiceRegistry()
