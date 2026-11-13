/** PRISM FinOps — provider constants for forms and filters. */

import { ALL_PROVIDERS } from '@/lib/utils/providers';
import type { Provider } from '@/types/api';

export const PROVIDER_OPTIONS: { value: Provider; label: string }[] =
  ALL_PROVIDERS.map((provider) => ({
    value: provider,
    label: provider === 'gcp' ? 'Google Cloud' : provider.toUpperCase(),
  }));
