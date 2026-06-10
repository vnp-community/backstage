# AI Issue #002: Extreme TypeScript Generics Complexity

## Severity: Critical
## Category: Code Comprehension

## Problem

Backstage frontend plugin API sử dụng **TypeScript generics cực kỳ phức tạp** với nhiều lớp type manipulation nâng cao mà hầu hết AI models đều gặp khó khăn hoặc không thể resolve chính xác.

### Evidence

1. **`createExtension.ts` (812 lines)** — một file chứa type definitions phức tạp nhất:

   ```typescript
   // 8 generic parameters cho 1 function
   export function createExtension<
     UOutput extends ExtensionDataRef,
     TInputs extends { [inputName in string]: ExtensionInput },
     UFactoryOutput extends ExtensionDataValue<any, any>,
     const TKind extends string | undefined = undefined,
     const TName extends string | undefined = undefined,
     UParentInputs extends ExtensionDataRef = ExtensionDataRef,
     TNewConfigSchema extends { [key: string]: StandardSchemaV1 } = {},
   >(...): OverridableExtensionDefinition<{...}>
   ```

2. **Union-to-intersection type tricks**:
   ```typescript
   type ToIntersection<U> = (U extends any ? (k: U) => void : never) extends (
     k: infer I,
   ) => void ? I : never;
   
   type PopUnion<U> = ToIntersection<
     U extends any ? () => U : never
   > extends () => infer R
     ? [rest: Exclude<U, R>, next: R]
     : undefined;
   ```

3. **Recursive template literal types**:
   ```typescript
   type JoinStringUnion<
     U,
     TDiv extends string = ', ',
     TResult extends string = '',
   > = PopUnion<U> extends [infer IRest extends string, infer INext extends string]
     ? TResult extends '' ? JoinStringUnion<IRest, TDiv, INext>
       : JoinStringUnion<IRest, TDiv, `${TResult}${TDiv}${INext}`>
     : TResult;
   ```

4. **Verify types trả về error strings thay vì TypeScript errors**:
   ```typescript
   type VerifyExtensionFactoryOutput<UDeclaredOutput, UFactoryOutput> = 
     [RequiredExtensionIds<UDeclaredOutput>] extends [UFactoryOutput['id']]
       ? [UFactoryOutput['id']] extends [UDeclaredOutput['id']]
         ? {}
         : `Error: The extension factory has undeclared output(s): ${JoinStringUnion<...>}`
       : `Error: The extension factory is missing the following output(s): ${JoinStringUnion<...>}`
   ```

5. **`createExtensionBlueprint.ts` (796 lines)** — tương tự complex:
   - 8+ generic parameters
   - Nested conditional types 4-5 levels deep
   - `ExtensionBlueprintDefineParams` — callback-based params definition system

6. **`override()` method trên `OverridableExtensionDefinition`** — ~200 lines của pure type definition:
   - Duplicated overload signatures cho deprecated và new config schema
   - Conditional types dựa vào `[T['params']] extends [never]`
   - String literal error types cho invalid usage

## Impact on AI

- **Không thể resolve inferred types**: AI models thường fail khi cần resolve type output của `createExtension()` với specific parameters
- **Function overloads gây confusion**: Mỗi factory function có 2-3 overloads (deprecated + new config), AI chọn sai overload
- **Conditional type evaluation**: AI không thể evaluate `VerifyExtensionFactoryOutput` để biết output type hợp lệ hay không
- **`as any` casts trong implementation**: 20+ `as any` trong wiring/*.ts files, meaning AI phải infer types thay vì đọc declarations
- **Error-as-type pattern**: `'Error: This blueprint uses advanced parameter types...'` — AI model có thể hiểu nhầm string literal type là value

## Affected Files (ranked by complexity)

| File | Lines | Generic Params | Overloads |
|------|-------|----------------|-----------|
| `frontend-plugin-api/src/wiring/createExtension.ts` | 812 | 8+ | 3 |
| `frontend-plugin-api/src/wiring/createExtensionBlueprint.ts` | 796 | 8+ | 2 |
| `backend-plugin-api/src/services/system/types.ts` | 321 | 5+ | 5 |
| `frontend-plugin-api/src/wiring/createFrontendPlugin.ts` | ~300 | 4+ | 2 |
