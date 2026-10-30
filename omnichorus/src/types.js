/**
 * OmniChorus / PulseDeck Architecture Core Types & Constants
 * Sovereign Multi-Platform Attention Router
 */

export const Platform = Object.freeze({
  YOUTUBE: 'youtube',
  TWITCH: 'twitch',
  TIKTOK: 'tiktok',
  KICK: 'kick',
  DISCORD: 'discord',
  SLACK: 'slack',
  TEAMS: 'teams',
  STRIPE_CHARITY: 'stripe_charity'
});

export const PlatformBadge = Object.freeze({
  [Platform.YOUTUBE]: '🔴 YT',
  [Platform.TWITCH]: '🟣 TW',
  [Platform.TIKTOK]: '🎵 TT',
  [Platform.KICK]: '🟢 KICK',
  [Platform.DISCORD]: '💬 DISC',
  [Platform.SLACK]: '💼 SLACK',
  [Platform.TEAMS]: '🏢 TEAMS',
  [Platform.STRIPE_CHARITY]: '💖 CHARITY'
});

export const ModMode = Object.freeze({
  NORMAL: 'NORMAL',
  FAMILY_LOVE: 'FAMILY_LOVE',       // beta=0.25, boosts first-time chatters and quietest platforms
  QA_CLUSTER: 'QA_CLUSTER',         // surfaces only semantically clustered questions
  SPONSOR_BLOCK: 'SPONSOR_BLOCK'    // prioritizes sponsor keywords, triggers synchronized CTA links
});

// Real-time FX Table to USD (Normalized reference rates)
export const FX_RATES_TO_USD = Object.freeze({
  USD: 1.0,
  EUR: 1.085,
  GBP: 1.302,
  JPY: 0.0067,    // ~149 JPY / USD
  CAD: 0.725,
  AUD: 0.665,
  BRL: 0.177,
  INR: 0.0119,
  KRW: 0.00073,
  MXN: 0.051
});
