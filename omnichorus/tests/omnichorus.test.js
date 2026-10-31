import { test } from 'node:test';
import assert from 'node:assert';
import { OmniChorusEngine, Platform, ModMode, CurrencyNormalizer, ModCockpit, VadSidechain, DwfqRouter } from '../src/index.js';

test('CurrencyNormalizer converts YouTube JPY SuperChat into accurate USD and faithful TTS', () => {
  const result = CurrencyNormalizer.normalize({
    platform: Platform.YOUTUBE,
    author: 'Kenji',
    amountMicros: 5_000_000_000, // 5,000 JPY
    currency: 'JPY'
  });

  assert.strictEqual(result.nativeDisplay, '¥5,000.00');
  assert.ok(result.grossUSD > 30.0 && result.grossUSD < 40.0, `Expected ~33.50 USD, got ${result.grossUSD}`);
  assert.ok(result.ttsShoutout.includes('YouTube Live'));
  assert.ok(result.ttsShoutout.includes('¥5,000.00'));
});

test('CurrencyNormalizer converts Twitch Bits and Gift Subs accurately', () => {
  const cheer = CurrencyNormalizer.normalize({
    platform: Platform.TWITCH,
    author: 'StarPilot',
    bits: 2500,
    eventType: 'cheer'
  });
  assert.strictEqual(cheer.grossUSD, 25.0);
  assert.strictEqual(cheer.nativeDisplay, '2,500 Bits');

  const giftSubs = CurrencyNormalizer.normalize({
    platform: Platform.TWITCH,
    author: 'WhaleGamer',
    giftCount: 10,
    subTier: '1000',
    eventType: 'gift_sub'
  });
  assert.ok(Math.abs(giftSubs.grossUSD - 49.90) < 0.001, `Expected ~49.90, got ${giftSubs.grossUSD}`);
  assert.strictEqual(giftSubs.nativeDisplay, '10x Tier 1 Gift Subs');
});

test('ModCockpit correctly boosts first-time chatters and clusters duplicate questions', () => {
  const cockpit = new ModCockpit();

  const msg1 = { platform: Platform.YOUTUBE, author: 'Newbie1', text: 'When does the game launch?' };
  const res1 = cockpit.evaluateMessage(msg1, { grossUSD: 0 });
  assert.strictEqual(res1.isFirstTime, true);
  assert.ok(res1.annotations.includes('🌱 FIRST CHAT'));

  // Second message from same user should not be first time
  const msg2 = { platform: Platform.YOUTUBE, author: 'Newbie1', text: 'I am so excited!' };
  const res2 = cockpit.evaluateMessage(msg2, { grossUSD: 0 });
  assert.strictEqual(res2.isFirstTime, false);

  // Another user asking the same question should trigger question cluster
  const msg3 = { platform: Platform.TWITCH, author: 'Gamer2', text: 'When does the game launch?' };
  const res3 = cockpit.evaluateMessage(msg3, { grossUSD: 0 });
  assert.ok(res3.annotations.some(a => a.includes('2x ASKED')));
});

test('VadSidechain ducks volume and enforces pre-speech pause gate', () => {
  const vad = new VadSidechain({ pauseGateMs: 300, duckingDb: -14.0 });

  const now = 10000;
  // Presenter speaks at t=10000
  vad.updatePresenterVoiceActivity(0.95, now);
  assert.strictEqual(vad.canTriggerTts(now), false);

  const dispatchDuringSpeech = vad.dispatchTts('Test announcement', now);
  assert.strictEqual(dispatchDuringSpeech.status, 'HELD_FOR_PRESENTER_PAUSE');

  // Presenter stops speaking at t=10100, but only 100ms has elapsed (gate is 300ms)
  vad.updatePresenterVoiceActivity(0.10, now + 100);
  assert.strictEqual(vad.canTriggerTts(now + 100), false);

  // At t=10450 (350ms elapsed silence), gate opens
  vad.updatePresenterVoiceActivity(0.10, now + 450);
  assert.strictEqual(vad.canTriggerTts(now + 450), true);

  const dispatchAfterPause = vad.dispatchTts('Test announcement', now + 450);
  assert.strictEqual(dispatchAfterPause.status, 'PLAYING');
  assert.strictEqual(dispatchAfterPause.effectiveGain, 1.0);
});

test('DwfqRouter prevents high-volume starvation and distributes fair attention', () => {
  const router = new DwfqRouter({ beta: 0.30, quantum: 100 });

  // Flood 100 messages on YouTube
  for (let i = 0; i < 100; i++) {
    router.enqueue(Platform.YOUTUBE, {
      id: `yt_${i}`,
      platform: Platform.YOUTUBE,
      author: `User_YT_${i}`,
      compositeScore: 10.0
    });
  }

  // Only 5 messages on Discord
  for (let i = 0; i < 5; i++) {
    router.enqueue(Platform.DISCORD, {
      id: `disc_${i}`,
      platform: Platform.DISCORD,
      author: `User_Disc_${i}`,
      compositeScore: 10.0
    });
  }

  // Dispatch 10 messages
  const batch = router.dispatchNext(10);
  assert.strictEqual(batch.length, 10);

  // Confirm Discord received dispatch slots despite having only 5% of the total input volume
  const discordDispatched = batch.filter(m => m.platform === Platform.DISCORD);
  assert.ok(discordDispatched.length >= 2, `Expected at least 2 Discord messages, got ${discordDispatched.length}`);
});

