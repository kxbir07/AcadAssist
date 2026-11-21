# AcadAssist — Azure Connectivity & Fallback Audit (Part 7)

## 1. Service-by-Service Connectivity Matrix

| Azure Service | Configured in `.env`? | Credentials Present? | Auth Mechanism | Live Connectivity Verified? | Active Runtime Mode | Remaining Cloud Config Needed (Optional) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Azure Blob Storage** (`acadassiststoragekc26` / `study-materials`) | Yes (`AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_CONTAINER`) | `AZURE_STORAGE_CONNECTION_STRING` is empty; relies on `DefaultAzureCredential` (`az login`) | `DefaultAzureCredential` or Connection String | No in offline sandbox; caches unreachable status after first check | **Local Filesystem Fallback** (`./data/storage`) | Run `az login` with Storage Blob Data Contributor role or set `AZURE_STORAGE_CONNECTION_STRING` |
| **Azure AI Search** (`acadassist-search-kc26.search.windows.net` / `acadassist-index`) | Yes (`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME`) | `AZURE_SEARCH_KEY` is empty; relies on `DefaultAzureCredential` | `AzureKeyCredential` or `DefaultAzureCredential` | No in offline sandbox; caches unreachable status after first check | **Local Hybrid Search Fallback** (`LocalHybridSearchIndex`: cosine vector + BM25 RRF + SQLite `document_chunks`) | Set `AZURE_SEARCH_KEY` or grant Search Index Data Contributor via `az login` |
| **Microsoft Foundry Agent Service** (`acadassist-foundry-kc26.services.ai.azure.com`) | Yes (`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_AGENT_NAME=AcadAssist`, `FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini`) | Entra ID (`DefaultAzureCredential`) required for `AIProjectClient` | `DefaultAzureCredential` | No in offline sandbox; caches unreachable status after first check | **Direct Azure OpenAI API-Key Fallback → Local Grounded RAG Synthesis** | Run `az login` with Azure AI Developer role on the Foundry project |
| **Azure OpenAI Chat & Embeddings** (`acadassist-foundry-kc26.cognitiveservices.azure.com`) | Yes (`AZURE_OPENAI_ENDPOINT`, `FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-small`) | Yes (`AZURE_OPENAI_API_KEY` is configured in `.env`) | API Key (`AzureOpenAI`) or `DefaultAzureCredential` | Requires outbound internet to `*.cognitiveservices.azure.com` | **Online: Azure OpenAI (`gpt-4.1-mini` / `text-embedding-3-small`)**<br>**Offline: Deterministic 1536-dim Local Embeddings & Grounded Chunk Synthesis** | Outbound internet access to `acadassist-foundry-kc26.cognitiveservices.azure.com` |

---

## 2. Architectural Safeguards Implemented

1. **Zero Secret Exposure**: `.env` is preserved untouched with no secrets hardcoded in source files or documentation.
2. **Endpoint Sanitization**: `app/config.py` strips stray quotes and whitespace from `FOUNDRY_PROJECT_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_SEARCH_ENDPOINT`.
3. **Single-Probe Failure Caching in Development**:
   - Previously, when running offline or without `az login`, every document chunk upload, search query, and chat message re-triggered `DefaultAzureCredential` network probes, causing multi-second delays.
   - Now, `AzureStorageService`, `AzureSearchService`, `EmbeddingService`, and `AcadAssistAgentService` cache `_cloud_unreachable = True` after the first failed connection attempt in `development` mode and immediately route subsequent operations to the local fallback.
4. **Production Enforcement Preserved**: When `ENVIRONMENT=production`, local fallbacks are not silently substituted for missing cloud infrastructure, preserving strict production fail-fast semantics.
