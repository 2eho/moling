import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Providers } from '@/components/Providers';
import { AppShell } from '@/components/layout/AppShell';
import { Suspense } from 'react';

export const metadata: Metadata = {
  title: {
    default: '墨灵 - AI 创作工作台',
    template: '%s | 墨灵',
  },
  description: '墨灵 · 智能创作引擎，15秒完成整章生成',
  keywords: ['AI写作', '小说创作', '网文', '智能写作', '灵感抽卡'],
  authors: [{ name: '墨灵团队' }],
  // 预连接 API 服务端以减少 DNS/SSL 握手耗时
  other: {
    'Cache-Control': 'no-cache',
    // Content Security Policy (CSP) - 防止 XSS 攻击
    // 注意：生产环境请根据实际使用的外部资源调整
    'Content-Security-Policy': `
      default-src 'self';
      script-src 'self' 'unsafe-eval' https://www.googletagmanager.com;
      style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
      img-src 'self' data: https: blob:;
      font-src 'self' https://fonts.gstatic.com;
      connect-src 'self' https://api.yourdomain.com https://www.googletagmanager.com wss://api.yourdomain.com;
      frame-src 'self';
      media-src 'self' blob:;
      object-src 'none';
    `.replace(/\s+/g, ' ').trim(),
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#0d0f1a',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* 预连接 API 服务以缩短 TLS 握手时间 */}
        <link
          rel="preconnect"
          href={process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}
          crossOrigin="anonymous"
        />
        {/* DNS 预解析 */}
        <link
          rel="dns-prefetch"
          href={process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}
        />
      </head>
      <body>
        {/* 无障碍：跳过导航链接 */}
        <a
          href="#main-content"
          style={{
            position: 'absolute',
            left: '-9999px',
            width: '1px',
            height: '1px',
            overflow: 'hidden',
          }}
          className="skip-link"
        >
          跳过导航，直达内容
        </a>
        <Providers>
          <Suspense fallback={
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '100vh',
              background: 'var(--color-bg)'
            }}>
              加载中...
            </div>
          }>
            <AppShell>
              <div id="main-content">{children}</div>
            </AppShell>
          </Suspense>
        </Providers>
      </body>
    </html>
  );
}
