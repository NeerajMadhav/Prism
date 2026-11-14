/** PRISM FinOps — multi-account connect wizard (N accounts per provider). */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMemo, useState, type FormEvent } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ROUTES } from '@/lib/constants/routes';
import { useConnectAccount } from '@/lib/hooks/useAccounts';
import { useAuthStore } from '@/lib/store/authStore';
import type { ConnectRequest, Provider } from '@/types/accounts';

const PROVIDERS: { id: Provider; label: string; hint: string }[] = [
  { id: 'aws', label: 'Amazon Web Services', hint: 'Cross-account role ARN + external ID' },
  { id: 'azure', label: 'Microsoft Azure', hint: 'Service principal + subscription' },
  { id: 'gcp', label: 'Google Cloud', hint: 'Billing export dataset + service account JSON' },
];

export default function ConnectAccountPage() {
  const router = useRouter();
  const orgId = useAuthStore((s) => s.org?.id);
  const connect = useConnectAccount(orgId);
  const [step, setStep] = useState<1 | 2>(1);
  const [provider, setProvider] = useState<Provider>('aws');
  const [displayName, setDisplayName] = useState('');
  const [scope, setScope] = useState('production');
  const [error, setError] = useState<string | null>(null);

  // AWS
  const [roleArn, setRoleArn] = useState('');
  const [externalId, setExternalId] = useState('');
  const [awsRegion, setAwsRegion] = useState('us-east-1');

  // Azure
  const [tenantId, setTenantId] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [subscriptionId, setSubscriptionId] = useState('');

  // GCP
  const [projectId, setProjectId] = useState('');
  const [datasetId, setDatasetId] = useState('');
  const [tablePrefix, setTablePrefix] = useState('gcp_billing_export');
  const [saJson, setSaJson] = useState('');

  const providerMeta = useMemo(
    () => PROVIDERS.find((p) => p.id === provider)!,
    [provider],
  );

  function buildBody(): ConnectRequest | null {
    const name = displayName.trim();
    if (!name) {
      setError('Display name is required (e.g. Prod AWS, Staging AWS).');
      return null;
    }
    if (provider === 'aws') {
      if (!roleArn.trim() || !externalId.trim()) {
        setError('AWS role ARN and external ID are required.');
        return null;
      }
      return {
        provider: 'aws',
        display_name: name,
        scope: scope.trim() || 'production',
        credentials: {
          role_arn: roleArn.trim(),
          external_id: externalId.trim(),
          region: awsRegion.trim() || 'us-east-1',
        },
      };
    }
    if (provider === 'azure') {
      if (!tenantId || !clientId || !clientSecret || !subscriptionId) {
        setError('All Azure fields are required.');
        return null;
      }
      return {
        provider: 'azure',
        display_name: name,
        scope: scope.trim() || 'production',
        credentials: {
          tenant_id: tenantId.trim(),
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
          subscription_id: subscriptionId.trim(),
        },
      };
    }
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(saJson) as Record<string, unknown>;
    } catch {
      setError('Service account JSON is invalid.');
      return null;
    }
    if (!projectId || !datasetId) {
      setError('GCP project ID and dataset ID are required.');
      return null;
    }
    return {
      provider: 'gcp',
      display_name: name,
      scope: scope.trim() || 'production',
      credentials: {
        project_id: projectId.trim(),
        dataset_id: datasetId.trim(),
        table_prefix: tablePrefix.trim() || 'gcp_billing_export',
        service_account_json: parsed,
      },
    };
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const body = buildBody();
    if (!body || !orgId) return;
    try {
      await connect.mutateAsync(body);
      router.push(ROUTES.accounts);
    } catch {
      setError('Could not connect account. Check credentials or duplicate cloud account ID.');
    }
  }

  return (
    <div className="animate-slide-up mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Connect Account"
        description="Add another AWS, Azure, or GCP account anytime — same provider is allowed when cloud IDs differ."
        actions={
          <Button variant="outline" render={<Link href={ROUTES.accounts} />}>
            Back
          </Button>
        }
      />

      {step === 1 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Step 1 — Choose provider</p>
          <div className="grid gap-3">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`rounded-lg border p-4 text-left transition hover:border-primary ${
                  provider === p.id ? 'border-primary bg-accent/40' : ''
                }`}
                onClick={() => setProvider(p.id)}
              >
                <div className="font-medium">{p.label}</div>
                <div className="text-xs text-muted-foreground">{p.hint}</div>
              </button>
            ))}
          </div>
          <Button type="button" onClick={() => setStep(2)}>
            Continue
          </Button>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={onSubmit}>
          <p className="text-sm text-muted-foreground">
            Step 2 — {providerMeta.label} credentials
          </p>
          <div className="space-y-2">
            <Label htmlFor="display_name">Display name</Label>
            <Input
              id="display_name"
              placeholder="e.g. Prod AWS"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="scope">Scope / environment</Label>
            <Input
              id="scope"
              placeholder="production"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            />
          </div>

          {provider === 'aws' ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="role_arn">Role ARN</Label>
                <Input
                  id="role_arn"
                  value={roleArn}
                  onChange={(e) => setRoleArn(e.target.value)}
                  placeholder="arn:aws:iam::123456789012:role/PrismCostRole"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="external_id">External ID</Label>
                <Input
                  id="external_id"
                  value={externalId}
                  onChange={(e) => setExternalId(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="aws_region">Region</Label>
                <Input
                  id="aws_region"
                  value={awsRegion}
                  onChange={(e) => setAwsRegion(e.target.value)}
                />
              </div>
            </>
          ) : null}

          {provider === 'azure' ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="tenant_id">Tenant ID</Label>
                <Input id="tenant_id" value={tenantId} onChange={(e) => setTenantId(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="client_id">Client ID</Label>
                <Input id="client_id" value={clientId} onChange={(e) => setClientId(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="client_secret">Client secret</Label>
                <Input
                  id="client_secret"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="subscription_id">Subscription ID</Label>
                <Input
                  id="subscription_id"
                  value={subscriptionId}
                  onChange={(e) => setSubscriptionId(e.target.value)}
                />
              </div>
            </>
          ) : null}

          {provider === 'gcp' ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="project_id">Project ID</Label>
                <Input
                  id="project_id"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dataset_id">Billing dataset ID</Label>
                <Input
                  id="dataset_id"
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="table_prefix">Table prefix</Label>
                <Input
                  id="table_prefix"
                  value={tablePrefix}
                  onChange={(e) => setTablePrefix(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sa_json">Service account JSON</Label>
                <textarea
                  id="sa_json"
                  className="min-h-32 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                  value={saJson}
                  onChange={(e) => setSaJson(e.target.value)}
                  placeholder='{"type":"service_account",...}'
                />
              </div>
            </>
          ) : null}

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button type="submit" disabled={connect.isPending || !orgId}>
              {connect.isPending ? 'Connecting…' : 'Connect account'}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
