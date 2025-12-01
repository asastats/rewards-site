


# Class: ActiveNetwork

Defined in: [src/ActiveNetwork.ts:16](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L16)

ActiveNetwork class manages network selection and display in the UI.

This class handles binding to DOM elements, rendering the current active network,
and providing click handlers for network selection. It also synchronizes
network changes with the backend server.

## Example

```typescript
const activeNetwork = new ActiveNetwork(walletManager)
activeNetwork.bind(document.getElementById('network-selector'))
```

## Constructors

### Constructor

> **new ActiveNetwork**(`manager`): `ActiveNetwork`

Defined in: [src/ActiveNetwork.ts:25](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L25)

Creates an instance of ActiveNetwork.

#### Parameters

##### manager

`WalletManager`

The WalletManager instance for wallet and network operations

#### Returns

`ActiveNetwork`

## Properties

### element

> `private` **element**: `HTMLElement` \| `null` = `null`

Defined in: [src/ActiveNetwork.ts:17](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L17)

***

### manager

> `private` **manager**: `WalletManager`

Defined in: [src/ActiveNetwork.ts:25](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L25)

The WalletManager instance for wallet and network operations

***

### unsubscribe

> `private` **unsubscribe**: () => `void` \| `null` = `null`

Defined in: [src/ActiveNetwork.ts:18](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L18)

## Methods

### bind()

> **bind**(`element`): `void`

Defined in: [src/ActiveNetwork.ts:36](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L36)

Binds the ActiveNetwork instance to a DOM element.

Sets up event listeners and subscribes to wallet manager state changes.
The element should contain network selection buttons with data-network attributes.

#### Parameters

##### element

`HTMLElement`

The HTMLElement to bind network controls to

#### Returns

`void`

#### Throws

If the element is null or invalid

***

### destroy()

> **destroy**(): `void`

Defined in: [src/ActiveNetwork.ts:114](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L114)

Cleans up event listeners and subscriptions.

Should be called when the ActiveNetwork instance is no longer needed
to prevent memory leaks and unwanted behavior.

#### Returns

`void`

***

### getCsrfToken()

> `private` **getCsrfToken**(): `string`

Defined in: [src/ActiveNetwork.ts:101](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L101)

Retrieves the CSRF token from cookies for API requests.

#### Returns

`string`

The CSRF token as a string

***

### handleClick()

> `private` **handleClick**(`e`): `Promise`\<`void`\>

Defined in: [src/ActiveNetwork.ts:54](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L54)

Handles click events on network selection buttons.

Updates the active network in the wallet manager and sends the change
to the backend server via API call.

#### Parameters

##### e

`Event`

The click event

#### Returns

`Promise`\<`void`\>

***

### render()

> `private` **render**(`activeNetwork`): `void`

Defined in: [src/ActiveNetwork.ts:86](https://github.com/asastats/rewards-suite/blob/main/rewardsweb/frontend/src/ActiveNetwork.ts#L86)

Renders the current active network state in the UI.

Updates the network display text and toggles disabled state
on network selection buttons.

#### Parameters

##### activeNetwork

The currently active network ID or null if none

`string` | `null`

#### Returns

`void`
