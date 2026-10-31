import crypto from 'node:crypto';
import { Platform, PlatformBadge } from './types.js';

/**
 * OmniChorus / PulseDeck: Sponsor Campaign Deck & Cryptographic ROI Attribution Engine
 * Automates synchronized multi-chat CTA drops, live sponsor-keyword elevation,
 * and 1-Click Cryptographically Timestamped HTML/JSON Sponsor ROI Reports.
 */
export class SponsorRoiTracker {
  constructor(campaignConfig = {}) {
    this.campaignId = campaignConfig.campaignId || `camp_${Date.now()}`;
    this.brandName = campaignConfig.brandName || 'AetherSim Pro';
    this.promoCode = campaignConfig.promoCode || 'AETHER20';
    this.baseCtaUrl = campaignConfig.baseCtaUrl || 'https://aethersim.gg/promo';
    this.sponsorKeywords = (campaignConfig.sponsorKeywords || [
      this.brandName.toLowerCase(),
      this.promoCode.toLowerCase(),
      '!promo',
      '!sponsor',
      'discount',
      'code',
      'deal',
      'link'
    ]).map(k => k.toLowerCase());

    this.cpmRateUsd = campaignConfig.cpmRateUsd ?? 28.0;
    this.cpcRateUsd = campaignConfig.cpcRateUsd ?? 1.85;
    this.flatFeeUsd = campaignConfig.flatFeeUsd ?? 2500.0;
    this.estimatedCtrByEngagement = campaignConfig.estimatedCtrByEngagement ?? 0.42;
    this.signingSecret = campaignConfig.signingSecret || 'omnichorus-sovereign-roi-secret-v1';

    this.startedAt = campaignConfig.startedAt || new Date().toISOString();
    this.ctaDrops = [];
    this.platformMetrics = new Map();
    this.engagedUsers = new Set();
    this.keywordHits = [];
    this.sponsoredGiftsUsd = 0.0;

    for (const p of Object.values(Platform)) {
      this.platformMetrics.set(p, {
        platform: p,
        totalMessagesIngested: 0,
        sponsorKeywordMatches: 0,
        ctaDropsTriggered: 0,
        uniqueEngagedChatters: new Set(),
        attributedGiftRevenueUsd: 0.0
      });
    }
  }

  /**
   * Generate and record synchronized multi-platform CTA link drops with UTM attribution
   */
  triggerSynchronizedCtaDrop(platforms = [Platform.YOUTUBE, Platform.TWITCH, Platform.TIKTOK, Platform.DISCORD], timestamp = Date.now()) {
    const dropId = `cta_${timestamp}_${this.ctaDrops.length + 1}`;
    const dispatches = platforms.map(platform => {
      const badge = PlatformBadge[platform] || platform.toUpperCase();
      const trackingUrl = `${this.baseCtaUrl}?utm_source=${encodeURIComponent(platform)}&utm_campaign=${encodeURIComponent(this.campaignId)}&code=${encodeURIComponent(this.promoCode)}`;
      const announcement = `${badge} ⭐ SPONSOR DROP: Check out ${this.brandName}! Use code "${this.promoCode}" at ${trackingUrl}`;

      const metrics = this._ensurePlatformMetrics(platform);
      metrics.ctaDropsTriggered += 1;

      return {
        platform,
        trackingUrl,
        promoCode: this.promoCode,
        announcement,
        timestamp
      };
    });

    const record = {
      dropId,
      campaignId: this.campaignId,
      timestamp: new Date(timestamp).toISOString(),
      platformsCount: dispatches.length,
      dispatches
    };
    this.ctaDrops.push(record);
    return record;
  }

