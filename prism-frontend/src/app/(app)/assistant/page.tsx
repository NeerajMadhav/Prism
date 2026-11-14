'use client';

import { useState } from 'react';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useLlmConfig, useLlmQuery } from '@/lib/hooks/useLlm';
import { useOrg } from '@/lib/hooks/useOrg';

export default function AssistantPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const config = useLlmConfig(orgId);
  const query = useLlmQuery(orgId);
  const [prompt, setPrompt] = useState('');
  const [answer, setAnswer] = useState('');

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="FinOps assistant" description="Ask questions about your cloud spend." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && config.isLoading ? <LoadingSkeleton variant="card" /> : null}
      {orgId && config.isError ? (
        <ErrorState error={config.error} retry={() => config.refetch()} />
      ) : null}
      {orgId && config.data && !config.data.configured ? (
        <EmptyState
          title="LLM not configured"
          message="Add provider credentials under Settings → LLM."
        />
      ) : null}
      {orgId && config.data?.configured ? (
        <>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="How did AWS spend change compared to last month?"
          />
          <Button
            disabled={!prompt.trim() || query.isPending}
            onClick={() =>
              query.mutate(
                { question: prompt },
                { onSuccess: (res) => setAnswer(res.answer) },
              )
            }
          >
            {query.isPending ? 'Thinking…' : 'Ask'}
          </Button>
          {answer ? (
            <div className="rounded-lg border bg-muted/30 p-4 text-sm whitespace-pre-wrap">
              {answer}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
