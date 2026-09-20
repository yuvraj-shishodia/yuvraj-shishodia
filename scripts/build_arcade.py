#!/usr/bin/env python3
"""
Arcade profile builder.

Reads  arcade.config  (in the repo root) and produces, inside ./dist :

    header.svg                 animated header with the chosen header game
    body-1.svg / body-1-dark.svg   first body game  (renamed from the generated graph)
    body-2.svg / body-2-dark.svg   second body game (or a 1x1 transparent placeholder)

Usage (the workflow calls these for you):

    python3 scripts/build_arcade.py games     -> prints  games=<comma list>  for the Action
    python3 scripts/build_arcade.py build     -> writes header + body slots into ./dist
    python3 scripts/build_arcade.py preview DIR  -> writes one header per game into DIR (local testing)

Standard library only, no installs needed.
"""
import configparser
import random
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "arcade.config"
DIST = ROOT / "dist"

GAMES = ["pacman", "galaga", "breakout", "puzzle-bobble", "bomberman", "minesweeper"]
ALIASES = {"pac-man": "pacman", "puzzlebobble": "puzzle-bobble", "bobble": "puzzle-bobble",
           "mine-sweeper": "minesweeper", "bomber-man": "bomberman"}
MAX_BODY = 2
DUR = 12      # seconds for one pass of the header animation
Y = 256       # vertical centre of the game lane in the header


# ───────────────────────────── helpers ─────────────────────────────
def fail(msg):
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def norm_game(name):
    g = re.sub(r"[\s_]+", "-", name.strip().lower())
    g = ALIASES.get(g, g)
    if g not in GAMES:
        fail(f"Unknown game '{name}' in arcade.config. Valid games: {', '.join(GAMES)}")
    return g


def read_config():
    if not CONFIG.exists():
        fail("arcade.config was not found in the repo root.")
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(CONFIG, encoding="utf-8")
    if "arcade" not in cp:
        fail("arcade.config must start with the line [arcade]")
    s = cp["arcade"]
    body = [norm_game(g) for g in s.get("body", "pacman").split(",") if g.strip()]
    if not body:
        fail("'body' in arcade.config needs at least one game.")
    if len(body) > MAX_BODY:
        fail(f"'body' in arcade.config can list at most {MAX_BODY} games (you listed {len(body)}).")
    return {
        "header": norm_game(s.get("header", "pacman")),
        "body": body,
        "name": s.get("name", "Your Name").strip(),
        "subtitle": s.get("subtitle", "").strip(),
        "tagline": s.get("tagline", "").strip(),
        "score": s.get("score", "001337").strip(),
        "high_score": s.get("high_score", "999999").strip(),
        "credit": s.get("credit", "01").strip(),
    }


def vanish(f):
    """opacity animation: visible, then gone from fraction f of the loop until it restarts."""
    return (f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;{f:.4f};1" '
            f'calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>')


def burst(cx, cy, f, color, rmax):
    """A small expanding ring that pops once per loop at fraction f."""
    a, b, c = f, min(f + 0.012, 0.995), min(f + 0.05, 0.999)
    kt = f"0;{a:.4f};{b:.4f};{c:.4f};1"
    return (f'<circle cx="{cx}" cy="{cy}" r="2" fill="none" stroke="{color}" stroke-width="2" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
            f'<animate attributeName="r" values="2;2;5;{rmax};{rmax}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
            f'</circle>')


def indent(lines, n):
    pad = " " * n
    return "\n".join(pad + l for l in lines)


