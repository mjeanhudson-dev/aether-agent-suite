import { Platform, PlatformBadge, FX_RATES_TO_USD } from './types.js';

/**
 * Universal Multi-Currency & Platform Gift Normalizer
 * Accurately normalizes 40+ fiat currencies and virtual tokens into USD
 * while producing faithful platform badges and natural TTS shoutouts.
 */
export class CurrencyNormalizer {
  /**
   * Normalize an incoming monetary or gift event
   * @param {Object} rawPayload
   * @returns {Object} Normalized event metadata
   */
  static normalize(rawPayload) {
    const { platform, author, eventType } = rawPayload;
    let grossUSD = 0.0;
    let nativeDisplay = '';
    let ttsShoutout = '';

    switch (platform) {
      case Platform.YOUTUBE: {
        // YouTube Live SuperChat / SuperSticker uses amountMicros and currency code
        const currency = (rawPayload.currency || 'USD').toUpperCase();
        const fx = FX_RATES_TO_USD[currency] || 1.0;
        const amountUnits = (rawPayload.amountMicros || 0) / 1_000_000.0;
        grossUSD = amountUnits * fx;

        const currencySymbol = this.getCurrencySymbol(currency);
        nativeDisplay = `${currencySymbol}${amountUnits.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        
        if (grossUSD > 0) {
          ttsShoutout = `Thank you to ${author} on YouTube Live for the ${nativeDisplay} SuperChat${currency !== 'USD' ? ` (about $${grossUSD.toFixed(2)} USD)` : ''}!`;
        }
        break;
      }

      case Platform.TWITCH: {
        if (eventType === 'cheer' || rawPayload.bits) {
          const bits = rawPayload.bits || 0;
          grossUSD = bits * 0.01;
          nativeDisplay = `${bits.toLocaleString()} Bits`;
          ttsShoutout = `Big love to ${author} on Twitch for cheering ${bits.toLocaleString()} Bits ($${grossUSD.toFixed(2)})!`;
        } else if (eventType === 'sub' || eventType === 'gift_sub') {
          const count = rawPayload.giftCount || 1;
          const tier = rawPayload.subTier || '1000';
          const tierPrice = tier === '3000' ? 24.99 : tier === '2000' ? 9.99 : 4.99;
          grossUSD = count * tierPrice;
          nativeDisplay = count > 1 ? `${count}x Tier ${tier[0]} Gift Subs` : `Tier ${tier[0]} Sub`;
          ttsShoutout = count > 1
            ? `Huge shoutout to ${author} on Twitch for gifting ${count} subs to the community ($${grossUSD.toFixed(2)})!`
            : `Welcome ${author} to the subscriber family on Twitch!`;
        }
        break;
      }

      case Platform.TIKTOK: {
        // TikTok Live WebcastGiftMessage (coins / diamondCount)
        const diamondCount = rawPayload.diamondCount || 0;
        const repeatCount = rawPayload.repeatCount || 1;
        const totalCoins = diamondCount * repeatCount;
        grossUSD = totalCoins * 0.0106; // Approx gross conversion rate
        const giftName = rawPayload.giftName || 'Gift';
        nativeDisplay = `${repeatCount > 1 ? `${repeatCount}x ` : ''}${giftName} (${totalCoins.toLocaleString()} Coins)`;
        ttsShoutout = `Massive shoutout to ${author} on TikTok Live for dropping ${repeatCount > 1 ? `${repeatCount} ` : 'a '}${giftName} (about $${grossUSD.toFixed(2)})!`;
        break;
      }

      case Platform.KICK: {
        const count = rawPayload.giftCount || 1;
        grossUSD = count * 4.99;
        nativeDisplay = count > 1 ? `${count}x Gifted Subs` : `Sub`;
        ttsShoutout = count > 1
          ? `Shoutout to ${author} on Kick for gifting ${count} subs!`
          : `Thanks ${author} for subbing on Kick!`;
        break;
      }

      case Platform.STRIPE_CHARITY: {
        const currency = (rawPayload.currency || 'USD').toUpperCase();
        const fx = FX_RATES_TO_USD[currency] || 1.0;
        const amount = (rawPayload.amountCents || 0) / 100.0;
        grossUSD = amount * fx;
        const symbol = this.getCurrencySymbol(currency);
        nativeDisplay = `${symbol}${amount.toFixed(2)}`;
        ttsShoutout = `Heartfelt thank you to ${author} for the generous ${nativeDisplay} charity pledge ($${grossUSD.toFixed(2)})!`;
        break;
      }

      default:
        grossUSD = rawPayload.grossUSD || 0.0;
        nativeDisplay = grossUSD > 0 ? `$${grossUSD.toFixed(2)}` : '';
        ttsShoutout = rawPayload.text || '';
        break;
    }

    const badge = PlatformBadge[platform] || '💬';
    const hudDisplay = grossUSD > 0
      ? `[${badge}] @${author} • ${nativeDisplay} (~$${grossUSD.toFixed(2)})`
      : `[${badge}] @${author}`;

    return {
      grossUSD,
      nativeDisplay,
      hudDisplay,
      ttsShoutout
    };
  }

  static getCurrencySymbol(code) {
    switch (code) {
      case 'EUR': return '€';
      case 'GBP': return '£';
      case 'JPY': return '¥';
      case 'BRL': return 'R$';
      case 'INR': return '₹';
      case 'KRW': return '₩';
      case 'CAD': return 'C$';
      case 'AUD': return 'A$';
      default: return '$';
    }
  }
}
