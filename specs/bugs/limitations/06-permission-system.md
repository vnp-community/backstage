# Limitation: Permission System

## Package
`@backstage/backend-plugin-api` (PermissionsService, PermissionsRegistryService)

## Source Files
- `packages/backend-plugin-api/src/services/definitions/PermissionsService.ts`
- `packages/backend-plugin-api/src/services/definitions/PermissionsRegistryService.ts`
- `packages/backend-plugin-api/src/services/definitions/AuthService.ts`
- `packages/backend-plugin-api/src/services/definitions/HttpAuthService.ts`

---

## L-PRM-001: No Fine-Grained Field-Level Permissions

**Severity**: High  
**Type**: Design Limitation

The permission system operates at the resource level (`ResourcePermission`), not at the field level. There is no built-in mechanism to restrict access to individual fields of an entity or API response.

**Impact**:
- Cannot implement "user can see the entity but not its secrets" patterns
- All-or-nothing access to resources
- Sensitive fields must be separated into different resource types

---

## L-PRM-002: Permission Evaluation Requires Round-Trip

**Severity**: Medium  
**Type**: Performance

Permission checks go through the `PermissionsService.authorize()` method, which may involve network calls to the permission backend:

```typescript
authorize(
  requests: AuthorizePermissionRequest[],
  options: PermissionsServiceRequestOptions,
): Promise<AuthorizePermissionResponse[]>;
```

**Impact**:
- Latency added to every authorized endpoint
- No local caching strategy built into the service interface
- Batching helps but still requires at least one network call per batch

---

## L-PRM-003: `getResources` is Optional in Resource Type Registration

**Severity**: Medium  
**Type**: Incomplete API

The `getResources` function in resource type registration is optional:

```typescript
getResources?(resourceRefs: string[]): Promise<Array<NoInfer<TResource> | undefined>>;
```

The docs state:
> "If this function is not provided the permission system will not be able to resolve conditional decisions except when requesting resources directly from the plugin."

**Impact**: Without `getResources`, conditional permissions cannot be evaluated by the central permission backend. This silently degrades permission enforcement.

---

## L-PRM-004: Access Restrictions Limited to Permission Names and Actions

**Severity**: Medium  
**Type**: Design Limitation

`BackstagePrincipalAccessRestrictions` can only restrict by permission names and actions:

```typescript
export type BackstagePrincipalAccessRestrictions = {
  permissionNames?: string[];
  permissionAttributes?: {
    action?: Array<Required<PermissionAttributes>['action']>;
  };
};
```

**Impact**:
- Cannot restrict by resource type, namespace, or entity kind
- Cannot restrict by time window (e.g., "only during business hours")
- Cannot restrict by IP range or network zone
- Access restrictions are coarse-grained

---

## L-PRM-005: HttpAuthPolicy Only Supports Two Allow Modes

**Severity**: Medium  
**Type**: Design Limitation

The HTTP auth policy only allows two modes:

```typescript
export interface HttpRouterServiceAuthPolicy {
  path: string;
  allow: 'unauthenticated' | 'user-cookie';
}
```

**Impact**:
- Cannot express "authenticated but any role" (without using the full permission system)
- No API key authentication mode
- No mutual TLS authentication mode
- No webhook signature verification mode

---

## L-PRM-006: Service Principal `subject` Has No Defined Semantics

**Severity**: Low  
**Type**: Design Weakness

The `BackstageServicePrincipal.subject` field explicitly disclaims any semantics:

```typescript
export type BackstageServicePrincipal = {
  type: 'service';
  subject: string; // Exact format TBD, possibly 'plugin:<pluginId>' or 'external:<externalServiceId>'
};
```

The comment says:
> "This string is only informational, has no well defined semantics, and should never be used to drive actual logic in code."

**Impact**: 
- Cannot reliably identify which service is making a request
- Service-to-service authorization must rely on other mechanisms
- The "TBD" format has not been finalized despite being in production

---

## L-PRM-007: No Permission Inheritance or Hierarchy

**Severity**: High  
**Type**: Missing Feature

The permission system has no concept of role hierarchy or permission inheritance. Each permission must be explicitly granted.

**Impact**:
- "Admin" role must have every permission individually listed
- Changes to permission sets require updating all policies
- No group-based permission delegation (e.g., "team leads inherit viewer + editor")

---

## L-PRM-008: Principal Check Missing Self-Verification

**Severity**: Low  
**Type**: Incomplete Implementation

Documented in `DefaultAuthService.ts`:

```typescript
// TODO: Check whether the principal is ourselves
```

**Impact**: A service cannot reliably determine if the incoming credentials represent itself, potentially leading to unnecessary permission checks on self-calls.
