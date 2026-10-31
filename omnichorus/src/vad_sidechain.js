/**
 * Voice-Activity-Ducking (VAD) & Sidechain Attenuation Engine
 * Prevents TTS alerts from speaking over the host/presenter.
 */
export class VadSidechain {
  constructor(options = {}) {
    this.speechThreshold = options.speechThreshold || 0.65;
    this.pauseGateMs = options.pauseGateMs || 600;       // Minimum silence before playing TTS
    this.duckingDb = options.duckingDb || -14.0;         // -14 dB attenuation
    this.duckingGain = Math.pow(10, this.duckingDb / 20.0); // ~0.1995 linear multiplier
    this.attackMs = options.attackMs || options.rampTimeMs || 50;
    this.releaseMs = options.releaseMs !== undefined ? options.releaseMs : 0;

    this.isPresenterSpeaking = false;
    this.lastSpeechTime = 0;
    this.currentTtsPlaying = null;
    this.currentGain = 1.0;
    this.targetGain = 1.0;
    this.transitionStartGain = 1.0;
    this.lastTransitionTime = 0;
  }

  /**
   * C^1 continuous raised-cosine gain calculation
   */
  computeGainAt(timestampMs) {
    if (this.currentGain === this.targetGain) {
      return this.currentGain;
    }
    const duration = this.targetGain < this.transitionStartGain ? this.attackMs : this.releaseMs;
    if (duration <= 0) {
      this.currentGain = this.targetGain;
      return this.currentGain;
    }
    const elapsed = Math.max(0, timestampMs - this.lastTransitionTime);
    if (elapsed >= duration) {
      this.currentGain = this.targetGain;
      return this.currentGain;
    }
    const progress = elapsed / duration;
    // C^1 raised-cosine interpolation: zero derivative at edges
    this.currentGain = this.targetGain + (this.transitionStartGain - this.targetGain) * 0.5 * (1.0 + Math.cos(Math.PI * progress));
    return this.currentGain;
  }

  /**
   * Update presenter audio frame activity
   * @param {number} speechProbability (0.0 - 1.0)
   * @param {number} timestampMs
   */
  updatePresenterVoiceActivity(speechProbability, timestampMs = Date.now()) {
    const wasSpeaking = this.isPresenterSpeaking;
    this.isPresenterSpeaking = speechProbability >= this.speechThreshold;

    if (this.isPresenterSpeaking) {
      this.lastSpeechTime = timestampMs;
      if (this.targetGain !== this.duckingGain) {
        this.transitionStartGain = this.computeGainAt(timestampMs);
        this.targetGain = this.duckingGain;
        this.lastTransitionTime = timestampMs;
      }
    } else {
      const silenceDuration = timestampMs - this.lastSpeechTime;
      if (silenceDuration >= this.pauseGateMs) {
        if (this.targetGain !== 1.0) {
          this.transitionStartGain = this.computeGainAt(timestampMs);
          this.targetGain = 1.0;
          this.lastTransitionTime = timestampMs;
        }
      }
    }

    this.computeGainAt(timestampMs);

    return {
      isPresenterSpeaking: this.isPresenterSpeaking,
      currentGain: this.currentGain,
      silenceDuration: timestampMs - this.lastSpeechTime
    };
  }

  /**
   * Check if the queue is clear to trigger a new TTS announcement
   * @param {number} timestampMs
   * @returns {boolean}
   */
  canTriggerTts(timestampMs = Date.now()) {
    if (this.isPresenterSpeaking) return false;
    const silenceDuration = timestampMs - this.lastSpeechTime;
    return silenceDuration >= this.pauseGateMs;
  }

  /**
   * Format the TTS dispatch envelope with volume gain
   */
  dispatchTts(ttsText, timestampMs = Date.now()) {
    if (!this.canTriggerTts(timestampMs)) {
      return {
        status: 'HELD_FOR_PRESENTER_PAUSE',
        ttsText,
        effectiveGain: 0.0
      };
    }

    return {
      status: 'PLAYING',
      ttsText,
      effectiveGain: this.currentGain,
      timestamp: timestampMs
    };
  }
}
