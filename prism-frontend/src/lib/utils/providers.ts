/** PRISM FinOps — cloud provider display helpers. */

import type { Provider } from '@/types/api';

export const ALL_PROVIDERS: Provider[] = ['aws', 'azure', 'gcp'];

export const CHART_COLORS = [
  '#6366F1',
  '#22C55E',
  '#F59E0B',
  '#3B82F6',
  '#EC4899',
  '#8B5CF6',
  '#14B8A6',
  '#F97316',
] as const;

const PROVIDER_COLORS: Record<Provider, string> = {
  aws: '#FF9900',
  azure: '#0078D4',
  gcp: '#34A853',
};

const PROVIDER_LABELS: Record<Provider, string> = {
  aws: 'AWS',
  azure: 'Azure',
  gcp: 'Google Cloud',
};

/** Returns the brand hex color for a provider. */
export function getProviderColor(provider: string): string {
  if (isValidProvider(provider)) {
    return PROVIDER_COLORS[provider];
  }
  return '#6B7280';
}

/** Returns the display label for a provider. */
export function getProviderLabel(provider: string): string {
  if (isValidProvider(provider)) {
    return PROVIDER_LABELS[provider];
  }
  return provider;
}

/** Returns the public path to a provider logo asset. */
export function getProviderLogo(provider: string): string {
  if (isValidProvider(provider)) {
    return `/providers/${provider}.svg`;
  }
  return '/providers/unknown.svg';
}

/** Type guard for known cloud providers. */
export function isValidProvider(str: string): str is Provider {
  return ALL_PROVIDERS.includes(str as Provider);
}
