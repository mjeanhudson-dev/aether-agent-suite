import { OmniChorusEngine, Platform, ModMode } from './index.js';

console.log('================================================================');
console.log('=== OmniChorus / PulseDeck: Multi-Stream Attention Router ===');
console.log('=== Simulating 4-Platform Firehose: YouTube, Twitch, TikTok, Discord ===');
console.log('================================================================\n');

const engine = new OmniChorusEngine();

// Simulated message pool across platforms
const simulatedEvents = [
  // YouTube flood (representing 25.0 msg/s volume)
  { platform: Platform.YOUTUBE, author: 'GamerAlex', text: 'LETS GOOOO!!', currency: 'USD' },
  { platform: Platform.YOUTUBE, author: 'Sarah_99', text: 'When does the new update drop?' },
  { platform: Platform.YOUTUBE, author: 'Speedy21', text: 'W stream tonight', amountMicros: 5_000_000, currency: 'USD' },
  { platform: Platform.YOUTUBE, author: 'Hiroshi_T', text: 'Tokyo says hello!', amountMicros: 3_000_000_000, currency: 'JPY' },
  { platform: Platform.YOUTUBE, author: 'YT_Fan_44', text: 'poggers in the chat' },
  { platform: Platform.YOUTUBE, author: 'YT_Fan_45', text: 'When does the new update drop?' },
  { platform: Platform.YOUTUBE, author: 'YT_Fan_46', text: 'can you show the car again?' },
  { platform: Platform.YOUTUBE, author: 'YT_Fan_47', text: 'hype hype hype' },
  { platform: Platform.YOUTUBE, author: 'YT_Fan_48', text: 'When does the new update drop?' },

  // Twitch events (5.0 msg/s volume)
  { platform: Platform.TWITCH, author: 'NightOwl_9', text: 'Dropping bits for good luck!', bits: 1500, eventType: 'cheer' },
  { platform: Platform.TWITCH, author: 'ClutchMaster', text: '5 gifted subs incoming!', giftCount: 5, subTier: '1000', eventType: 'gift_sub' },
  { platform: Platform.TWITCH, author: 'ApexPredator', text: 'What graphics card are you running?' },

  // TikTok Live events (1.5 msg/s volume)
  { platform: Platform.TIKTOK, author: 'Valkyrie_Rose', text: 'Lion gift for the champ!', diamondCount: 29999, repeatCount: 1, giftName: 'Lion Gift' },
  { platform: Platform.TIKTOK, author: 'DanceGuru', text: 'First time seeing this stream! Love the energy' },

  // Discord Executive / VIP thread (0.3 msg/s volume)
  { platform: Platform.DISCORD, author: 'ModSarah', text: 'Dev team confirmed the build is ready for review', isPinnedByMod: true, modWhisper: 'Highlight this during QA block' },
  { platform: Platform.DISCORD, author: 'VIP_Donator', text: 'Can we get sponsor promo code details?' }
];

// Generate an extended stream of 500 messages reflecting realistic ratios
console.log('Generating and ingesting 500 stream messages...');
const rawCounts = { [Platform.YOUTUBE]: 0, [Platform.TWITCH]: 0, [Platform.TIKTOK]: 0, [Platform.DISCORD]: 0 };

for (let i = 0; i < 500; i++) {
  const rand = Math.random();
  let baseEvent;
  if (rand < 0.85) { // 85% YouTube
    baseEvent = simulatedEvents[Math.floor(Math.random() * 9)];
  } else if (rand < 0.94) { // 9% Twitch
    baseEvent = simulatedEvents[9 + Math.floor(Math.random() * 3)];
  } else if (rand < 0.98) { // 4% TikTok
    baseEvent = simulatedEvents[12 + Math.floor(Math.random() * 2)];
  } else { // 2% Discord
    baseEvent = simulatedEvents[14 + Math.floor(Math.random() * 2)];
  }

  rawCounts[baseEvent.platform] = (rawCounts[baseEvent.platform] || 0) + 1;
  engine.ingest({ ...baseEvent, id: `msg_${i}` });
}

console.log('\n--- RAW CHRONOLOGICAL ARRIVAL DISTRIBUTION (The Firehose Bias) ---');
for (const [p, count] of Object.entries(rawCounts)) {
  console.log(`  ${p.padEnd(10)}: ${count} msgs (${((count / 500) * 100).toFixed(1)}%)`);
}

console.log('\n--- DISPATCHING VIA DWFQ ATTENTION ROUTER (Balanced Attention) ---');
let totalSampleCards = [];
for (let round = 0; round < 10; round++) {
  // Simulating presenter speech activity: round 2 and 5 have presenter talking (VAD > 0.8)
  const isSpeaking = round === 2 || round === 5 ? 0.90 : 0.10;
  const result = engine.dispatchPresenterBatch(5, isSpeaking);
  totalSampleCards.push(...result.cards);
}

console.log('\n--- SAMPLE PRESENTER EYE-LINE TELEPROMPTER CARDS ---');
totalSampleCards.slice(0, 8).forEach((card, idx) => {
  console.log(`[Card #${idx + 1}] Score: ${card.score.padStart(5)} | ${card.hudHeadline}`);
  console.log(`          Message: "${card.text}"`);
  if (card.tts) {
    console.log(`          TTS Status: ${card.tts.status} (Gain: ${card.tts.effectiveGain.toFixed(2)}) -> "${card.tts.ttsText}"`);
  }
  console.log('');
});

console.log('--- FINAL BALANCED DWFQ DISTRIBUTION REPORT ---');
const dist = engine.getDistribution();
for (const [p, data] of Object.entries(dist.breakdown)) {
  console.log(`  ${p.padEnd(10)}: ${data.count.toString().padStart(3)} dispatched (${data.percentage.padStart(5)}) [Arrival: ${data.currentArrivalRate}]`);
}
console.log(`  TOTAL DISPATCHED: ${dist.totalDispatched} messages`);

engine.triggerSponsorCtaDrop([Platform.YOUTUBE, Platform.TWITCH, Platform.TIKTOK, Platform.DISCORD]);
const roiReport = engine.generateSponsorRoiReport();
console.log('\n--- SPONSOR PROOF-OF-PERFORMANCE & CRYPTOGRAPHIC ROI RECEIPT ---');
console.log(`  Campaign: ${roiReport.brandName} (${roiReport.campaignId}) | Promo: ${roiReport.promoCode}`);
console.log(`  Effective Impressions: ${roiReport.totals.effectiveImpressions} | Sponsor Hits: ${roiReport.totals.totalSponsorKeywordMatches} | Est. Value: $${roiReport.totals.estimatedMediaValueUsd.toFixed(2)} (${roiReport.totals.roiMultiplier.toFixed(2)}x ROI)`);
console.log(`  SHA-256 Receipt: ${roiReport.verificationReceipt.payloadSha256}`);
console.log('\nResult: Successfully transformed 85%+ lopsided YouTube firehose into a fair-share community feed!');

