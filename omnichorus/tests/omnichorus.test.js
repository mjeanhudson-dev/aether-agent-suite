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