# ───────────────────────────── shared header shell ─────────────────────────────
SHELL = r'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300" role="img" aria-labelledby="t d" xmlns:c2pa="http://c2pa.org/manifest"><metadata><c2pa:manifest>AAAWgmp1bWIAAAAeanVtZGMycGEAEQAQgAAAqgA4m3EDYzJwYQAAABZcanVtYgAAAEdqdW1kYzJtYQARABCAAACqADibcQN1cm46YzJwYTowODhkMWFkMi1kMThkLTQxM2ItOTgwZC04OTc2ZWQ0ZDQ4NDkAAAADl2p1bWIAAAApanVtZGMyYXMAEQAQgAAAqgA4m3EDYzJwYS5hc3NlcnRpb25zAAAAALxqdW1iAAAARGp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuaW5ncmVkaWVudC52MwAAAAAYYzJzaPIAJSw/WmaqoVtibgevKf8AAABwY2JvcqNpZGM6Zm9ybWF0bWltYWdlL3N2Zyt4bWxqaW5zdGFuY2VJRHgseG1wOmlpZDo2Mzc3ZDVkMi00MzQyLTQ4ODItOWI2NC0zNjI3MzlmMjBiNDlscmVsYXRpb25zaGlwaHBhcmVudE9mAAAB4mp1bWIAAABBanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5hY3Rpb25zLnYyAAAAABhjMnNo+oguwTPtbNxEznX74+67ZAAAAZljYm9yomdhY3Rpb25zgqJmYWN0aW9ua2MycGEub3BlbmVkanBhcmFtZXRlcnOha2luZ3JlZGllbnRzgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFgggoheFzb6eKSku9ThVYIcRDvnYDlj/QEh8pQQ7ZI2BEKkZmFjdGlvbngdY29tLmFudGhyb3BpYy5jbGF1ZGUucHJvdmlkZWRqcGFyYW1ldGVyc6F4H2NvbS5hbnRocm9waWMub3JpZ2luLWNvbmZpZGVuY2VndW5rbm93bmtkZXNjcmlwdGlvbnhmQ2xhdWRlIHByb3ZpZGVkIHRoaXMgZmlsZSBhdCB0aGUgcmVxdWVzdCBvZiBhIHVzZXIgYW5kIG1heSBoYXZlIGNyZWF0ZWQgb3IgbW9kaWZpZWQgdGhlIGZpbGUgY29udGVudHMubXNvZnR3YXJlQWdlbnShZG5hbWVmQ2xhdWRlcmFsbEFjdGlvbnNJbmNsdWRlZPUAAADIanVtYgAAAEBqdW1kY2JvcgARABCAAACqADibcRNjMnBhLmhhc2guZGF0YQAAAAAYYzJzaFEBXfrVtM/si5XmtTQioGQAAACAY2JvcqVjYWxnZnNoYTI1NmNwYWRNAAAAAAAAAAAAAAAAAGRoYXNoWCDxVRRY56BzubSJMxsyYLRasyazEkzwWpajK7wab5VPqmRuYW1lbmp1bWJmIG1hbmlmZXN0amV4Y2x1c2lvbnOBomVzdGFydBi3Zmxlbmd0aBkeBAAAAj5qdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAACD2Nib3KlY2FsZ2ZzaGEyNTZpc2lnbmF0dXJleE1zZWxmI2p1bWJmPS9jMnBhL3VybjpjMnBhOjA4OGQxYWQyLWQxOGQtNDEzYi05ODBkLTg5NzZlZDRkNDg0OS9jMnBhLnNpZ25hdHVyZWppbnN0YW5jZUlEeCx4bXA6aWlkOjRjZWMxZGY3LWEyZGUtNDE2Zi1iNTY5LTgzMTUyYjhkMDk5MHJjcmVhdGVkX2Fzc2VydGlvbnODomN1cmx4LXNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuaW5ncmVkaWVudC52M2RoYXNoWCCCiF4XNvp4pKS71OFVghxEO+dgOWP9ASHylBDtkjYEQqJjdXJseCpzZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmFjdGlvbnMudjJkaGFzaFggZ9CYoAHx9N38LYuM2Vzuqw04FzPZXsanzA39WGGzcK2iY3VybHgpc2VsZiNqdW1iZj1jMnBhLmFzc2VydGlvbnMvYzJwYS5oYXNoLmRhdGFkaGFzaFggN1e8uoL+IBD+y/gHmBaB3IvOEuRuOYK5nNttisO9cqt0Y2xhaW1fZ2VuZXJhdG9yX2luZm+jZG5hbWVvQW50aHJvcGljIEZpbGVzZ3ZlcnNpb25lMS4wLjBrc3BlY1ZlcnNpb25lMi40LjAAABA4anVtYgAAAChqdW1kYzJjcwARABCAAACqADibcQNjMnBhLnNpZ25hdHVyZQAAABAIY2JvctKEWQISogEmGCFZAgowggIGMIIBjaADAgECAhRA5aAK7sI50L64g/oGQgU9Z1UTADAKBggqhkjOPQQDAzBJMRcwFQYDVQQKEw5BbnRocm9waWMsIFBCQzEuMCwGA1UEAxMlQW50aHJvcGljIENvbnRlbnQgQ3JlZGVudGlhbHMgUm9vdCBDQTAeFw0yNjA4MDcxODQzNTZaFw0yODA4MDYxOTQzNTZaMEQxFzAVBgNVBAoTDkFudGhyb3BpYywgUEJDMSkwJwYDVQQDEyBBbnRocm9waWMgQ2xhdWRlIENvbnRlbnQgU2lnbmluZzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABJh6CmvLUBgFFNU0vUKlOVtE6djd17L5SuwX0LemFisBM3dkd/3cyjxFA3Qo5S46fX0/ihY0VZ7mfb9KF703t5OjWDBWMA4GA1UdDwEB/wQEAwIHgDAVBgNVHSUEDjAMBgorBgEEAYPoXgIBMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUzlHiBIFOZFsj+OPEz5o+nMHXXMIwCgYIKoZIzj0EAwMDZwAwZAIwMXMdFJ4BetLLVY7ORuE9noqbbAZOZn/aArXyTwFAZfKrPzxF2vPoJNf1+UCdg1XGAjBwX1zd9WGqYkqmL5SFqw1QySjr1zJfpJM9+1rdDwSPLMOPOjKuiXjoU/pUUeG9RwmhY3BhZFkNngAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPZYQFttbW7Vi15bcFlMaZ+xpi8LhZ7VlJK4y7EVdbw65XsLRUsV1txfyhnbEHKHqhkCKoO5IkniN+J5P8HtNMq8sBo=</c2pa:manifest></metadata>
  <title id="t">__TITLE__</title>
  <desc id="d">__DESC__</desc>

  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1a1730"/>
      <stop offset="1" stop-color="#0d0b18"/>
    </linearGradient>

    <radialGradient id="glowPink" cx="0.12" cy="1" r="0.6">
      <stop offset="0" stop-color="#fe428e" stop-opacity="0.32"/>
      <stop offset="1" stop-color="#fe428e" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowPurple" cx="0.88" cy="0" r="0.65">
      <stop offset="0" stop-color="#7a35d6" stop-opacity="0.42"/>
      <stop offset="1" stop-color="#7a35d6" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.07"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>

    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M30 0H0V30" fill="none" stroke="#ffffff" stroke-opacity="0.045" stroke-width="1"/>
    </pattern>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1.6" fill="#000000" fill-opacity="0.22"/>
    </pattern>

    <filter id="glow" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="blur8" x="-20%" y="-60%" width="140%" height="220%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>

    <clipPath id="card"><rect width="900" height="300" rx="18"/></clipPath>