  /**
   * Record an ingested chat message or gift event for sponsor attribution
   */
  recordMessage(envelope) {
    if (!envelope || !envelope.platform) {
      return { matched: false, matchedKeywords: [] };
    }

    const platform = envelope.platform;
    const metrics = this._ensurePlatformMetrics(platform);
    metrics.totalMessagesIngested += 1;

    const text = String(envelope.text || '').toLowerCase();
    const matchedKeywords = this.sponsorKeywords.filter(kw => text.includes(kw));
    const isMatched = matchedKeywords.length > 0 || Boolean(envelope.isSponsorMatch);

    if (isMatched) {
      metrics.sponsorKeywordMatches += 1;
      const authorKey = `${platform}:${String(envelope.author || 'anon').toLowerCase()}`;
      metrics.uniqueEngagedChatters.add(authorKey);
      this.engagedUsers.add(authorKey);

      const giftUsd = envelope.normalized?.grossUSD || 0.0;
      if (giftUsd > 0) {
        metrics.attributedGiftRevenueUsd += giftUsd;
        this.sponsoredGiftsUsd += giftUsd;
      }

      this.keywordHits.push({
        id: envelope.id || `hit_${this.keywordHits.length + 1}`,
        platform,
        author: envelope.author || 'anonymous',
        text: envelope.text || '',
        matchedKeywords,
        timestamp: envelope.timestamp || Date.now()
      });
    }

    return {
      matched: isMatched,
      matchedKeywords
    };
  }

  /**
   * Generate a 1-Click Cryptographically Timestamped JSON & HTML Sponsor ROI Report
   */
  generateSignedRoiReport(options = {}) {
    const generatedAt = options.generatedAt || new Date().toISOString();
    const concurrentViewersByPlatform = options.concurrentViewersByPlatform || {
      [Platform.YOUTUBE]: 5000,
      [Platform.TWITCH]: 800,
      [Platform.TIKTOK]: 150,
      [Platform.DISCORD]: 90
    };

    const platformBreakdown = {};
    let totalMessages = 0;
    let totalKeywordMatches = 0;
    let totalCtaDrops = 0;
    let totalConcurrentViewers = 0;

    for (const [platform, metrics] of this.platformMetrics.entries()) {
      const viewers = concurrentViewersByPlatform[platform] || 0;
      if (metrics.totalMessagesIngested === 0 && metrics.ctaDropsTriggered === 0 && viewers === 0) {
        continue;
      }
      totalMessages += metrics.totalMessagesIngested;
      totalKeywordMatches += metrics.sponsorKeywordMatches;
      totalCtaDrops += metrics.ctaDropsTriggered;
      totalConcurrentViewers += viewers;

      platformBreakdown[platform] = {
        concurrentViewers: viewers,
        messagesIngested: metrics.totalMessagesIngested,
        sponsorKeywordMatches: metrics.sponsorKeywordMatches,
        uniqueEngagedChatters: metrics.uniqueEngagedChatters.size,
        ctaDropsTriggered: metrics.ctaDropsTriggered,
        attributedGiftRevenueUsd: Number(metrics.attributedGiftRevenueUsd.toFixed(2))
      };
    }

    const effectiveImpressions = totalConcurrentViewers * Math.max(1, this.ctaDrops.length) + totalMessages * 4;
    const estimatedClicks = Math.round(totalKeywordMatches * this.estimatedCtrByEngagement + this.ctaDrops.length * (totalConcurrentViewers * 0.012));
    const mediaValueUsd = (effectiveImpressions / 1000.0) * this.cpmRateUsd + (estimatedClicks * this.cpcRateUsd) + this.sponsoredGiftsUsd;
    const effectiveCpmUsd = effectiveImpressions > 0 ? (this.flatFeeUsd / (effectiveImpressions / 1000.0)) : 0.0;
    const roiMultiplier = this.flatFeeUsd > 0 ? (mediaValueUsd / this.flatFeeUsd) : 0.0;

    const canonicalPayload = {
      campaignId: this.campaignId,
      brandName: this.brandName,
      promoCode: this.promoCode,
      startedAt: this.startedAt,
      generatedAt,
      totals: {
        totalConcurrentViewers,
        totalMessagesIngested: totalMessages,
        totalSponsorKeywordMatches: totalKeywordMatches,
        uniqueEngagedChatters: this.engagedUsers.size,
        synchronizedCtaDrops: this.ctaDrops.length,
        totalPlatformCtaDispatches: totalCtaDrops,
        effectiveImpressions,
        estimatedClicks,
        sponsoredGiftsUsd: Number(this.sponsoredGiftsUsd.toFixed(2)),
        estimatedMediaValueUsd: Number(mediaValueUsd.toFixed(2)),
        effectiveCpmUsd: Number(effectiveCpmUsd.toFixed(2)),
        roiMultiplier: Number(roiMultiplier.toFixed(2))
      },
      platformBreakdown
    };

    const serializedPayload = JSON.stringify(canonicalPayload);
    const sha256Hash = crypto.createHash('sha256').update(serializedPayload).digest('hex');
    const hmacSignature = crypto.createHmac('sha256', this.signingSecret).update(serializedPayload).digest('hex');

    const htmlReport = this._renderHtmlReport(canonicalPayload, sha256Hash, hmacSignature);

    return {
      ...canonicalPayload,
      verificationReceipt: {
        algorithm: 'HMAC-SHA256',
        payloadSha256: sha256Hash,
        hmacSignature,
        verifiedTimestamp: generatedAt
      },
      htmlReport
    };
  }

