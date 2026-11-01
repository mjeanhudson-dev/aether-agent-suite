# ⚡ Aether Gemini Context Caching Engine
**Dual-Mode Blueprint Caching, 75% Input Token Reduction & KPPC Kernel Spec Integration**

Part of the **Aether Sovereign Agent Suite** (`mjeanhudson-dev/aether-agent-suite`).

## Features
- **Dual-Mode Auth**: Automatically detects Google AI Studio `GEMINI_API_KEY` with seamless fallback to Google Cloud Vertex AI Application Default Credentials (`ADC`).
- **75% Cost Reduction**: Caches heavy system architecture blueprints and Kernel Packet Processing & Coordination (KPPC) specifications server-side with configurable TTL.
- **Cross-Language Support**: Full implementations in Python (`google-genai`) and TypeScript / Node.js (`@google/genai`).
- **Break-Even**: Economically superior for any workflow issuing 3 or more queries per hour ($k^* \approx 2.07$).

## Usage

### Python
```bash
python -m context_caching.context_cache --list-caches
python -m context_caching.context_cache --test-cache
```

### TypeScript / Node.js
```typescript
import { createCache, queryCache } from './context_cache';

const cache = await createCache({
  blueprintContent: myBlueprintText,
  modelName: 'gemini-2.5-pro',
  ttl: '3600s',
});

const response = await queryCache({
  cacheName: cache.name,
  contents: 'Analyze routing layer.',
});
```

## Running Tests
```bash
python -m unittest discover -s context_caching/tests
```
