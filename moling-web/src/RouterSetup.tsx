import { useNavigate } from "react-router-dom";
import { setRouterHook } from "@/lib/navigation";

/** Bridges react-router-dom → @moling/ui navigation abstraction. */
export function RouterSetup() {
  const navigate = useNavigate();

  // Synchronous — must be set before any child calls useRouter()
  setRouterHook(() => ({
    push: (url: string) => navigate(url),
  }));

  return null;
}
