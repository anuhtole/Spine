# Spine TypeScript SDK (thin client)

Small wrapper around `fetch` for `POST /v1/intercept`.

## Build

```bash
cd sdks/ts
npm install
npm run build
```

## Usage

```ts
import { SpineClient } from "./dist/index.js";

const client = new SpineClient({
  baseUrl: "http://127.0.0.1:8000",
  orgKey: "spine_...",
});
```
