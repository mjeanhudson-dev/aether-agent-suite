import { ModMode } from './types.js';

/**
 * Mod-Team Cockpit, Question Clusterer & Heavy Modifier Engine
 */
export class ModCockpit {
  constructor(options = {}) {
    this.mode = options.initialMode || ModMode.NORMAL;
    this.pinnedMessages = [];
    this.sponsorKeywords = options.sponsorKeywords || ['sponsor', 'promo', 'code', 'discount', 'link', 'deal'];
    this.seenUsers = new Set();
    this.questionClusters = new Map(); // clusterKey -> { canonicalText, counts: Map(platform, count), sampleMessages: [] }
    this.sponsorEngagementCount = 0;
  }

  setMode(mode) {
    if (Object.values(ModMode).includes(mode)) {
      this.mode = mode;
    }
  }

  /**
   * Apply heavy modifiers and calculate composite utility score
   * U(m) = Base * M_affinity * M_semantic + Omega_mod + Omega_sponsor
   */
  evaluateMessage(message, normalizedData) {
    let baseScore = 10.0;
    let affinityMultiplier = 1.0;
    let semanticMultiplier = 1.0;
    let modOverride = 0.0;
    let sponsorOverride = 0.0;
    const annotations = [];

    // 1. Monetary / Gift elevation
    if (normalizedData.grossUSD > 0) {
      baseScore += Math.min(200.0, normalizedData.grossUSD * 5.0);
      annotations.push(`💰 $${normalizedData.grossUSD.toFixed(2)} USD`);
    }

    // 2. First-Time Chatter Boost
    const userKey = `${message.platform}:${message.author.toLowerCase()}`;
    const isFirstTime = !this.seenUsers.has(userKey);
    this.seenUsers.add(userKey);

    if (isFirstTime) {
      const boost = this.mode === ModMode.FAMILY_LOVE ? 3.5 : 2.5;
      affinityMultiplier *= boost;
      annotations.push('🌱 FIRST CHAT');
    }

    // 3. Mod Pin Override
    if (message.isPinnedByMod) {
      modOverride += 10_000.0; // Infinite/instant priority
      if (message.modWhisper) {
        annotations.push(`🛡️ Mod Note: "${message.modWhisper}"`);
      } else {
        annotations.push('📌 PINNED BY MOD');
      }
    }

    // 4. Semantic Question Clustering
    const text = (message.text || '').trim();
    if (this.isQuestion(text)) {
      const clusterKey = this.extractQuestionKernel(text);
      let cluster = this.questionClusters.get(clusterKey);
      if (!cluster) {
        cluster = {
          canonicalText: text,
          totalCount: 0,
          platformCounts: {}
        };
        this.questionClusters.set(clusterKey, cluster);
      }
      cluster.totalCount += 1;
      cluster.platformCounts[message.platform] = (cluster.platformCounts[message.platform] || 0) + 1;

      if (cluster.totalCount > 1) {
        semanticMultiplier *= (1.0 + Math.log(cluster.totalCount) * 0.8);
        const breakdown = Object.entries(cluster.platformCounts)
          .map(([p, count]) => `${p.toUpperCase()}: ${count}`)
          .join(', ');
        annotations.push(`🔥 ${cluster.totalCount}x ASKED [${breakdown}]`);
      }
    }

    // 5. Sponsor Mode & Campaign Keywords
    const hasSponsorKeyword = this.sponsorKeywords.some(kw => text.toLowerCase().includes(kw));
    if (this.mode === ModMode.SPONSOR_BLOCK && hasSponsorKeyword) {
      sponsorOverride += 500.0;
      this.sponsorEngagementCount += 1;
      annotations.push('⭐ SPONSOR QUERY');
    }

    const compositeScore = (baseScore * affinityMultiplier * semanticMultiplier) + modOverride + sponsorOverride;

    return {
      compositeScore,
      annotations,
      isFirstTime,
      isSponsorMatch: hasSponsorKeyword
    };
  }

  isQuestion(text) {
    if (text.includes('?')) return true;
    const lower = text.toLowerCase();
    return lower.startsWith('when') || lower.startsWith('what') || lower.startsWith('where') ||
           lower.startsWith('how') || lower.startsWith('why') || lower.startsWith('who') ||
           lower.startsWith('will') || lower.startsWith('can');
  }

  extractQuestionKernel(text) {
    // Basic normalized token representation for grouping questions
    return text.toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter(w => w.length > 3)
      .slice(0, 4)
      .sort()
      .join('_') || 'general_query';
  }

  pinMessage(messageId, modWhisper = null) {
    this.pinnedMessages.push({ messageId, modWhisper, timestamp: Date.now() });
  }

  getSponsorReport() {
    return {
      mode: this.mode,
      sponsorInteractionsCaptured: this.sponsorEngagementCount,
      timestamp: new Date().toISOString()
    };
  }
}
