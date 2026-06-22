"use client";

import { useState, useEffect, useCallback, useRef } from "react";

type ResizeSide = "left" | "right";

interface ResizeConfig {
  /** ref to store the current resize state */
  resizeRef: React.MutableRefObject<{ side: ResizeSide; startX: number; startW: number } | null>;
  /** min/max bounds for left panel */
  leftBounds: [number, number];
  /** min/max bounds for right panel */
  rightBounds: [number, number];
}

export function usePanelResize({
  resizeRef,
  leftBounds,
  rightBounds,
}: ResizeConfig) {
  const [leftWidth, setLeftWidth] = useState(240);
  const [rightWidth, setRightWidth] = useState(260);

  const onResizeMouseDown = useCallback(
    (side: ResizeSide) => (e: React.MouseEvent) => {
      e.preventDefault();
      const startW = side === "left" ? leftWidth : rightWidth;
      resizeRef.current = { side, startX: e.clientX, startW };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [leftWidth, rightWidth, resizeRef],
  );

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const { side, startX, startW } = resizeRef.current;
      const delta = side === "left" ? e.clientX - startX : startX - e.clientX;
      const newW = Math.round(startW + delta);
      if (side === "left") {
        setLeftWidth(Math.max(leftBounds[0], Math.min(leftBounds[1], newW)));
      } else {
        setRightWidth(Math.max(rightBounds[0], Math.min(rightBounds[1], newW)));
      }
    };
    const onUp = () => {
      resizeRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [leftBounds, rightBounds, resizeRef]);

  return { leftWidth, rightWidth, onResizeMouseDown };
}