__DEFS__
  </defs>

  <g clip-path="url(#card)">
    <!-- background -->
    <rect width="900" height="300" fill="url(#bg)"/>
    <rect width="900" height="300" fill="url(#grid)"/>
    <rect width="900" height="300" fill="url(#glowPink)"/>
    <rect width="900" height="300" fill="url(#glowPurple)"/>

    <!-- maze walls -->
    <rect x="12" y="12" width="876" height="276" rx="20" fill="none" stroke="#4b3fe0" stroke-width="3" filter="url(#glow)"/>
    <rect x="21" y="21" width="858" height="258" rx="13" fill="none" stroke="#4b3fe0" stroke-opacity="0.65" stroke-width="1.2"/>

__PRE_HUD__    <!-- HUD -->
    <g font-family="'Courier New', Courier, monospace" font-weight="700" font-size="16" letter-spacing="2">
      <text x="48" y="52" fill="#ffffff" fill-opacity="0.92">
        1UP
        <animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/>
      </text>
      <text x="48" y="73" fill="#f8d847">__P1__</text>

      <text x="450" y="52" fill="#ffffff" fill-opacity="0.92" text-anchor="middle">HIGH SCORE</text>
      <text x="450" y="73" fill="#f8d847" text-anchor="middle">__HI__</text>

      <text x="852" y="52" fill="#ffffff" fill-opacity="0.92" text-anchor="end">CREDIT</text>
      <text x="852" y="73" fill="#f8d847" text-anchor="end">__CREDIT__</text>
    </g>

__TEXT__
__LANE__
    <!-- CRT scanlines + slow sweep -->
    <rect width="900" height="300" fill="url(#scan)"/>
    <rect width="900" height="70" y="-70" fill="url(#sweep)">
      <animate attributeName="y" from="-70" to="300" dur="6s" repeatCount="indefinite"/>
    </rect>
  </g>
