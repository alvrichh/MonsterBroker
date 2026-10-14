// The browser wallet (MetaMask, Rabby, Coinbase Wallet…) through EIP-1193.
// Signing a message is free: no gas, no transaction, nothing moves.

export const hasWallet = () => typeof window !== 'undefined' && Boolean(window.ethereum);

export class WalletError extends Error {
  constructor(message, code) {
    super(message);
    this.code = code; // 4001 = the user closed the wallet prompt
  }
}

const wrap = (error) => (error instanceof WalletError ? error : new WalletError(error?.message || 'wallet', error?.code));

export async function connectWallet() {
  if (!hasWallet()) throw new WalletError('no-wallet', 'no-wallet');
  try {
    const [address] = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!address) throw new WalletError('no-account', 'no-account');
    return address;
  } catch (error) {
    throw wrap(error);
  }
}

// personal_sign wants the message hex-encoded; some wallets reject plain text.
const toHex = (text) => `0x${Array.from(new TextEncoder().encode(text), (b) => b.toString(16).padStart(2, '0')).join('')}`;

export async function signMessage(address, message) {
  try {
    return await window.ethereum.request({ method: 'personal_sign', params: [toHex(message), address] });
  } catch (error) {
    throw wrap(error);
  }
}