  /**
   * Verify a previously generated ROI report's cryptographic integrity
   */
  verifyReportSignature(report) {
    if (!report || !report.verificationReceipt) return false;
    const canonicalPayload = {
      campaignId: report.campaignId,
      brandName: report.brandName,
      promoCode: report.promoCode,
      startedAt: report.startedAt,
      generatedAt: report.generatedAt,
      totals: report.totals,
      platformBreakdown: report.platformBreakdown
    };
    const serialized = JSON.stringify(canonicalPayload);
    const expectedSha = crypto.createHash('sha256').update(serialized).digest('hex');
    const expectedHmac = crypto.createHmac('sha256', this.signingSecret).update(serialized).digest('hex');

    return (
      expectedSha === report.verificationReceipt.payloadSha256 &&
      expectedHmac === report.verificationReceipt.hmacSignature
    );
  }

  _ensurePlatformMetrics(platform) {
    if (!this.platformMetrics.has(platform)) {
      this.platformMetrics.set(platform, {
        platform,
        totalMessagesIngested: 0,
        sponsorKeywordMatches: 0,
        ctaDropsTriggered: 0,
        uniqueEngagedChatters: new Set(),
        attributedGiftRevenueUsd: 0.0
      });
    }
    return this.platformMetrics.get(platform);
  }

  _renderHtmlReport(payload, sha256Hash, hmacSignature) {
    const rows = Object.entries(payload.platformBreakdown)
      .map(([platform, data]) => (
        `<tr>` +
        `<td>${platform.toUpperCase()}</td>` +
        `<td>${data.concurrentViewers}</td>` +
        `<td>${data.messagesIngested}</td>` +
        `<td>${data.sponsorKeywordMatches}</td>` +
        `<td>${data.uniqueEngagedChatters}</td>` +
        `<td>${data.ctaDropsTriggered}</td>` +
        `</tr>`
      ))
      .join('\n');

    return [
      '<!DOCTYPE html>',
      '<html lang="en">',
      '<head><meta charset="utf-8"><title>OmniChorus Sponsor Proof-of-Performance Report</title></head>',
      '<body>',
      `  <h1>Sponsor Proof-of-Performance: ${payload.brandName} (${payload.campaignId})</h1>`,
      `  <p>Promo Code: <strong>${payload.promoCode}</strong> | Generated: ${payload.generatedAt}</p>`,
      '  <section id="executive-summary">',
      `    <p>Effective Impressions: ${payload.totals.effectiveImpressions}</p>`,
      `    <p>Sponsor Keyword Matches: ${payload.totals.totalSponsorKeywordMatches}</p>`,
      `    <p>Estimated CTA Clicks: ${payload.totals.estimatedClicks}</p>`,
      `    <p>Estimated Media Value: $${payload.totals.estimatedMediaValueUsd.toFixed(2)} USD (${payload.totals.roiMultiplier.toFixed(2)}x ROI)</p>`,
      '  </section>',
      '  <table border="1">',
      '    <thead><tr><th>Platform</th><th>CCV</th><th>Messages</th><th>Sponsor Hits</th><th>Unique Users</th><th>CTA Drops</th></tr></thead>',
      `    <tbody>${rows}</tbody>`,
      '  </table>',
      '  <footer>',
      `    <small>SHA-256 Receipt: <code>${sha256Hash}</code> | HMAC: <code>${hmacSignature}</code></small>`,
      '  </footer>',
      '</body>',
      '</html>'
    ].join('\n');
  }
}
