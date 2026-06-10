# Limitation: Error Handling System

## Package
`@backstage/errors`

## Source Files
- `packages/errors/src/errors/common.ts`
- `packages/errors/src/errors/CustomErrorBase.ts`
- `packages/errors/src/errors/ResponseError.ts`
- `packages/errors/src/serialization/error.ts`
- `packages/errors/src/serialization/response.ts`

---

## L-ERR-001: No Error Code in Business Errors

**Severity**: Medium  
**Type**: Design Limitation

The business error classes (`InputError`, `AuthenticationError`, `NotAllowedError`, `NotFoundError`, `ConflictError`, `NotModifiedError`, `NotImplementedError`, `ServiceUnavailableError`) do not carry a machine-readable error code. They rely solely on `name` for classification:

```typescript
export class InputError extends CustomErrorBase {
  name = 'InputError' as const;
}
```

**Impact**: 
- No granular error categorization (e.g., distinguishing "missing required field" from "invalid format")
- Error handling in consumers requires string comparison on `name`
- No standard way to attach domain-specific error codes

---

## L-ERR-002: `ResponseError.fromResponse` Assumes Body Not Consumed

**Severity**: Medium  
**Type**: API Contract

`ResponseError.fromResponse()` has a hard requirement documented in comments:

```typescript
// Assumes that the response has already been checked to be not ok.
// This function consumes the body of the response, and assumes that it hasn't been consumed before.
```

If the body has already been consumed (e.g., by logging middleware), `fromResponse` will silently produce a fallback error message with no details:

```typescript
return {
  error: { name: 'Error', message: `Request failed with status ${response.status} ${response.statusText}` },
  response: { statusCode: response.status },
};
```

**Impact**: Error details are silently lost when middleware or interceptors consume the response body before error handling.

---

## L-ERR-003: Error Serialization Depends on Third-Party Library

**Severity**: Low  
**Type**: Dependency Risk

Error serialization/deserialization relies on the `serialize-error` package:

```typescript
import { deserializeError as deserializeErrorInternal, serializeError as serializeErrorInternal } from 'serialize-error';
```

**Impact**: 
- Version changes in `serialize-error` can affect error round-tripping behavior
- The library's serialization format becomes part of Backstage's wire protocol between frontend and backend

---

## L-ERR-004: Stack Traces Stripped by Default

**Severity**: Low  
**Type**: Design Decision

`serializeError()` strips stack traces by default (line 61):

```typescript
if (!options?.includeStack) {
  delete result.stack;
  if (result.cause && typeof result.cause === 'object' && 'stack' in result.cause) {
    delete result.cause.stack;
  }
}
```

**Impact**: When debugging issues across plugin boundaries (frontend ↔ backend), stack traces are unavailable in serialized errors unless explicitly opted in. This makes production debugging harder.

---

## L-ERR-005: `parseErrorResponseBody` Swallows Parsing Failures Silently

**Severity**: Medium  
**Type**: Error Handling

The `parseErrorResponseBody()` function has two empty `catch` blocks:

```typescript
try {
  const body = JSON.parse(text);
  if (body.error && body.response) { return body; }
} catch {
  // ignore
}
// ...
} catch {
  // ignore
}
```

**Impact**: If the server returns a non-JSON error body (e.g., HTML from a reverse proxy), the actual error details are discarded and replaced with a generic "Request failed with status" message. No logging or telemetry captures the original error body.

---

## L-ERR-006: `CustomErrorBase.cause` Coerces Non-Error Causes

**Severity**: Low  
**Type**: Design Quirk

The `CustomErrorBase` constructor converts any `cause` value to an `Error` via `toError()`. If a string or object is passed as cause, it gets wrapped, potentially losing information:

```typescript
const causeError = cause !== undefined ? toError(cause) : undefined;
```

**Impact**: When third-party code throws non-Error values (strings, plain objects), the original value's structure may be altered during wrapping.

---

## L-ERR-007: `ConsumedResponse` Type Includes Mutable Methods

**Severity**: Low  
**Type**: Type Safety

The `ConsumedResponse` type includes mutable header methods (`append`, `delete`, `set`) on what should be a read-only consumed response:

```typescript
export type ConsumedResponse = {
  readonly headers: {
    append(name: string, value: string): void;
    delete(name: string): void;
    set(name: string, value: string): void;
    // ...
  };
};
```

**Impact**: Consumers can inadvertently mutate headers on a response that's already been consumed, leading to potential bugs in middleware chains.

---

## L-ERR-008: No Retry/Rate-Limit Error Types

**Severity**: Medium  
**Type**: Missing Feature

The error hierarchy is missing common error types needed for production resilience:
- `RateLimitError` (HTTP 429)
- `TimeoutError` (HTTP 408 / operation timeouts)
- `GatewayError` (HTTP 502/503/504 upstream failures)

**Impact**: Plugins must create custom error types or misuse existing ones (e.g., `ServiceUnavailableError`) for these common scenarios, leading to inconsistent error handling across the ecosystem.
