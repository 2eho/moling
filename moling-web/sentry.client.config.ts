// Sentry 客户端配置（浏览器端）
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  
  // 根据环境设置采样率
  // 生产环境建议 0.2，开发环境可以设为 1.0
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
  
  // 性能监控采样率
  profilesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
  
  // 环境标识
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || "development",
  
  // 发布版本
  release: `moling-web@${process.env.npm_package_version || "1.0.0"}`,
  
  // 捕获用户 IP 等基本信息
  sendDefaultPii: true,
  
  // 集成
  integrations: [
    // 自动捕获客户端错误
    Sentry.browserTracingIntegration(),
    // 捕获控制台错误
    Sentry.captureConsoleIntegration({ levels: ["error", "warn"] }),
  ],
  
  // 过滤敏感信息
  beforeSend(event) {
    // 不发送包含身份验证令牌的错误
    if (event.request?.cookies) {
      delete event.request.cookies;
    }
    return event;
  },
});
