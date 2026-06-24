"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export const LLM_MODELS = [
  { id: "deepseek-v4-pro", label: "deepseek-v4-pro", desc: "旗舰模型，最强综合能力" },
  { id: "deepseek-v4-flash", label: "deepseek-v4-flash", desc: "极速响应，高吞吐低延迟" },
] as const;

export type LLMModelId = (typeof LLM_MODELS)[number]["id"];

export interface LLMSettings {
  /** API Key — stored in localStorage, to be moved to backend */
  apiKey: string;
  /** LLM API base URL */
  baseUrl: string;
  /** Model ID */
  model: LLMModelId;
  /** Temperature 0–2 */
  temperature: number;
  /** Max output tokens */
  maxTokens: number;
}

interface LLMSettingsStore extends LLMSettings {
  setApiKey: (key: string) => void;
  setBaseUrl: (url: string) => void;
  setModel: (model: LLMModelId) => void;
  setTemperature: (t: number) => void;
  setMaxTokens: (n: number) => void;
  reset: () => void;
}

const DEFAULTS: LLMSettings = {
  apiKey: "",
  baseUrl: "https://api.deepseek.com",
  model: "deepseek-v4-pro",
  temperature: 0.8,
  maxTokens: 8192,
};

export const useLLMSettings = create<LLMSettingsStore>()(
  persist(
    (set) => ({
      ...DEFAULTS,

      setApiKey: (apiKey) => set({ apiKey }),
      setBaseUrl: (baseUrl) => set({ baseUrl }),
      setModel: (model) => set({ model }),
      setTemperature: (temperature) => set({ temperature: Math.min(2, Math.max(0, temperature)) }),
      setMaxTokens: (maxTokens) => set({ maxTokens: Math.min(32768, Math.max(256, maxTokens)) }),
      reset: () => set(DEFAULTS),
    }),
    {
      name: "moling-llm-settings",
      version: 1,
    },
  ),
);
