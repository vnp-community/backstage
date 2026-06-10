# Limitation: Signals & Real-Time Communication

## Package
`@backstage/plugin-signals-backend`, `@backstage/plugin-signals-node`

## Source Files
- `plugins/signals-backend/src/service/SignalManager.ts`
- `plugins/signals-backend/src/service/router.ts`

---

## L-SIG-001: All Connections Stored In-Memory

**Severity**: Critical  
**Type**: Scalability

All WebSocket connections are stored in a `Map` in the process memory:

```typescript
private connections: Map<string, SignalConnection> = new Map<string, SignalConnection>();
```

**Impact**:
- Cannot run signals-backend in a multi-replica deployment without all replicas receiving all events
- Memory grows linearly with active WebSocket connections
- A process restart drops all active connections immediately
- No connection persistence or reconnection token support

---

## L-SIG-002: Fan-Out Only by EventsService Subscription

**Severity**: Medium  
**Type**: Design Limitation

In a scaled deployment, each signals instance subscribes with a unique ID to ensure fan-out:

```typescript
// Use a unique subscriber ID for each signals instance, in order to fan-out
// all events to each signals instance. This ensures that events always
// reach users in a scaled deployment.
const id = `signals-${crypto.randomBytes(8).toString('hex')}`;
```

**Impact**:
- The solution relies entirely on the `EventsService` backend broadcasting to all subscribers
- If the events backend uses in-memory pub/sub (default), cross-process fan-out does NOT work
- Requires an external event broker (Kafka, Google Pub/Sub, AWS SQS) for true multi-replica support

---

## L-SIG-003: Ping Interval Only Starts on First Connection

**Severity**: Low  
**Type**: Code Logic

The WebSocket ping interval starts only on the first connection and never stops:

```typescript
addConnection(ws: WebSocket, identity?: BackstageUserInfo) {
  // Start pinging on first connection
  if (!this.pingInterval) {
    this.pingInterval = setInterval(() => this.ping(), 30000);
  }
```

**Impact**:
- If all connections disconnect, the ping interval continues running indefinitely
- The `onShutdown()` method clears the interval, but normal operation leaves it running with zero connections
- Wasteful polling even when no clients are connected

---

## L-SIG-004: Event Unsubscription Not Implemented

**Severity**: Medium  
**Type**: Resource Leak

On shutdown, the `onShutdown()` method has a documented gap:

```typescript
private onShutdown() {
  if (this.pingInterval) {
    clearInterval(this.pingInterval);
  }
  // TODO: Unsubscribe from events?
  this.connections.forEach(conn => { conn.ws.terminate(); });
  this.connections.clear();
}
```

**Impact**:
- After shutdown, the signals instance may still receive events from the EventsService broker
- In environments where the event broker keeps subscriptions alive, this is a resource leak
- No proper cleanup of event subscription on graceful shutdown

---

## L-SIG-005: Binary Messages Silently Ignored

**Severity**: Low  
**Type**: Design Gap

Binary WebSocket messages are silently dropped:

```typescript
ws.on('message', (data: RawData, isBinary: boolean) => {
  if (isBinary) {
    return;  // silently ignored
  }
```

**Impact**:
- No error or warning sent back to the client
- Plugin authors trying to send binary payloads (e.g., compressed messages) get no feedback

---

## L-SIG-006: No Message Delivery Guarantee

**Severity**: High  
**Type**: Reliability

WebSocket message delivery is fire-and-forget with only basic error logging:

```typescript
conn.ws.send(jsonMessage, err => {
  if (err) {
    this.logger.error(`Failed to send message to ${conn.id}: ${err}`);
  }
});
```

**Impact**:
- Failed deliveries are only logged — not retried
- No message queue or buffer for temporarily-disconnected clients
- Clients that miss messages during disconnection must re-fetch state manually

---

## L-SIG-007: Recipient Filtering Uses Ownership Entity Refs Only

**Severity**: Medium  
**Type**: Design Limitation

Signal targeting is limited to user entity refs and ownership refs:

```typescript
if (
  recipients.type !== 'broadcast' &&
  !conn.ownershipEntityRefs.some((ref: string) => users.includes(ref))
) {
  return;
}
```

**Impact**:
- Cannot target signals by group membership, role, or namespace
- No support for dynamic recipient resolution (e.g., "all users with permission X")
- `broadcast` sends to ALL connected users regardless of subscription — no channel scoping

---

## L-SIG-008: No WebSocket Payload Size Limit

**Severity**: Medium  
**Type**: Security / Reliability

There is no documented or enforced limit on incoming WebSocket message size:

```typescript
ws.on('message', (data: RawData, isBinary: boolean) => {
  const json = JSON.parse(data.toString()) as JsonObject;
  this.handleMessage(conn, json);
```

**Impact**:
- A malicious or misbehaving client can send extremely large payloads
- `JSON.parse` on a very large string can block the event loop
- Potential for memory exhaustion via large message flooding
