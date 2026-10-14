// Colour coin icons from spothq/cryptocurrency-icons 0.18.1 (CC0), served
// from /images/coins/<base>.svg. Anything else gets a lettered fallback in
// <CoinIcon>.
const ICON_BASES = [
  'BTC', 'ETH', 'LTC', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'AVAX', 'LINK', 'TRX', 'UNI', 'ATOM',
  'XLM', 'ETC', 'BCH', 'FIL', 'ALGO', 'VET', 'ICP', 'USDT', 'USDC', 'DAI', 'AAVE', 'MKR', 'XMR', 'GRT', 'SAND',
  'MANA', 'THETA', 'EOS', 'XTZ', 'ZEC', 'DASH', 'NEO', 'COMP', 'CRV', 'SNX', '1INCH', 'ZIL', 'BAT', 'ENJ',
];
export const COIN_ICONS = Object.fromEntries(ICON_BASES.map((base) => [base, `/images/coins/${base.toLowerCase()}.svg`]));
COIN_ICONS.POL = COIN_ICONS.MATIC; // Polygon's ticker after the MATIC → POL migration

// Brand colours for the home coin cards' glow and top rule.
export const COIN_COLORS = {
  BTC: '#f7931a',
  ETH: '#627eea',
  LTC: '#345d9d',
  SOL: '#14f195',
};

// The "Participa" row on the home page: the prototype's table, now live.
export const HOME_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'SOL/USDT'];

// The home ticker tape: the cards above plus a few heavyweights.
export const TAPE_SYMBOLS = [...HOME_SYMBOLS, 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT'];

export const TIMEFRAMES = ['15m', '1h', '4h', '1d'];