test('TikTok Live streak idempotency gates revenue on repeatEnd === 1', () => {
  // In-progress streak drops: repeatCount 1..9 with repeatEnd === 0
  const inProgress1 = CurrencyNormalizer.normalize({
    platform: Platform.TIKTOK,
    author: 'ViewerA',
    giftName: 'Rose',
    diamondCount: 1,
    repeatCount: 1,
    repeatEnd: 0
  });
  assert.strictEqual(inProgress1.grossUSD, 0.0);
  assert.strictEqual(inProgress1.ttsShoutout, '');

  const inProgress5 = CurrencyNormalizer.normalize({
    platform: Platform.TIKTOK,
    author: 'ViewerA',
    giftName: 'Rose',
    diamondCount: 1,
    repeatCount: 5,
    repeatEnd: 0
  });
  assert.strictEqual(inProgress5.grossUSD, 0.0);

  // Terminal streak drop: repeatCount 10 with repeatEnd === 1
  const finalDrop = CurrencyNormalizer.normalize({
    platform: Platform.TIKTOK,
    author: 'ViewerA',
    giftName: 'Rose',
    diamondCount: 1,
    repeatCount: 10,
    repeatEnd: 1
  });
  // 10 coins * 0.0106 = $0.106 USD
  assert.strictEqual(finalDrop.grossUSD.toFixed(3), '0.106');
  assert.ok(finalDrop.ttsShoutout.includes('ViewerA on TikTok Live'));
});

test('DwfqRouter calculates simplex-normalized weights and drains empty queue deficit', () => {
  const router = new DwfqRouter({ beta: 0.30, quantum: 100, wMin: 0.05 });
  router.enqueue(Platform.TWITCH, { id: 'tw1', platform: Platform.TWITCH, compositeScore: 20 });
  router.enqueue(Platform.YOUTUBE, { id: 'yt1', platform: Platform.YOUTUBE, compositeScore: 20 });
  router.enqueue(Platform.TIKTOK, { id: 'tt1', platform: Platform.TIKTOK, compositeScore: 20 });

  const weights = router.calculateWeights();
  let sum = 0;
  for (const w of weights.values()) {
    assert.ok(w >= 0.05, 'Each weight must meet floor');
    sum += w;
  }
  assert.ok(Math.abs(sum - 1.0) < 1e-6, `Simplex sum must equal 1.0, got ${sum}`);

  // Dispatch all 3 so queues drain to empty
  router.dispatchNext(5);
  for (const p of [Platform.TWITCH, Platform.YOUTUBE, Platform.TIKTOK]) {
    assert.strictEqual(router.deficits.get(p), 0.0, `Queue for ${p} must reset deficit to 0 upon drain`);
  }
});

test('ModMode.QA_CLUSTER boosts questions and de-prioritizes non-questions', () => {
  const cockpit = new ModCockpit({ initialMode: ModMode.QA_CLUSTER });

  const questionMsg = { text: 'How do I download the latest release?', platform: Platform.TWITCH, author: 'Ch1' };
  const qEval = cockpit.evaluateMessage(questionMsg, { grossUSD: 0 });
  assert.ok(qEval.annotations.includes('❓ QA PRIORITY'));
  assert.ok(qEval.compositeScore > 20.0);

  const regularMsg = { text: 'Just chilling and saying hello', platform: Platform.TWITCH, author: 'Ch2' };
  const rEval = cockpit.evaluateMessage(regularMsg, { grossUSD: 0 });
  assert.ok(rEval.compositeScore < 10.0, 'Non-question must be deprioritized in QA_CLUSTER mode');
});

test('VadSidechain performs smooth C^1 continuous raised-cosine ducking', () => {
  const vad = new VadSidechain({ pauseGateMs: 200, attackMs: 50, releaseMs: 100 });
  const t0 = 1000;

  // Presenter speaks at t0 -> triggers attack ramp down to duckingGain
  vad.updatePresenterVoiceActivity(0.90, t0);
  assert.strictEqual(vad.canTriggerTts(t0), false);

  // Midway through attack (25ms in)
  const midAttackGain = vad.computeGainAt(t0 + 25);
  assert.ok(midAttackGain < 1.0 && midAttackGain > vad.duckingGain, 'Mid-attack gain is smoothly interpolated');

  // Attack complete at 50ms
  const endAttackGain = vad.computeGainAt(t0 + 50);
  assert.ok(Math.abs(endAttackGain - vad.duckingGain) < 0.001);

  // Presenter stops speaking at t0 + 100. Pause gate is 200ms -> gate opens at t0 + 300
  vad.updatePresenterVoiceActivity(0.10, t0 + 300);
  assert.strictEqual(vad.canTriggerTts(t0 + 300), true);

  // Midway through release (t0 + 350, 50ms into 100ms release)
  const midReleaseGain = vad.computeGainAt(t0 + 350);
  assert.ok(midReleaseGain > vad.duckingGain && midReleaseGain < 1.0, 'Mid-release gain is smoothly interpolated');

  // Fully released at t0 + 400
  const endReleaseGain = vad.computeGainAt(t0 + 400);
  assert.strictEqual(endReleaseGain, 1.0);
});
