


# Class: App

Defined in: [src/main.ts:23](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L23)

Main application class that orchestrates the entire frontend application.

This class initializes all components, manages wallet connections, and
coordinates between different parts of the application. It handles the
complete lifecycle of the application including initialization, component
binding, and cleanup.

## Example

```typescript
// The application auto-initializes on DOMContentLoaded
const app = new App()
```

## Constructors

### Constructor

> **new App**(): `App`

Defined in: [src/main.ts:38](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L38)

Creates an instance of App.
Sets up the DOMContentLoaded event listener for initialization.

#### Returns

`App`

## Properties

### activeNetworkComponent

> `private` **activeNetworkComponent**: [`ActiveNetwork`](../../ActiveNetwork/classes/ActiveNetwork.md) \| `null` = `null`

Defined in: [src/main.ts:28](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L28)

***

### addAllocationsComponent

> `private` **addAllocationsComponent**: [`AddAllocationsComponent`](../../AddAllocationsComponent/classes/AddAllocationsComponent.md) \| `null` = `null`

Defined in: [src/main.ts:31](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L31)

***

### claimComponent

> `private` **claimComponent**: [`ClaimComponent`](../../ClaimComponent/classes/ClaimComponent.md) \| `null` = `null`

Defined in: [src/main.ts:30](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L30)

***

### reclaimAllocationsComponent

> `private` **reclaimAllocationsComponent**: [`ReclaimAllocationsComponent`](../../ReclaimAllocationsComponent/classes/ReclaimAllocationsComponent.md) \| `null` = `null`

Defined in: [src/main.ts:32](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L32)

***

### walletComponents

> `private` **walletComponents**: [`WalletComponent`](../../WalletComponent/classes/WalletComponent.md)[] = `[]`

Defined in: [src/main.ts:29](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L29)

***

### walletManager

> **walletManager**: `WalletManager` \| `null` = `null`

Defined in: [src/main.ts:25](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L25)

The wallet manager instance for handling multiple wallets

## Methods

### init()

> **init**(): `Promise`\<`void`\>

Defined in: [src/main.ts:53](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/main.ts#L53)

Initializes the application by setting up wallets, components, and event handlers.

This method:
- Fetches initial wallet and network data from the backend
- Initializes the WalletManager with available wallets
- Binds all UI components to their respective DOM elements
- Sets up cleanup handlers for page unload

#### Returns

`Promise`\<`void`\>

#### Throws

When initial data fetching fails