</svg>
'''

PACMAN_DEFS = r'''    <clipPath id="dotsClip">
      <rect y="0" width="2000" height="300" x="-36">
        <animate attributeName="x" from="-36" to="1094" dur="12s" repeatCount="indefinite"/>
      </rect>
    </clipPath>'''

PACMAN_LANE = r'''    <!-- dots + power pellet -->
    <g clip-path="url(#dotsClip)" fill="#ffe0b8">
      <circle cx="70"  cy="256" r="3"/><circle cx="100" cy="256" r="3"/><circle cx="130" cy="256" r="3"/>
      <circle cx="160" cy="256" r="3"/><circle cx="190" cy="256" r="3"/><circle cx="220" cy="256" r="3"/>
      <circle cx="250" cy="256" r="3"/><circle cx="280" cy="256" r="3"/><circle cx="310" cy="256" r="3"/>
      <circle cx="340" cy="256" r="3"/><circle cx="370" cy="256" r="3"/><circle cx="400" cy="256" r="3"/>
      <circle cx="430" cy="256" r="3"/><circle cx="460" cy="256" r="3"/><circle cx="490" cy="256" r="3"/>
      <circle cx="520" cy="256" r="3"/><circle cx="550" cy="256" r="3"/><circle cx="580" cy="256" r="3"/>
      <circle cx="610" cy="256" r="3"/><circle cx="640" cy="256" r="3"/><circle cx="670" cy="256" r="3"/>
      <circle cx="700" cy="256" r="3"/><circle cx="730" cy="256" r="3"/><circle cx="760" cy="256" r="3"/>
      <circle cx="820" cy="256" r="3"/><circle cx="850" cy="256" r="3"/>
      <circle cx="790" cy="256" r="6.5">
        <animate attributeName="opacity" values="1;0.15" calcMode="discrete" dur="0.6s" repeatCount="indefinite"/>
      </circle>
    </g>

    <!-- ghost 2 (cyan) -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="-190 256" to="940 256" dur="12s" repeatCount="indefinite"/>
      <path fill="#a9fef7" d="M-16 16 L-16 0 A16 16 0 0 1 16 0 L16 16 L11 11 L5.5 16 L0 11 L-5.5 16 L-11 11 Z">
        <animate attributeName="d" calcMode="discrete" dur="0.36s" repeatCount="indefinite"
          values="M-16 16 L-16 0 A16 16 0 0 1 16 0 L16 16 L11 11 L5.5 16 L0 11 L-5.5 16 L-11 11 Z;M-16 11 L-16 0 A16 16 0 0 1 16 0 L16 11 L11 16 L5.5 11 L0 16 L-5.5 11 L-11 16 Z"/>
      </path>
      <circle cx="-6" cy="-3" r="4.6" fill="#ffffff"/><circle cx="6" cy="-3" r="4.6" fill="#ffffff"/>
      <circle cx="-4.2" cy="-3" r="2.2" fill="#2a2aa8"/><circle cx="7.8" cy="-3" r="2.2" fill="#2a2aa8"/>
    </g>

    <!-- ghost 1 (pink) -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="-130 256" to="1000 256" dur="12s" repeatCount="indefinite"/>
      <path fill="#fe428e" d="M-16 16 L-16 0 A16 16 0 0 1 16 0 L16 16 L11 11 L5.5 16 L0 11 L-5.5 16 L-11 11 Z">
        <animate attributeName="d" calcMode="discrete" dur="0.36s" repeatCount="indefinite"
          values="M-16 16 L-16 0 A16 16 0 0 1 16 0 L16 16 L11 11 L5.5 16 L0 11 L-5.5 16 L-11 11 Z;M-16 11 L-16 0 A16 16 0 0 1 16 0 L16 11 L11 16 L5.5 11 L0 16 L-5.5 11 L-11 16 Z"/>
      </path>
      <circle cx="-6" cy="-3" r="4.6" fill="#ffffff"/><circle cx="6" cy="-3" r="4.6" fill="#ffffff"/>
      <circle cx="-4.2" cy="-3" r="2.2" fill="#2a2aa8"/><circle cx="7.8" cy="-3" r="2.2" fill="#2a2aa8"/>
    </g>

    <!-- Pac-Man -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="-40 256" to="1090 256" dur="12s" repeatCount="indefinite"/>
      <path fill="#f8d847" d="M0 0 L15.98 -0.84 A16 16 0 1 0 15.98 0.84 Z">
        <animate attributeName="d" dur="0.36s" repeatCount="indefinite"
          values="M0 0 L15.98 -0.84 A16 16 0 1 0 15.98 0.84 Z;M0 0 L12.61 -9.85 A16 16 0 1 0 12.61 9.85 Z;M0 0 L15.98 -0.84 A16 16 0 1 0 15.98 0.84 Z"/>
      </path>
      <circle cx="1.5" cy="-8" r="2" fill="#141321"/>
    </g>
'''


def text_blocks(cfg):
    """Name + subtitle + tagline, sized so they always fit the card."""
    name = escape(cfg["name"].upper())
    n = max(len(cfg["name"]), 1)
    size = min(58.0, 700.0 / (n * 0.711))
    tl = min(n * 0.711 * size, 780)
    out = f'''    <!-- name -->
    <g font-family="'Courier New', Courier, monospace" font-weight="900" font-size="{size:.1f}" text-anchor="middle">
      <text x="450" y="150" fill="#fe428e" fill-opacity="0.75" filter="url(#blur8)" textLength="{tl:.0f}" lengthAdjust="spacing">{name}</text>
      <text x="454" y="154" fill="#fe428e" textLength="{tl:.0f}" lengthAdjust="spacing">{name}</text>
      <text x="450" y="150" fill="#f8d847" textLength="{tl:.0f}" lengthAdjust="spacing">{name}</text>
    </g>
