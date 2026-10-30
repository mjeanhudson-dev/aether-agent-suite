# 🎙️ Aether Mobile Voice & Hardware-Button Bridge for Antigravity

Production-grade, zero-trust webhook bridge connecting mobile hardware buttons (iOS Action Button / Back Tap, Android Side Key / Quick Settings Tiles) and voice assistants directly into your local Google Antigravity workstation session.

---

## 1. Architectural Highlights

- **Typed Semantic Airlock**: Inspects incoming voice transcripts for acoustic misrecognitions and dangerous terminal commands (`format`, `rmdir /s`, `rm -rf`, `git reset --hard`, `drop table`, `shutdown`) and safely halts execution before touching the CLI.
- **Constant-Time Cryptographic Auth**: Verifies `X-Auth-Token` or `Authorization: Bearer` using `secrets.compare_digest` against a persistent 48-character cryptographic token (`.token`).
- **Antigravity CLI Subprocess Management**: Runs [`agy -p "<prompt>" -c`](file:///C:/Users/Zachariah/AppData/Local/agy/bin/agy.exe) to append continuous turns to your active workstation session without IDE context loss.
- **TTS Text Cleaner**: Strips markdown formatting, code block syntax, backticks, hashes, and LaTeX math into clear conversational phrasing suitable for text-to-speech audio playback on your phone.

---

## 2. Quick Start

### Start the Bridge Daemon
From PowerShell:
```powershell
cd "c:\Users\Zachariah\aether agent"
.\voice_bridge\start_bridge.ps1
```
The server binds to `0.0.0.0:8844` by default and prints your active token and local/Tailscale IP addresses.

### Run Automated Tests
```powershell
& "c:\Users\Zachariah\aether agent\voice_bridge\.venv\Scripts\python.exe" -m pytest "c:\Users\Zachariah\aether agent\voice_bridge\tests"
```

---

## 3. Network Exposure: Tailscale Setup (Recommended)

Tailscale provides an encrypted WireGuard mesh between your mobile phone and workstation without exposing ports to the public internet:

1. **Install Tailscale on Workstation**:
   - Download from [tailscale.com](https://tailscale.com) and log into your Tailscale account.
   - Your workstation gets an IP (e.g. `100.x.y.z`) and a MagicDNS name (e.g. `workstation.tailnet-name.ts.net`).
2. **Install Tailscale on iPhone or Android**:
   - Install the Tailscale app from the App Store / Play Store and log into the same account.
   - Enable the VPN switch. Your phone can now ping and curl `http://100.x.y.z:8844` securely.

*(Alternative: If on the same home Wi-Fi network, you can also use your workstation's local LAN IP `http://192.168.x.y:8844`.)*

---

## 4. Mobile Client Configuration

### A. iOS Shortcuts (Action Button / Back Tap)

1. Open the **Shortcuts** app on iOS.
2. Tap **+** to create a new shortcut named **"Antigravity Voice"**.
3. Add the following action stack:
   1. **Dictate Text**:
      - Language: `English`
      - Stop Listening: `After Pause`
   2. **Get Contents of URL**:
      - URL: `http://<YOUR_TAILSCALE_OR_LAN_IP>:8844/antigravity/voice`
      - Method: `POST`
      - Headers:
        - `X-Auth-Token`: `<YOUR_TOKEN_FROM_.token_FILE>`
        - `Content-Type`: `application/json`
      - Request Body: `JSON`
        - Key: `prompt` -> Type: `Text` -> Value: `[Dictated Text]`
        - Key: `continue_last` -> Type: `Boolean` -> Value: `true`
   3. **Get Dictionary Value**:
      - Get `Value` for key `reply` in `[Contents of URL]`
   4. **Speak Text**:
      - Text: `[Dictionary Value]`
      - Rate / Pitch: Default Siri / Natural voice
4. Bind to Hardware:
   - **iPhone 15 Pro / 16 / 16 Pro**: Go to **Settings $\rightarrow$ Action Button**, swipe to **Shortcut**, and select **"Antigravity Voice"**.
   - **Other iPhones**: Go to **Settings $\rightarrow$ Accessibility $\rightarrow$ Touch $\rightarrow$ Back Tap** (Double Tap or Triple Tap) and assign **"Antigravity Voice"**.

---

### B. Android (Side Key / Quick Settings Tile)

#### Using HTTP Shortcuts (Free, Open-Source on Play Store / F-Droid):
1. Install **HTTP Shortcuts** on Android.
2. Create a new shortcut named **"Antigravity Voice"**.
3. Under **Variables**:
   - Create a variable `{prompt}` with type **Voice Input**.
4. Under **Basic Request Settings**:
   - Method: `POST`
   - URL: `http://<YOUR_TAILSCALE_OR_LAN_IP>:8844/antigravity/voice`
5. Under **Headers**:
   - `X-Auth-Token`: `<YOUR_TOKEN_FROM_.token_FILE>`
   - `Content-Type`: `application/json`
6. Under **Request Body**:
   - Body type: `JSON`
   - Content: `{"prompt": "{prompt}", "continue_last": true}`
7. Under **Response Handling**:
   - Enable **Extract from JSON** -> `$.reply`.
   - Set **Action on Success** -> **Speak Text (TTS)**.
8. Bind to Hardware:
   - Long-press homescreen $\rightarrow$ Widgets $\rightarrow$ HTTP Shortcuts $\rightarrow$ select "Antigravity Voice".
   - Or add it to **Quick Settings** notification shade tiles.
   - Or on Samsung Galaxy: **Settings $\rightarrow$ Advanced features $\rightarrow$ Side button $\rightarrow$ Double press / Long press** or use **Modes & Routines**.

---

## 5. Manual Verification & Health Check

Test locally from PowerShell or bash:

```powershell
# 1. Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8844/health"

# 2. Voice execution test
$Headers = @{
    "X-Auth-Token" = (Get-Content "c:\Users\Zachariah\aether agent\voice_bridge\.token").Trim()
    "Content-Type" = "application/json"
}
$Body = @{
    prompt = "What branch is active and what is the git status?"
    continue_last = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8844/antigravity/voice" -Method Post -Headers $Headers -Body $Body
```
