// Coin icons live in /images/coins/<base>.svg (lower-case ticker): colour
// icons from spothq/cryptocurrency-icons 0.18.1 (CC0) plus branded token
// icons from @web3icons/core 4.0.40 (MIT). <CoinIcon> tries the file for any
// ticker and falls back to letters when there's none. Aliases cover tickers
// that changed or that Binance prefixes.
export const COIN_ICON_ALIASES = {
  POL: 'matic', // Polygon's ticker after the MATIC → POL migration
};

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
