/** PRISM FinOps — UI preferences store with persistence. */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { CostView } from '@/types/costs';

export type DateRangePreset = '7d' | '30d' | 'month';
export type PageSize = 20 | 50 | 100;

interface UiState {
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  costView: CostView;
  defaultDateRangePreset: DateRangePreset;
  recentPages: string[];
  pageSize: PageSize;
  toggleSidebar: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  setCostView: (view: CostView) => void;
  setDatePreset: (preset: DateRangePreset) => void;
  addRecentPage: (path: string) => void;
  setPageSize: (size: PageSize) => void;
}

/** Persisted UI preferences (sidebar, filters, table page size). */
export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      commandPaletteOpen: false,
      costView: 'unblended',
      defaultDateRangePreset: 'month',
      recentPages: [],
      pageSize: 20,
      toggleSidebar: () =>
        set({ sidebarCollapsed: !get().sidebarCollapsed }),
      openCommandPalette: () => set({ commandPaletteOpen: true }),
      closeCommandPalette: () => set({ commandPaletteOpen: false }),
      setCostView: (view) => set({ costView: view }),
      setDatePreset: (preset) => set({ defaultDateRangePreset: preset }),
      addRecentPage: (path) => {
        const recent = get().recentPages.filter((p) => p !== path);
        set({ recentPages: [path, ...recent].slice(0, 5) });
      },
      setPageSize: (size) => set({ pageSize: size }),
    }),
    {
      name: 'prism-ui',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        costView: state.costView,
        defaultDateRangePreset: state.defaultDateRangePreset,
        recentPages: state.recentPages,
        pageSize: state.pageSize,
      }),
    },
  ),
);
