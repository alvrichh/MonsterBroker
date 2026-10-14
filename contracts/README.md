# MonsterBroker contracts

Foundry + OpenZeppelin 5. Two contracts, built for Base (Sepolia first):

- `src/MonsterToken.sol` — **MonsterCoin (MBK)**, an ERC-20 with a fixed `cap`,
  `ERC20Permit` and a `MINTER_ROLE` (only the backend mints learning rewards).
  Nobody sells it.
- `src/MonsterBadge.sol` — **Monster Badges**, *soulbound* ERC-721: badges for
  achievements, one of each kind per wallet, non-transferable, the owner may burn it.

Why, and how it fits the app: [`docs/WEB3.md`](../docs/WEB3.md).

## Development

```bash
# Foundry: https://getfoundry.sh (on Windows, from Git Bash)
cd contracts
forge install            # pulls lib/openzeppelin-contracts and lib/forge-std (submodules)
forge build
forge test -vv
```

## Deploying to Base Sepolia

1. Create a wallet for deploying and get testnet ETH from the Base faucets:
   https://docs.base.org/base-chain/tools/network-faucets
2. Variables (in `contracts/.env`, never committed):

   ```bash
   BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
   PRIVATE_KEY=0x...            # the wallet holding testnet ETH
   MINTER=0x...                 # the backend wallet (the one that will sign rewards)
   BASESCAN_API_KEY=...         # optional, to verify the source
   ```

3. Deploy and verify:

   ```bash
   source .env
   forge script script/Deploy.s.sol --rpc-url base_sepolia --private-key $PRIVATE_KEY --broadcast --verify -vvvv
   ```

4. Copy the addresses it prints into the backend `.env`: `TOKEN_ADDRESS`,
   `BADGE_ADDRESS`, `CHAIN_ID=84532`, `WEB3_RPC_URL=https://sepolia.base.org`.

Mainnet (`--rpc-url base`, chain 8453) only after the legal review described in `docs/WEB3.md`.
