/** PRISM FinOps — scheduled report hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as reportsApi from '@/lib/api/reports';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { UpdateReportConfig } from '@/types/reports';

export function useReports(orgId: string) {
  return useQuery({
    queryKey: queryKeys.reports(orgId),
    queryFn: () => reportsApi.get(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useUpdateReports(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateReportConfig) => reportsApi.update(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.reports(orgId) });
      toast.success('Report schedule saved');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useSendReportNow(orgId: string) {
  return useMutation({
    mutationFn: () => reportsApi.sendNow(orgId),
    onSuccess: () => toast.success('Report queued for delivery'),
    onError: (error) => handleApiError(error),
  });
}

export function useReportPreview(orgId: string, enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.reports(orgId), 'preview'],
    queryFn: () => reportsApi.preview(orgId),
    enabled: Boolean(orgId) && enabled,
    staleTime: STALE_TIMES.settings,
  });
}

export function useDownloadReportPdf(orgId: string) {
  return useMutation({
    mutationFn: async () => {
      const blob = await reportsApi.downloadPdf(orgId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prism-report-${new Date().toISOString().slice(0, 7)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => toast.success('PDF downloaded'),
    onError: (error) => handleApiError(error),
  });
}
