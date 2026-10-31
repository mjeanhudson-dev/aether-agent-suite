import { test } from 'node:test';
import assert from 'node:assert';
import { OmniChorusEngine, Platform, ModMode, SponsorRoiTracker } from '../src/index.js';

test('SponsorRoiTracker triggers synchronized multi-platform CTA drops with UTM tracking', () => {
  const tracker = new SponsorRoiTracker({
    campaignId: 'camp_q4_launch',
    brandName: 'DualSense Forge',
    promoCode: 'GYRO50',
    baseCtaUrl: 'https://dualsenseforge.io/deal'
  });

  const drop = tracker.triggerSynchronizedCtaDrop(
    [Platform.YOUTUBE, Platform.TWITCH, Platform.TIKTOK, Platform.DISCORD],
    1730000000000
  );

  assert.strictEqual(drop.campaignId, 'camp_q4_launch');
  assert.strictEqual(drop.platformsCount, 4);
  assert.strictEqual(drop.dispatches.length, 4);

  const ytDispatch = drop.dispatches.find(d => d.platform === Platform.YOUTUBE);
  assert.ok(ytDispatch.trackingUrl.includes('utm_source=youtube'));
  assert.ok(ytDispatch.trackingUrl.includes('utm_campaign=camp_q4_launch'));
  assert.ok(ytDispatch.trackingUrl.includes('code=GYRO50'));
  assert.ok(ytDispatch.announcement.includes('DualSense Forge'));
});

test('SponsorRoiTracker attributes keyword engagements, unique users, and generates verifiable cryptographic receipt', () => {
  const tracker = new SponsorRoiTracker({
    campaignId: 'camp_verify_01',
    brandName: 'ApexTelemetry',
    promoCode: 'APEX25',
    flatFeeUsd: 1500.0
  });

  tracker.triggerSynchronizedCtaDrop([Platform.YOUTUBE, Platform.TWITCH]);

  const hit1 = tracker.recordMessage({
    id: 'm1',
    platform: Platform.YOUTUBE,
    author: 'RacerOne',
    text: 'Just used code APEX25 for the discount!',
    normalized: { grossUSD: 10.0 }
  });
  assert.strictEqual(hit1.matched, true);
  assert.ok(hit1.matchedKeywords.includes('apex25'));

  // Duplicate message from same user on same platform shouldn't inflate unique chatter count
  tracker.recordMessage({
    id: 'm2',
    platform: Platform.YOUTUBE,
    author: 'RacerOne',
    text: 'Where is the !promo link?'
  });

  // Unrelated message
  const miss = tracker.recordMessage({
    id: 'm3',
    platform: Platform.TWITCH,
    author: 'CasualViewer',
    text: 'Great overtake on turn 3!'
  });
  assert.strictEqual(miss.matched, false);

  const report = tracker.generateSignedRoiReport({
    generatedAt: '2026-10-30T21:00:00.000Z',
    concurrentViewersByPlatform: {
      [Platform.YOUTUBE]: 4000,
      [Platform.TWITCH]: 1000
    }
  });

  assert.strictEqual(report.totals.totalMessagesIngested, 3);
  assert.strictEqual(report.totals.totalSponsorKeywordMatches, 2);
  assert.strictEqual(report.totals.uniqueEngagedChatters, 1);
  assert.strictEqual(report.totals.sponsoredGiftsUsd, 10.0);
  assert.ok(report.totals.effectiveImpressions > 5000);
  assert.ok(report.verificationReceipt.payloadSha256.length === 64);
  assert.ok(report.verificationReceipt.hmacSignature.length === 64);
  assert.ok(report.htmlReport.includes('ApexTelemetry'));
  assert.ok(report.htmlReport.includes(report.verificationReceipt.payloadSha256));

  // Verify signature passes untouched report and rejects tampered report
  assert.strictEqual(tracker.verifyReportSignature(report), true);
  const tampered = JSON.parse(JSON.stringify(report));
  tampered.totals.totalSponsorKeywordMatches = 9999;
  assert.strictEqual(tracker.verifyReportSignature(tampered), false);
});

test('OmniChorusEngine integrates SponsorRoiTracker end-to-end during SPONSOR_BLOCK mode', () => {
  const engine = new OmniChorusEngine({
    sponsorRoi: {
      campaignId: 'camp_live_01',
      brandName: 'ShiftSim',
      promoCode: 'SHIFT10'
    }
  });

  engine.setMode(ModMode.SPONSOR_BLOCK);
  const drop = engine.triggerSponsorCtaDrop([Platform.YOUTUBE, Platform.DISCORD]);
  assert.strictEqual(drop.platformsCount, 2);

  engine.ingest({
    platform: Platform.DISCORD,
    author: 'Exec_VIP',
    text: 'Grabbing the ShiftSim deal with code SHIFT10 right now!'
  });

  const report = engine.generateSponsorRoiReport();
  assert.strictEqual(report.campaignId, 'camp_live_01');
  assert.strictEqual(report.totals.totalSponsorKeywordMatches, 1);
  assert.strictEqual(engine.sponsorRoi.verifyReportSignature(report), true);
});
