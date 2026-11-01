/**
 * Aether Context Caching Engine (TypeScript / @google/genai)
 * =========================================================
 * Provides explicit context caching for large system architectures, KPPC routing specs,
 * and multi-agent blueprints with automatic dual-mode authentication.
 */

import { GoogleGenAI } from '@google/genai';

export const DEFAULT_ADC_PROJECT = 'project-31f97d8a-b7dd-449b-b4d';
export const DEFAULT_ADC_LOCATION = 'us-central1';
export const DEFAULT_MODEL = 'gemini-2.5-pro';

export interface GenAIOptions {
  apiKey?: string;
  project?: string;
  location?: string;
}

export interface CacheConfig {
  blueprintContent: string;
  systemInstruction?: string;
  modelName?: string;
  ttl?: string;
}

export interface QueryConfig {
  cacheName: string;
  contents: string;
  modelName?: string;
  temperature?: number;
}

export function getAIClient(options: GenAIOptions = {}): GoogleGenAI {
  const apiKey = options.apiKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (apiKey) {
    return new GoogleGenAI({ apiKey });
  }

  const project = options.project || process.env.GOOGLE_CLOUD_PROJECT || DEFAULT_ADC_PROJECT;
  const location = options.location || process.env.GOOGLE_CLOUD_LOCATION || DEFAULT_ADC_LOCATION;

  return new GoogleGenAI({
    vertexai: true,
    project,
    location,
  });
}

export async function createCache(config: CacheConfig, options: GenAIOptions = {}) {
  const ai = getAIClient(options);
  const modelName = config.modelName || DEFAULT_MODEL;
  const ttl = config.ttl || '3600s';
  const systemInstruction = config.systemInstruction || 
    'You are Aether, the core collaborative co-pilot operating inside the MyAssistance control plane.';

  console.log(`[+] Initializing context cache on model '${modelName}' (TTL: ${ttl})...`);
  const cache = await ai.caches.create({
    model: modelName,
    config: {
      contents: [config.blueprintContent],
      systemInstruction,
      ttl,
    },
  });

  console.log(`[✓] Cache created: ${cache.name}`);
  return cache;
}

export async function queryCache(config: QueryConfig, options: GenAIOptions = {}) {
  const ai = getAIClient(options);
  const modelName = config.modelName || DEFAULT_MODEL;

  console.log(`\n[+] Sending query referencing cache '${config.cacheName}'...`);
  const response = await ai.models.generateContent({
    model: modelName,
    contents: config.contents,
    config: {
      cachedContent: config.cacheName,
      temperature: config.temperature ?? 0.7,
    },
  });

  console.log('\n--- Response ---');
  console.log(response.text);
  console.log('\n--- Usage Metadata ---');
  console.log(response.usageMetadata);
  return response;
}

export async function listCaches(options: GenAIOptions = {}) {
  const ai = getAIClient(options);
  console.log('[+] Fetching active context caches...');
  const pager = await ai.caches.list();
  for await (const c of pager) {
    console.log(` - ${c.name} (model: ${c.model}, expires: ${c.expireTime})`);
  }
}