'''
    lines = []
    if cfg["subtitle"]:
        t = cfg["subtitle"].upper(); m = max(len(t), 1)
        sz = min(19.0, 780.0 / (m * 0.816)); tlen = min(m * 0.816 * sz, 780)
        lines.append(f'      <text x="450" y="196" font-size="{sz:.1f}" fill="#a9fef7" textLength="{tlen:.0f}" lengthAdjust="spacing">{escape(t)}</text>')
    if cfg["tagline"]:
        t = cfg["tagline"].upper(); m = max(len(t), 1)
        sz = min(14.0, 780.0 / (m * 0.714)); tlen = min(m * 0.714 * sz, 780)
        lines.append(f'      <text x="450" y="222" font-size="{sz:.1f}" fill="#ffffff" fill-opacity="0.72" textLength="{tlen:.0f}" lengthAdjust="spacing">{escape(t)}</text>')
    if lines:
        out += ('\n    <!-- titles -->\n'
                '    <g font-family="\'Courier New\', Courier, monospace" font-weight="700" text-anchor="middle">\n'
                + "\n".join(lines) + '\n    </g>\n')
    return out


# ───────────────────────────── game lanes ─────────────────────────────
def lane_pacman():
    return {"defs": PACMAN_DEFS, "pre": "", "lane": PACMAN_LANE}


CRAB = ["00100000100", "00010001000", "00111111100", "01101110110",
        "11111111111", "10111111101", "10100000101", "00011011000"]


def sprite_path(rows, p):
    d, w = [], len(rows[0])
    for r, row in enumerate(rows):
        c = 0
        while c < w:
            if row[c] == "1":
                s = c
                while c < w and row[c] == "1":
                    c += 1
                d.append(f"M{(s - w / 2) * p:.2f} {(r - len(rows) / 2) * p:.2f}h{(c - s) * p:.2f}v{p:.2f}h{-(c - s) * p:.2f}z")
            else:
                c += 1
    return "".join(d)


def lane_galaga():
    SHIP0, SHIP1, LASER = -40, 1090, 72
    alien_d = sprite_path(CRAB, 2.6)
    colors = ["#a9fef7", "#fe428e"]
    aliens, bursts = [], []
    for i, x in enumerate(range(130, 851, 48)):
        f = ((x - LASER) - SHIP0) / (SHIP1 - SHIP0)
        aliens.append(f'<use href="#alien" x="{x}" y="{Y}" fill="{colors[i % 2]}">{vanish(f)}</use>')
        bursts.append(burst(x, Y, f, "#f8d847", 16))
    lane = f'''    <!-- enemies -->
    <g>
      <animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur="0.9s" repeatCount="indefinite"/>
{indent(aliens, 6)}
    </g>
{indent(bursts, 4)}

    <!-- fighter -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="{SHIP0} {Y}" to="{SHIP1} {Y}" dur="{DUR}s" repeatCount="indefinite"/>
      <line x1="22" y1="0" x2="{LASER}" y2="0" stroke="#fe428e" stroke-opacity="0.35" stroke-width="8" stroke-linecap="round"/>
      <line x1="22" y1="0" x2="{LASER}" y2="0" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-dasharray="9 5">
        <animate attributeName="stroke-dashoffset" from="0" to="-14" dur="0.18s" repeatCount="indefinite"/>
      </line>
      <path d="M-12 -2 L-21 0 L-12 2 Z" fill="#f8d847"><animate attributeName="opacity" values="1;0.35;1" dur="0.15s" repeatCount="indefinite"/></path>
      <path d="M4 -5 L-6 -15 L-13 -15 L-10 -5 Z" fill="#fe428e"/>
      <path d="M4 5 L-6 15 L-13 15 L-10 5 Z" fill="#fe428e"/>
      <path d="M18 0 L6 -5 L-8 -5 L-12 -2 L-12 2 L-8 5 L6 5 Z" fill="#ffffff"/>
      <circle cx="4" cy="0" r="2.6" fill="#4b3fe0"/>
    </g>
