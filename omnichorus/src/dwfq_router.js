/**
 * Sub-Linear Deficit Weighted Fair-Queuing (DWFQ) Attention Router
 * 
 * Balances wildly lopsided chat velocities across platforms:
 * Raw arrival: 93.2% YouTube (25 msg/s), 5.6% TikTok (1.5 msg/s), 1.1% Discord (0.3 msg/s)
 * DWFQ output (beta=0.30): ~54% YouTube, ~23% TikTok, ~14% Discord, ~8% Kick
 */
export class DwfqRouter {
  constructor(options = {}) {
    this.beta = options.beta || 0.30;             // Sub-linear concavity exponent
    this.quantum = options.quantum || 100.0;       // Base quantum credit per round
    this.wMin = options.wMin || 0.05;              // Minimum bandwidth guarantee per active platform
    this.epsilon = options.epsilon || 0.05;        // Non-zero arrival smoothing offset
    this.alpha = options.alpha || 0.20;            // EWMA arrival rate smoothing factor

    this.queues = new Map();                       // platform -> Array<MessageEnvelope>
    this.deficits = new Map();                     // platform -> number
    this.arrivalRates = new Map();                 // platform -> smoothed msg/sec
    this.recentArrivalCounts = new Map();          // platform -> count in current window
    this.lastRateCalcTime = Date.now();
    this.totalDispatched = 0;
    this.dispatchedByPlatform = new Map();
  }

  registerPlatform(platform) {
    if (!this.queues.has(platform)) {
      this.queues.set(platform, []);
      this.deficits.set(platform, 0.0);
      this.arrivalRates.set(platform, 1.0);
      this.recentArrivalCounts.set(platform, 0);
      this.dispatchedByPlatform.set(platform, 0);
    }
  }

  enqueue(platform, messageEnvelope) {
    this.registerPlatform(platform);
    const q = this.queues.get(platform);

    let inserted = false;
    for (let i = 0; i < q.length; i++) {
      if (messageEnvelope.compositeScore > q[i].compositeScore) {
        q.splice(i, 0, messageEnvelope);
        inserted = true;
        break;
      }
    }
    if (!inserted) {
      q.push(messageEnvelope);
    }

    const currentCount = this.recentArrivalCounts.get(platform) || 0;
    this.recentArrivalCounts.set(platform, currentCount + 1);
  }

  updateArrivalRates(now = Date.now()) {
    const elapsedSec = Math.max(0.1, (now - this.lastRateCalcTime) / 1000.0);
    this.lastRateCalcTime = now;

    for (const [platform, count] of this.recentArrivalCounts.entries()) {
      const instantRate = count / elapsedSec;
      const prevRate = this.arrivalRates.get(platform) || 1.0;
      const smoothed = (this.alpha * instantRate) + ((1.0 - this.alpha) * prevRate);
      this.arrivalRates.set(platform, Math.max(0.01, smoothed));
      this.recentArrivalCounts.set(platform, 0);
    }
  }

  calculateWeights() {
    const activePlatforms = [];
    for (const [platform, q] of this.queues.entries()) {
      if (q.length > 0) {
        activePlatforms.push(platform);
      }
    }

    if (activePlatforms.length === 0) {
      return new Map();
    }

    let denom = 0.0;
    const powerTerms = new Map();
    for (const p of activePlatforms) {
      const lambda = this.arrivalRates.get(p) || 0.5;
      const term = Math.pow(lambda + this.epsilon, this.beta);
      powerTerms.set(p, term);
      denom += term;
    }

    const weights = new Map();
    if (denom <= 0) denom = 1.0;

    for (const p of activePlatforms) {
      const rawWeight = powerTerms.get(p) / denom;
      weights.set(p, Math.max(this.wMin, rawWeight));
    }

    return weights;
  }

  dispatchNext(maxToDispatch = 5) {
    this.updateArrivalRates();
    const dispatched = [];
    let roundsWithoutProgress = 0;

    while (dispatched.length < maxToDispatch && roundsWithoutProgress < 3) {
      const weights = this.calculateWeights();
      if (weights.size === 0) break; // All queues drained

      // Allocate quantum deficits based on weights
      for (const [platform, weight] of weights.entries()) {
        const currentDeficit = this.deficits.get(platform) || 0.0;
        this.deficits.set(platform, currentDeficit + (weight * this.quantum));
      }

      let progressInRound = false;

      for (const [platform, weight] of weights.entries()) {
        const q = this.queues.get(platform);
        let deficit = this.deficits.get(platform) || 0.0;

        while (q && q.length > 0 && dispatched.length < maxToDispatch) {
          const candidate = q[0];
          const cost = Math.max(10.0, 100.0 / (1.0 + Math.log(1.0 + (candidate.compositeScore || 1.0))));

          if (deficit >= cost) {
            const msg = q.shift();
            deficit -= cost;
            this.deficits.set(platform, deficit);
            dispatched.push(msg);
            this.totalDispatched += 1;
            this.dispatchedByPlatform.set(platform, (this.dispatchedByPlatform.get(platform) || 0) + 1);
            progressInRound = true;
          } else {
            break; // Insufficient deficit, wait for next quantum round
          }
        }

        if (dispatched.length >= maxToDispatch) break;
      }

      if (progressInRound) {
        roundsWithoutProgress = 0;
      } else {
        roundsWithoutProgress++;
      }
    }

    return dispatched;
  }

  getDistributionStats() {
    const stats = {};
    for (const [platform, count] of this.dispatchedByPlatform.entries()) {
      const pct = this.totalDispatched > 0
        ? ((count / this.totalDispatched) * 100).toFixed(1) + '%'
        : '0%';
      stats[platform] = { count, percentage: pct, currentArrivalRate: (this.arrivalRates.get(platform) || 0).toFixed(2) + ' msg/s' };
    }
    return {
      totalDispatched: this.totalDispatched,
      breakdown: stats
    };
  }
}
