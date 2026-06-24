/**
 * Router abstraction layer — allows @moling/ui components to be shared
 * between Next.js (next/navigation) and Vite/Spa (react-router-dom).
 *
 * Each host app calls setRouterHook() once at startup to inject its router.
 */

type Router = {
  push: (url: string) => void;
};

let _routerHook: (() => Router) | null = null;

/** Called once by the host app to register its router implementation. */
export function setRouterHook(hook: () => Router): void {
  _routerHook = hook;
}

/** Abstraction wrapping the host app's router. */
export function useRouter(): Router {
  if (!_routerHook) {
    throw new Error(
      "setRouterHook() must be called before any component uses useRouter(). " +
        "In Next.js: import { useRouter } from 'next/navigation' and pass it. " +
        "In Vite/Spa: import { useNavigate } from 'react-router-dom' and wrap it.",
    );
  }
  return _routerHook();
}
