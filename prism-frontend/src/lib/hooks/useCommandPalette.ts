/** PRISM FinOps — command palette keyboard shortcut hook. */

import { useCallback, useEffect } from 'react';

import { useUiStore } from '@/lib/store/uiStore';

/** Registers ⌘K / Ctrl+K and exposes open/close helpers. */
export function useCommandPalette() {
  const open = useUiStore((s) => s.commandPaletteOpen);
  const openCommandPalette = useUiStore((s) => s.openCommandPalette);
  const closeCommandPalette = useUiStore((s) => s.closeCommandPalette);

  const toggle = useCallback(() => {
    if (open) {
      closeCommandPalette();
    } else {
      openCommandPalette();
    }
  }, [closeCommandPalette, open, openCommandPalette]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isMetaK =
        (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
      if (!isMetaK) {
        return;
      }
      event.preventDefault();
      toggle();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [toggle]);

  return {
    open,
    openCommandPalette,
    closeCommandPalette,
    toggle,
  };
}
