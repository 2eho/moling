"""Unified Dependency Injection Container — RF4.1 形式化。

提供单一入口点进行所有服务查找，支持测试用 mock 替换（override/reset）。
纯 Python class-based registry，不引入第三方 DI 库。

用法:
    from app.core.di import ServiceProvider

    # 注册（在 app/service/__init__.py 中批量完成）
    ServiceProvider.register(AuthService, auth_service)

    # 查找
    auth = ServiceProvider.get(AuthService)

    # 测试 mock
    ServiceProvider.override(AuthService, mock_auth)
    # ... 测试 ...
    ServiceProvider.reset_overrides()
"""

from __future__ import annotations

from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")


class ServiceProvider:
    """中心化服务注册表，支持 mock override。

    所有 22 个 service 单例在 app/service/__init__.py 中注册。
    ServiceRegistry（sentinel 模式）继续用于 Celery worker 循环依赖解决。
    """

    _services: Dict[Type[Any], Any] = {}
    _overrides: Dict[Type[Any], Any] = {}

    @classmethod
    def register(cls, service_type: Type[T], instance: T) -> None:
        """注册服务实例（按类型）。重复注册会覆盖。"""
        cls._services[service_type] = instance

    @classmethod
    def get(cls, service_type: Type[T]) -> T:
        """获取服务实例，优先返回 mock override（测试用）。"""
        if service_type in cls._overrides:
            return cls._overrides[service_type]
        if service_type not in cls._services:
            raise KeyError(
                f"Service {service_type.__name__} 未注册。请在 app/service/__init__.py 中注册。"
            )
        return cls._services[service_type]

    @classmethod
    def override(cls, service_type: Type[T], mock: T) -> None:
        """测试用：临时替换服务。"""
        cls._overrides[service_type] = mock

    @classmethod
    def reset_overrides(cls) -> None:
        """清除所有 mock override（测试 teardown）。"""
        cls._overrides.clear()

    @classmethod
    def reset(cls) -> None:
        """完全重置（仅测试用）。"""
        cls._services.clear()
        cls._overrides.clear()

    @classmethod
    def list_registered(cls) -> list[str]:
        """列出所有已注册的服务类型名称。"""
        return [t.__name__ for t in cls._services]


# 便捷别名
service_provider = ServiceProvider
