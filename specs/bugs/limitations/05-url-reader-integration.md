# Limitation: URL Reader & Integration System

## Package
`@backstage/backend-plugin-api` (UrlReaderService), `@backstage/integration`

## Source Files
- `packages/backend-plugin-api/src/services/definitions/UrlReaderService.ts`
- `packages/integration/src/types.ts`
- `packages/integration/src/ScmIntegrations.ts`
- `packages/backend-defaults/src/entrypoints/urlReader/lib/*.ts`

---

## L-URL-001: Azure URL Reader Missing ETag Support

**Severity**: Medium  
**Type**: Missing Feature

Documented directly in the code:

```typescript
// TODO etag is not implemented yet.
```

Found in `AzureUrlReader.ts` lines 87 and 128.

**Impact**: Cannot use ETag-based caching for Azure DevOps content, leading to redundant downloads during catalog ingestion.

---

## L-URL-002: Google GCS URL Reader Missing ETag Support

**Severity**: Medium  
**Type**: Missing Feature

Documented directly in the code:

```typescript
// TODO etag is not implemented yet.
```

Found in `GoogleGcsUrlReader.ts` lines 131 and 219.

**Impact**: Same as Azure — no change detection for GCS-hosted content.

---

## L-URL-003: Azure URL Reader Lacks Filepath-Based Tree Reading

**Severity**: Medium  
**Type**: Missing Feature

```typescript
// TODO: Support filepath based reading tree feature like other providers
```

Found in `AzureUrlReader.ts` line 128.

**Impact**: Cannot read a specific subdirectory from an Azure DevOps repo — must download the entire repo archive.

---

## L-URL-004: BitbucketServer/Azure/BitbucketCloud Search Reads Entire Repo

**Severity**: High  
**Type**: Performance

Multiple URL readers have the same limitation:

```typescript
// TODO(freben): For now, read the entire repo and filter through that. In
// a more optimal solution we could be smart and use the GitHub tree endpoint.
```

Found in `BitbucketServerUrlReader.ts`, `AzureUrlReader.ts`, and `BitbucketCloudUrlReader.ts`.

**Impact**: 
- Search operations download entire repository archives into memory
- Extremely slow for large repos (100+ MB)
- Causes high memory spikes that can OOM the backend

---

## L-URL-005: AbortSignal Support is Inconsistent

**Severity**: Medium  
**Type**: Inconsistent API

The `UrlReaderServiceReadUrlOptions` documents:

```typescript
signal?: AbortSignal;
// Not all reader implementations may take this field into account.
```

**Impact**: Callers cannot reliably cancel long-running URL reads. Some providers respect the signal, others ignore it.

---

## L-URL-006: `readTree.dir()` Caller Must Clean Up

**Severity**: Medium  
**Type**: Resource Management

The `dir()` method on tree responses has a documented responsibility:

```typescript
/**
 * Extracts the tree response into a directory and returns the path of the directory.
 * **NOTE**: It is the responsibility of the caller to remove the directory after use.
 */
dir(options?: UrlReaderServiceReadTreeResponseDirOptions): Promise<string>;
```

**Impact**: 
- No automatic cleanup — leaked temp directories accumulate on disk
- No finalizer or disposable pattern
- Crash during processing leaves orphaned directories

---

## L-URL-007: Signal Casting Workaround for node-fetch

**Severity**: Low  
**Type**: Technical Debt

Multiple URL readers contain the same workaround comment:

```typescript
// TODO(freben): The signal cast is there because pre-3.x versions of
// node-fetch has a slightly different AbortSignal type signature
```

Found across GerritUrlReader, GithubUrlReader, BitbucketServerUrlReader, AzureUrlReader, BitbucketCloudUrlReader, GitlabUrlReader, and FetchUrlReader.

**Impact**: Type safety is compromised by casting; the workaround should have been resolved when upgrading to node-fetch 3.x or native fetch.

---

## L-URL-008: Limited SCM Provider Support

**Severity**: Medium  
**Type**: Ecosystem Gap

The integration package supports only 12 SCM providers:
- GitHub, GitLab, Azure, Bitbucket Cloud, Bitbucket Server
- Gerrit, Gitea, AWS CodeCommit, Harness
- AWS S3, Azure Blob Storage, Google GCS (storage only)

**Impact**:
- No support for SourceForge, Codeberg, Forgejo, Gogs, or other Git hosting
- No support for generic Git over SSH/HTTPS without provider-specific integration
- Adding a new provider requires deep knowledge of the integration registry
