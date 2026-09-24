/**
 * Azure and Foundry Integration Configuration
 * Prepared for Person 1 integration.
 * NOTE: Never commit secrets to frontend code.
 * Browser-facing VITE_* variables must not contain private keys or SAS tokens with full access.
 */

export interface AzureIntegrationConfig {
  openAiEndpoint?: string;
  foundryAgentId?: string;
  blobStorageUrl?: string;
  isConfigured: boolean;
}

export function getAzureConfig(): AzureIntegrationConfig {
  const openAiEndpoint = import.meta.env.VITE_AZURE_OPENAI_ENDPOINT || '';
  const foundryAgentId = import.meta.env.VITE_AZURE_FOUNDRY_AGENT_ID || '';
  const blobStorageUrl = import.meta.env.VITE_AZURE_BLOB_STORAGE_URL || '';

  return {
    openAiEndpoint: openAiEndpoint || undefined,
    foundryAgentId: foundryAgentId || undefined,
    blobStorageUrl: blobStorageUrl || undefined,
    isConfigured: Boolean(openAiEndpoint || foundryAgentId || blobStorageUrl),
  };
}
