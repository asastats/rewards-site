# Rewards Suite smart contract

This directory contains smart contract written in Puya for the Algorand blockchain that is used for allocation of rewards in the Rewards Suite.

## Features

- **Admin-managed:** A single admin account is responsible for setting up the contract and allocating tokens.
- **Batch Allocations:** The admin can add or update token allocations for multiple users in a single transaction.
- **User Claims:** Users can connect to a dApp and claim their allocated tokens.
- **Per-User Expiration:** Each user's allocation has a specific expiration time, which is reset each time the admin adds a new allocation for them.
- **Safe Reclaims:** The admin can reclaim a user's allocated tokens after their individual claim period has expired.
- **Box Storage:** Allocations are stored in a `BoxMap`, allowing the contract to support a large number of users efficiently.

## Contract Methods

### `create_application()`
- **Description:** A bare method that must be called during contract creation. It sets the creator's address as the admin of the contract.

### `setup(token_id: asset, claim_period_duration: uint64)`
- **Action:** `NoOp`
- **Description:** Sets up the contract's parameters. It can only be called by the admin and only once. The contract automatically opts-in to the specified `token_id`.
- **Arguments:**
    - `token_id`: The ID of the ASA (Algorand Standard Asset) to be distributed.
    - `claim_period_duration`: The duration of the claim period in seconds (e.g., 31536000 for one year).

### `add_allocations(addresses: address[], amounts: uint64[])`
- **Action:** `NoOp`
- **Description:** The admin calls this method to add or update token allocations for a batch of users. If an address already has a pending allocation, the new amount is added to the existing one, and the expiration timer is reset.
- **Arguments:**
    - `addresses`: An array of user addresses.
    - `amounts`: An array of corresponding token amounts in the smallest unit of the ASA.

### `claim()`
- **Action:** `NoOp`
- **Description:** A user calls this method to claim their allocated tokens. If the user has not already opted-in to the ASA, the contract will automatically create an opt-in transaction for them. Upon a successful claim, the contract transfers the tokens to the user and removes their allocation entry to prevent double-claiming.

### `reclaim_allocation(user_address: address)`
- **Action:** `NoOp`
- **Description:** The admin can call this method to reclaim a user's allocation if it has expired.
- **Arguments:**
    - `user_address`: The address of the user whose allocation is to be reclaimed.

## Workflow

1.  **Deployment:** The admin deploys the contract. Their address is automatically saved as the admin.
2.  **Setup:** The admin calls the `setup` method, providing the ASA ID and the duration for the claim period.
3.  **Funding:** The admin transfers the total amount of the ASA to be rewardsped into the smart contract's account.
4.  **Allocation:** The admin calls `add_allocations` one or more times to register the users and their respective claimable amounts. This sets an expiration date for each allocation.
5.  **Claiming:** Users who have been allocated tokens can call the `claim` method to receive their funds before their allocation expires.
6.  **Reclaiming:** If a user does not claim their tokens before the expiration date, the admin can call `reclaim_allocation` to retrieve that specific user's unclaimed tokens.
