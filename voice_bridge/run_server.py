"""
Main entry point to start the Aether Mobile Voice Bridge server.
"""

import sys
import socket
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from voice_bridge.config import config

def get_local_ips():
    """Detect LAN and Tailscale IPs on this host."""
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            ips.append(ip)
    except Exception:
        pass
    return ips

def main():
    print("=" * 70)
    print("  🚀 AETHER MOBILE VOICE & HARDWARE-BUTTON BRIDGE FOR ANTIGRAVITY")
    print("=" * 70)
    print(f"• Host Bound       : {config.HOST}:{config.PORT}")
    print(f"• Workspace Target : {config.DEFAULT_WORKSPACE}")
    print(f"• Antigravity CLI  : {config.AGY_PATH}")
    print(f"• Timeout Window   : {config.DEFAULT_TIMEOUT}s")
    print(f"• Secret Auth Token: {config.SECRET_TOKEN}")
    print("-" * 70)
    print("Available Network Addresses:")
    print(f"  - Localhost      : http://127.0.0.1:{config.PORT}")
    for ip in get_local_ips():
        desc = "Tailscale Mesh" if ip.startswith("100.") else "Local LAN"
        print(f"  - {desc:<15}: http://{ip}:{config.PORT}")
    print("-" * 70)
    print("iOS Shortcut / Android Webhook Setup:")
    print(f"  URL     : http://<YOUR_TAILSCALE_OR_LAN_IP>:{config.PORT}/antigravity/voice")
    print("  Method  : POST")
    print(f"  Header  : X-Auth-Token: {config.SECRET_TOKEN}")
    print('  Body    : {"prompt": "<Transcribed Speech>", "continue_last": true}')
    print("=" * 70)

    uvicorn.run(
        "voice_bridge.server:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
