"use client";

import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  Sentry.captureException(error);

  return (
    <html>
      <body>
        <div style={{ 
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0d0f1a',
          color: '#e5e7eb',
          padding: '2rem'
        }}>
          <div style={{ maxWidth: '600px', textAlign: 'center' }}>
            <h2 style={{ color: '#6366f1', fontSize: '1.5rem', marginBottom: '1rem' }}>
              抱歉，应用程序出现了错误
            </h2>
            <p style={{ color: '#9ca3af', marginBottom: '1rem' }}>
              {error.message || '未知错误'}
            </p>
            <button
              onClick={() => reset()}
              style={{
                padding: '0.5rem 1.5rem',
                background: '#6366f1',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              重试
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