'''
    rnd = random.Random(7)
    stars = []
    for _ in range(34):
        x, y = rnd.randint(30, 870), rnd.randint(30, 236)
        dur = rnd.choice([1.4, 1.9, 2.6, 3.1]); r = rnd.choice([0.9, 1.2, 1.5])
        stars.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#ffffff" opacity="0.5">'
                     f'<animate attributeName="opacity" values="0.15;0.75;0.15" dur="{dur}s" begin="-{rnd.random() * dur:.2f}s" repeatCount="indefinite"/></circle>')
    pre = "    <!-- starfield -->\n    <g>\n" + indent(stars, 6) + "\n    </g>\n\n"
    return {"defs": f'    <path id="alien" d="{alien_d}"/>', "pre": pre, "lane": lane}


def lane_breakout():
    B0, B1 = -20, 920
    pal = ["#fe428e", "#f8d847", "#a9fef7", "#7a35d6"]
    bricks, bursts = [], []
    for i, x in enumerate(range(60, 841, 30)):
        f = (x - B0) / (B1 - B0)
        bricks.append(f'<rect x="{x - 13}" y="233" width="26" height="12" rx="2" fill="{pal[i % 4]}">{vanish(f)}</rect>')
        bursts.append(burst(x, 239, f, pal[i % 4], 13))
    lane = f'''    <!-- bricks -->
    <g>
{indent(bricks, 6)}
    </g>
{indent(bursts, 4)}

    <!-- paddle -->
    <rect y="270" width="64" height="7" rx="3.5" fill="#a9fef7" filter="url(#glow)">
      <animate attributeName="x" from="{B0 - 32}" to="{B1 - 32}" dur="{DUR}s" repeatCount="indefinite"/>
    </rect>

    <!-- ball -->
    <circle r="4.5" fill="#ffffff" filter="url(#glow)">
      <animate attributeName="cx" from="{B0}" to="{B1}" dur="{DUR}s" repeatCount="indefinite"/>
      <animate attributeName="cy" values="252;264;252" dur="0.7s" repeatCount="indefinite"/>
    </circle>
'''
    return {"defs": "", "pre": "", "lane": lane}


def lane_puzzle_bobble():
    L0, L1 = -40, 1090
    span = L1 - L0
    cols = ["#fe428e", "#a9fef7", "#f8d847", "#a78bfa"]
    groups, shots, bursts = [], [], []
    for k in range(10):
        gx = 130 + 74 * k
        col = cols[k % 4]
        edge = gx - 9
        f = ((edge - 80) - L0) / span          # moment the launcher is 80px behind the group
        a = f - 0.5 / DUR                       # shot leaves 0.5s earlier
        bubbles = ""
        for j in range(3):
            cx = gx + 20 * j
            bubbles += (f'<circle cx="{cx}" cy="{Y}" r="9" fill="{col}"/>'
                        f'<circle cx="{cx - 3}" cy="{Y - 3.5}" r="2.4" fill="#ffffff" fill-opacity="0.65"/>')
        groups.append(f'<g>{bubbles}{vanish(f)}</g>')
        s, e = edge - 103, edge - 2
        kt = f"0;{a:.4f};{f:.4f};1"
        shots.append(f'<circle cy="{Y}" r="8" fill="{col}" opacity="0">'
                     f'<animate attributeName="cx" values="{s};{s};{e};{e}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="{kt}" calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>'
                     f'</circle>')
        bursts.append(burst(gx + 20, Y, f, col, 32))
    lane = f'''    <!-- bubbles -->
    <g>
{indent(groups, 6)}
    </g>
{indent(bursts, 4)}
{indent(shots, 4)}

    <!-- launcher -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="{L0} {Y}" to="{L1} {Y}" dur="{DUR}s" repeatCount="indefinite"/>
      <rect x="2" y="-4.5" width="24" height="9" rx="4" fill="#a9fef7"/>
      <circle r="12" fill="#4b3fe0" stroke="#a9fef7" stroke-width="2"/>
      <circle r="4" fill="#a9fef7"/>
      <circle cx="-4" cy="-17" r="5" fill="#fe428e"/>
    </g>
