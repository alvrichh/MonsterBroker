# Web3 en MonsterBroker: token propio, NFTs y cómo puede sostenerse

Objetivo declarado: **aprender y ayudar a aprender**. El dinero es un objetivo
a futuro y se busca por caminos que no obliguen a vender un criptoactivo con
valor al público (que es justo lo que MiCA regula con más dureza).

## 1. Qué construimos

| Pieza | Qué es | Contrato |
| --- | --- | --- |
| **MonsterCoin (MBK)** | Token ERC-20 de aprendizaje. Se gana completando lecciones y retos; sirve para desbloquear contenido y funciones. Sin valor monetario en testnet. | `contracts/src/MonsterToken.sol` |
| **Monster Badges** | NFTs ERC-721 *soulbound* (no transferibles): insignias por logros (primer tick del bot, glosario de futuros, racha de lectura del radar…). Prueba verificable de lo aprendido. | `contracts/src/MonsterBadge.sol` |
| **Wallet como identidad** | Entrar con la wallet (Sign-In with Ethereum): el usuario firma un mensaje, no hay contraseña. | backend `auth/wallet/*` |
| **Learn-to-earn** | El backend es el único *minter*: cuando completas un reto, acuña MBK a tu wallet y la insignia correspondiente. Los retos y las reclamaciones viven en `app/services/quests.py` (tabla `quest_claims`); la acuñación en `app/onchain/rewards.py`; la lectura del saldo y las insignias en `app/onchain/token.py`. Sin `MINTER_PRIVATE_KEY` las reclamaciones quedan `pending` y `python -m app.cli settle` las acuña después. | `app/services/quests.py`, `app/onchain/rewards.py` |

Red: **Base** (L2 de Coinbase, comisiones de céntimos). Primero **Base Sepolia**
(testnet, gratis). Pasar a mainnet es un cambio de `CHAIN_ID` y direcciones,
pero antes hay que leer la sección legal.

## 2. Cómo puede dar dinero (sin vender un token con valor)

Ordenado de menos a más complejo/regulado:

1. **Afiliación con exchanges regulados** (Binance, Bitpanda, Kraken… tienen
   programas de referidos). La app ya enseña a operar; enlazar al broker donde
   abrir cuenta es el modelo de todas las webs de "learn and earn".
2. **Campañas patrocinadas de learn-to-earn** (modelo Galxe/Coinbase Earn): un
   proyecto paga para que nuestros usuarios aprendan sobre él y reciban *su*
   token. Nosotros cobramos la campaña; el token que reparte es del tercero.
3. **NFTs de pago con utilidad**: certificados de curso, acceso a un canal
   privado, mentoría. Los NFT únicos y no fungibles quedan **fuera de MiCA**
   (art. 2.3 del Reglamento), siempre que no sean fraccionados ni emitidos en
   serie intercambiable. Royalties en reventa (EIP-2981). El contrato ya
   existe: `contracts/src/MonsterCertificate.sol` (`buy` a precio fijo en ETH,
   `grant` gratis desde el backend a quien termina el curso, una por curso y
   wallet, `withdraw` a la tesorería). Falta la tienda en la app.
4. **Suscripción premium** (más señales del bot, alertas, histórico) pagada en
   euros (Stripe) o en cripto estable. Esto es SaaS normal.
5. **MBK con valor en mainnet** — *último paso, no primero*. Si el token se
   compra/vende tiene valor y entra en MiCA: white paper notificado a la CNMV
   (salvo exenciones: oferta gratuita, menos de 150 personas por Estado, menos
   de 1 M€ en 12 meses, solo inversores cualificados), prohibición de
   publicidad engañosa y, si gestionamos cripto de otros, licencia CASP. Las
   recompensas **gratuitas** por aprender encajan en la exención de "oferta
   sin contraprestación", pero hay que tratarlo con un abogado antes de pasar
   a mainnet.

Regla que nos ponemos: **nada de prometer rentabilidad**, el token no se
vende, y todo lo que tenga valor real pasa por un proveedor regulado.

## 3. Marco legal (España / UE), en corto

- **MiCA** (Reglamento UE 2023/1114) aplica en España desde finales de 2024;
  el transitorio para proveedores de servicios (CASP) terminó el 1 de julio de
  2026: solo operan los autorizados por la CNMV o con pasaporte europeo.
- Emitir un **utility token** y ofrecerlo al público requiere white paper
  (Título II) salvo exenciones del art. 4. En **testnet no hay oferta** (no hay
  activo con valor).
- Los **NFT** únicos no son criptoactivos a efectos de MiCA; sí lo son si se
  emiten en grandes series fungibles de facto.
- **Security tokens** (participaciones, promesas de beneficio) son
  instrumentos financieros (MiFID II): fuera de nuestro alcance a propósito.
- Fiscalidad: las recompensas con valor son renta; los NFT vendidos tributan.
  Otro motivo para que MBK no tenga valor hasta tenerlo claro.

## 4. Roadmap

1. ✅ Contratos (Foundry + OpenZeppelin 5), tests, script de despliegue.
2. ✅ Login con wallet (SIWE) junto a Google/Microsoft/GitHub.
3. ⏳ Desplegar en Base Sepolia (falta: wallet con ETH de testnet del faucet y
   `MINTER_PRIVATE_KEY` del backend; `GET /api/token/info` enseña la dirección
   que hay que pasar como `MINTER`).
4. ✅ Página `/token`: vincular wallet, saldo MBK, insignias, retos reclamables
   (`GET /api/token/info|me`, `POST /api/token/claim`); metadatos ERC-721 de
   cada insignia en `GET /api/token/metadata/{reto}`.
5. ✅ Tres retos: bienvenida (vincular wallet), primer tick del bot, glosario de
   futuros. ⏳ Siguientes: 7 días seguidos de radar, primera posición en
   perpetuos, racha de aciertos del bot.
6. ✅ Contrato de certificados NFT de pago (`MonsterCertificate`, con
   royalties EIP-2981). ⏳ Tienda de certificados en la app + afiliación
   (primer ingreso real).
7. 🔒 Mainnet solo con revisión legal.

## 5. Referencias

- Base: <https://docs.base.org/get-started/deploy-smart-contracts>
- Foundry: <https://getfoundry.sh/introduction/installation>
- OpenZeppelin Contracts 5: <https://docs.openzeppelin.com/contracts/5.x/>
- MiCA (texto): <https://eur-lex.europa.eu/eli/reg/2023/1114/oj>
- CNMV y MiCA en España: <https://www.cnmv.es>
- SIWE (EIP-4361): <https://eips.ethereum.org/EIPS/eip-4361>
- EIP-2981 (royalties): <https://eips.ethereum.org/EIPS/eip-2981>
