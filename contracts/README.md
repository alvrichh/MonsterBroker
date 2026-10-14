# Contratos de MonsterBroker

Foundry + OpenZeppelin 5. Dos contratos, pensados para Base (Sepolia primero):

- `src/MonsterToken.sol` — **MonsterCoin (MBK)**, ERC-20 con `cap` fijo, `ERC20Permit`
  y `MINTER_ROLE` (solo el backend acuña recompensas de aprendizaje). Nadie lo vende.
- `src/MonsterBadge.sol` — **Monster Badges**, ERC-721 *soulbound*: insignias por logros,
  una de cada tipo por wallet, intransferibles, el dueño puede quemarla.

Por qué y cómo encaja en la app: [`docs/WEB3.md`](../docs/WEB3.md).

## Desarrollo

```bash
# Foundry: https://getfoundry.sh (en Windows, desde Git Bash)
cd contracts
forge install            # trae lib/openzeppelin-contracts y lib/forge-std (submódulos)
forge build
forge test -vv
```

## Despliegue en Base Sepolia

1. Crea una wallet para desplegar y pide ETH de testnet en los faucets de Base:
   https://docs.base.org/base-chain/tools/network-faucets
2. Variables (en `contracts/.env`, nunca commiteado):

   ```bash
   BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
   PRIVATE_KEY=0x...            # la wallet con ETH de testnet
   MINTER=0x...                 # wallet del backend (la que firmará las recompensas)
   BASESCAN_API_KEY=...         # opcional, para verificar el código
   ```

3. Despliega y verifica:

   ```bash
   source .env
   forge script script/Deploy.s.sol --rpc-url base_sepolia --private-key $PRIVATE_KEY --broadcast --verify -vvvv
   ```

4. Copia las direcciones que imprime a `.env` del backend: `TOKEN_ADDRESS`,
   `BADGE_ADDRESS`, `CHAIN_ID=84532`, `WEB3_RPC_URL=https://sepolia.base.org`.

Mainnet (`--rpc-url base`, chain 8453) solo tras la revisión legal descrita en `docs/WEB3.md`.
