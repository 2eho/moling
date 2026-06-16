/**
 * API健康检查模块
 * 提供后端健康检查功能
 */

export interface HealthStatus {
  isOnline: boolean;
  lastChecked: Date | null;
  error: string | null;
}

type HealthListener = (status: HealthStatus) => void;

class HealthCheckService {
  private listeners: Set<HealthListener> = new Set();
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private status: HealthStatus = {
    isOnline: true,
    lastChecked: null,
    error: null,
  };
  private checkInterval = 30000; // 30秒
  private healthEndpoint = '/api/health';

  /**
   * 开始健康检查
   */
  start(): void {
    if (this.intervalId) return;

    // 立即检查一次
    this.check();

    // 设置定时检查
    this.intervalId = setInterval(() => {
      this.check();
    }, this.checkInterval);
  }

  /**
   * 停止健康检查
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * 执行健康检查
   */
  async check(): Promise<HealthStatus> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(this.healthEndpoint, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
        },
      });

      clearTimeout(timeoutId);

      const newStatus: HealthStatus = {
        isOnline: response.ok,
        lastChecked: new Date(),
        error: response.ok ? null : `HTTP ${response.status}`,
      };

      this.updateStatus(newStatus);
    } catch (error) {
      const newStatus: HealthStatus = {
        isOnline: false,
        lastChecked: new Date(),
        error: error instanceof Error ? error.message : '未知错误',
      };

      this.updateStatus(newStatus);
    }

    return this.status;
  }

  /**
   * 更新状态并通知监听器
   */
  private updateStatus(newStatus: HealthStatus): void {
    const wasOffline = !this.status.isOnline;
    const isNowOnline = newStatus.isOnline;

    this.status = newStatus;

    // 通知所有监听器
    this.notifyListeners();

    // 如果恢复在线，打印日志
    if (wasOffline && isNowOnline) {
      console.log('[HealthCheck] 后端连接已恢复');
    }
  }

  /**
   * 获取当前状态
   */
  getStatus(): HealthStatus {
    return { ...this.status };
  }

  /**
   * 订阅状态变化
   */
  subscribe(listener: HealthListener): () => void {
    this.listeners.add(listener);

    // 立即通知当前状态
    listener(this.getStatus());

    // 返回取消订阅函数
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * 通知所有监听器
   */
  private notifyListeners(): void {
    const status = this.getStatus();
    this.listeners.forEach((listener) => {
      try {
        listener(status);
      } catch (error) {
        console.error('[HealthCheck] 监听器执行失败:', error);
      }
    });
  }
}

// 导出单例
const healthCheckService = new HealthCheckService();
export default healthCheckService;