'''
    return {"defs": "", "pre": "", "lane": lane}


def lane_bomberman():
    L0, L1 = -40, 1090
    span = L1 - L0
    blocks, bombs, flames = [], [], []
    for k in range(9):
        cx = 150 + 84 * k
        f = ((cx - 70) - L0) / span
        a = f - 1.0 / DUR
        for dx in (-12, 12):
            blocks.append(f'<g>'
                          f'<rect x="{cx + dx - 11}" y="{Y - 11}" width="22" height="22" rx="3" fill="#6d2a8f"/>'
                          f'<rect x="{cx + dx - 8}" y="{Y - 8}" width="16" height="16" rx="2" fill="none" stroke="#b18cff" stroke-opacity="0.7" stroke-width="1.5"/>'
                          f'{vanish(f)}</g>')
        kt = f"0;{a:.4f};{f:.4f};1"
        bombs.append(f'<g opacity="0">'
                     f'<circle cx="{cx}" cy="{Y}" r="9" fill="#0b0a14" stroke="#ffffff" stroke-opacity="0.35" stroke-width="1.5"><animate attributeName="r" values="8;10;8" dur="0.3s" repeatCount="indefinite"/></circle>'
                     f'<circle cx="{cx - 3}" cy="{Y - 3}" r="2" fill="#ffffff" fill-opacity="0.6"/>'
                     f'<circle cx="{cx + 6}" cy="{Y - 11}" r="2.6" fill="#f8d847"><animate attributeName="opacity" values="1;0.2;1" dur="0.2s" repeatCount="indefinite"/></circle>'
                     f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="{kt}" calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>'
                     f'</g>')
        kf = f"0;{f:.4f};{min(f + 0.04, 0.999):.4f};1"
        flames.append(f'<g opacity="0">'
                      f'<rect x="{cx - 36}" y="{Y - 7}" width="72" height="14" rx="7" fill="#fe428e"/>'
                      f'<rect x="{cx - 7}" y="{Y - 20}" width="14" height="40" rx="7" fill="#fe428e"/>'
                      f'<rect x="{cx - 30}" y="{Y - 3.5}" width="60" height="7" rx="3.5" fill="#f8d847"/>'
                      f'<rect x="{cx - 3.5}" y="{Y - 16}" width="7" height="32" rx="3.5" fill="#f8d847"/>'
                      f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="{kf}" calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>'
                      f'</g>')
    lane = f'''    <!-- soft blocks -->
    <g>
{indent(blocks, 6)}
    </g>
{indent(bombs, 4)}
{indent(flames, 4)}

    <!-- bomber -->
    <g>
      <animateTransform attributeName="transform" type="translate" from="{L0} {Y}" to="{L1} {Y}" dur="{DUR}s" repeatCount="indefinite"/>
      <g>
        <animateTransform attributeName="transform" type="translate" values="0 0;0 -1.6;0 0" dur="0.3s" repeatCount="indefinite"/>
        <line x1="0" y1="-13" x2="0" y2="-19" stroke="#ffffff" stroke-width="1.6"/>
        <circle cx="0" cy="-20" r="3" fill="#fe428e"/>
        <rect x="-7" y="6" width="14" height="8" rx="3" fill="#4b3fe0"/>
        <circle cx="0" cy="-3" r="11" fill="#ffffff"/>
        <rect x="-5" y="-9" width="15" height="10" rx="4" fill="#2a2aa8"/>
        <circle cx="0" cy="-4" r="1.7" fill="#ffffff"/>
        <circle cx="5" cy="-4" r="1.7" fill="#ffffff"/>
      </g>
      <ellipse cx="-4" cy="15" rx="4" ry="2.5" fill="#fe428e"><animate attributeName="cy" values="15;13;15" dur="0.3s" repeatCount="indefinite"/></ellipse>
      <ellipse cx="5" cy="13" rx="4" ry="2.5" fill="#fe428e"><animate attributeName="cy" values="13;15;13" dur="0.3s" repeatCount="indefinite"/></ellipse>
    </g>
'''
    return {"defs": "", "pre": "", "lane": lane}


def lane_minesweeper():
    B0, B1 = -20, 920
    rnd = random.Random(11)
    num_col = {1: "#5aa9ff", 2: "#4cd964", 3: "#ff6b6b"}
    under, over = [], []
    for i, cx in enumerate(range(96, 825, 28)):
        f = (cx - B0) / (B1 - B0)
        x = cx - 12
        cell = f'<rect x="{x}" y="{Y - 12}" width="24" height="24" rx="2" fill="#0f0d1b" stroke="#ffffff" stroke-opacity="0.14"/>'
        if rnd.random() < 0.22:   # a mine, shown flagged
            cell += (f'<line x1="{cx - 1}" y1="{Y - 7}" x2="{cx - 1}" y2="{Y + 7}" stroke="#ffffff" stroke-width="1.6"/>'
                     f'<path d="M{cx - 1} {Y - 7} L{cx + 7} {Y - 3.5} L{cx - 1} {Y} Z" fill="#fe428e"/>'
                     f'<rect x="{cx - 6}" y="{Y + 6}" width="10" height="2.4" fill="#ffffff" fill-opacity="0.85"/>')
        else:
            n = rnd.choice([1, 1, 1, 2, 2, 3])
            cell += (f'<text x="{cx}" y="{Y + 6}" text-anchor="middle" font-family="\'Courier New\', Courier, monospace" '
                     f'font-weight="900" font-size="17" fill="{num_col[n]}">{n}</text>')
        under.append(cell)
        over.append(f'<g>'
                    f'<rect x="{x}" y="{Y - 12}" width="24" height="24" rx="2" fill="#5a55a0" stroke="#2b2860"/>'
                    f'<rect x="{x + 2}" y="{Y - 10}" width="20" height="20" rx="1" fill="none" stroke="#a09bdc" stroke-opacity="0.65"/>'
                    f'{vanish(f)}</g>')
    lane = f'''    <!-- revealed cells -->
    <g>
{indent(under, 6)}
    </g>

    <!-- covered cells (open one by one) -->
    <g>
{indent(over, 6)}
    </g>

    <!-- solver cursor -->
    <rect y="{Y - 15}" width="30" height="30" rx="4" fill="none" stroke="#f8d847" stroke-width="2.5" filter="url(#glow)">
      <animate attributeName="x" from="{B0 - 15}" to="{B1 - 15}" dur="{DUR}s" repeatCount="indefinite"/>
    </rect>
