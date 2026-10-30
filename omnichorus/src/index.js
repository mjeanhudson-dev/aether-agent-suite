import { DwfqRouter } from './dwfq_router.js';
import { CurrencyNormalizer } from './currency_normalizer.js';
import { ModCockpit } from './mod_cockpit.js';
import { VadSidechain } from './vad_sidechain.js';
import { Platform, ModMode, PlatformBadge } from './types.js';

/**
 * OmniChorus Unified Multi-Stream Controller
 */
export class OmniChorusEngine {
  constructor(options = {}) {
    this.router = new DwfqRouter(options.router);
    this.cockpit = new ModCockpit(options.cockpit);
    this.vad = new VadSidechain(options.vad);
    this.teleprompterCards = [];
  }

  /**
   * Ingest a raw event from any platform
   */
  ingest(rawMessage) {
    // 1. Currency & Gift Normalization
    const normalized = CurrencyNormalizer.normalize(rawMessage);

    // 2. Mod & Scoring Evaluation
    const modResult = this.cockpit.evaluateMessage(rawMessage, normalized);

    // 3. Assemble unified envelope
    const envelope = {
      id: rawMessage.id || `msg_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      platform: rawMessage.platform,
      author: rawMessage.author,
      text: rawMessage.text,
      timestamp: rawMessage.timestamp || Date.now(),
      normalized,
      compositeScore: modResult.compositeScore,
      annotations: modResult.annotations,
      isFirstTime: modResult.isFirstTime,
      isSponsorMatch: modResult.isSponsorMatch
    };

    // 4. Enqueue into DWFQ Attention Router
    this.router.enqueue(rawMessage.platform, envelope);

    return envelope;
  }

  /**
   * Dispatch next batch of messages for Presenter HUD & TTS
   */
  dispatchPresenterBatch(maxCount = 5, presenterVoiceProbability = 0.0) {
    // Update presenter VAD state
    const vadState = this.vad.updatePresenterVoiceActivity(presenterVoiceProbability);

    // Dequeue fair-share messages
    const envelopes = this.router.dispatchNext(maxCount);

    const cards = envelopes.map(env => {
      // Build presenter eye-line teleprompter card
      const badge = PlatformBadge[env.platform] || env.platform.toUpperCase();
      const annotationString = env.annotations.length > 0
        ? ` [${env.annotations.join(' | ')}]`
        : '';
      
      const hudHeadline = `${badge} @${env.author}${annotationString}`;
      
      // Determine TTS candidate
      let ttsCandidate = null;
      if (env.normalized.grossUSD > 0 || env.isFirstTime || env.isSponsorMatch || env.compositeScore > 50.0) {
        const ttsText = env.normalized.ttsShoutout || `${env.author} says: "${env.text}"`;
        ttsCandidate = this.vad.dispatchTts(ttsText);
      }

      return {
        id: env.id,
        platform: env.platform,
        author: env.author,
        text: env.text,
        score: env.compositeScore.toFixed(1),
        hudHeadline,
        hudDisplay: env.normalized.hudDisplay,
        tts: ttsCandidate
      };
    });

    this.teleprompterCards.push(...cards);
    return {
      cards,
      vadState,
      distribution: this.router.getDistributionStats()
    };
  }

  setMode(mode) {
    this.cockpit.setMode(mode);
  }

  getDistribution() {
    return this.router.getDistributionStats();
  }
}

export { Platform, ModMode, PlatformBadge, DwfqRouter, CurrencyNormalizer, ModCockpit, VadSidechain };