'''
    return {"defs": "", "pre": "", "lane": lane}


LANES = {"pacman": lane_pacman, "galaga": lane_galaga, "breakout": lane_breakout,
         "puzzle-bobble": lane_puzzle_bobble, "bomberman": lane_bomberman, "minesweeper": lane_minesweeper}

DESCRIPTIONS = {
    "pacman": "Pac-Man eats dots while two ghosts chase him.",
    "galaga": "a Galaga-style fighter shoots a row of aliens.",
    "breakout": "a Breakout ball smashes a row of bricks.",
    "puzzle-bobble": "a launcher pops groups of matching bubbles.",
    "bomberman": "a bomber blows up soft blocks.",
    "minesweeper": "a solver opens a row of Minesweeper cells.",
}


def render_header(game, cfg):
    lane = LANES[game]()
    svg = SHELL
    title = f'{cfg["name"]} - {cfg["subtitle"]}'.strip(" -")
    svg = svg.replace("__TITLE__", escape(title))
    svg = svg.replace("__DESC__", escape(f"Arcade-style animated header: {DESCRIPTIONS[game]}"))
    svg = svg.replace("__DEFS__", lane["defs"])
    svg = svg.replace("__PRE_HUD__", lane["pre"])
    svg = svg.replace("__P1__", escape(cfg["score"]))
    svg = svg.replace("__HI__", escape(cfg["high_score"]))
    svg = svg.replace("__CREDIT__", escape(cfg["credit"]))
    svg = svg.replace("__TEXT__", text_blocks(cfg))
    svg = svg.replace("__LANE__", lane["lane"])
    return svg


# ───────────────────────────── commands ─────────────────────────────
def cmd_games():
    cfg = read_config()
    uniq = list(dict.fromkeys(cfg["body"]))
    print("games=" + ",".join(uniq))


def cmd_build():
    cfg = read_config()
    DIST.mkdir(exist_ok=True)

    (DIST / "header.svg").write_text(render_header(cfg["header"], cfg), encoding="utf-8")
    print(f"header  -> {cfg['header']}")

    placeholder = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1"/>'
    for slot in range(1, MAX_BODY + 1):
        light, dark = DIST / f"body-{slot}.svg", DIST / f"body-{slot}-dark.svg"
        if slot <= len(cfg["body"]):
            game = cfg["body"][slot - 1]
            src_l = DIST / f"{game}-contribution-graph.svg"
            src_d = DIST / f"{game}-contribution-graph-dark.svg"
            for src in (src_l, src_d):
                if not src.exists():
                    have = ", ".join(sorted(p.name for p in DIST.iterdir())) or "(empty)"
                    fail(f"Expected {src.name} in dist/ but it was not generated. Files present: {have}")
            shutil.copyfile(src_l, light)
            shutil.copyfile(src_d, dark)
            print(f"body-{slot} -> {game}")
        else:
            light.write_text(placeholder, encoding="utf-8")
            dark.write_text(placeholder, encoding="utf-8")
            print(f"body-{slot} -> (empty)")


def cmd_preview(outdir):
    cfg = read_config()
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for g in GAMES:
        (out / f"header-{g}.svg").write_text(render_header(g, cfg), encoding="utf-8")
        print("wrote", out / f"header-{g}.svg")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["games"]:
        cmd_games()
    elif args[:1] == ["build"]:
        cmd_build()
    elif args[:1] == ["preview"] and len(args) == 2:
        cmd_preview(args[1])
    else:
        print(__doc__)
        sys.exit(2)
