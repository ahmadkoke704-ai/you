#!/usr/bin/env python3
"""
=============================================================================
 GroupHelp Telegram Bot • Standalone Interactive Terminal Console
 Locked with security password: ah.adhsan900
=============================================================================
"""

import sys
import os
import json
import urllib.request
import urllib.error

API_URL = "http://127.0.0.1:5005/api/terminal"

def send_terminal_cmd(cmd: str) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"command": cmd}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"output": f"Connection error: {e}", "authenticated": False}

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear()
    banner = (
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║       🔒 TELEGRAM FORCED ADD BOT - SECURE MANAGEMENT CONSOLE        ║\n"
        "║                   GROUPHELP PREMIUM EDITION                          ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝"
    )
    print(banner)

    # Prompt immediately for password
    try:
        pwd = input("[SECURITY ACCESS GATE] Enter Master Password: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return

    res = send_terminal_cmd(pwd)
    if not res.get("authenticated", False):
        clear()
        print("❌ ACCESS DENIED! Invalid security password. Access rejected.\n")
        return

    clear()
    print(res.get("output", ""))

    while True:
        try:
            cmd = input("admin@grouphelp-bot:~$ ").strip()
            if not cmd:
                continue
            if cmd in ("exit", "quit", "q"):
                print("Exiting CLI session.")
                break
            res = send_terminal_cmd(cmd)
            print(res.get("output", ""))
            if not res.get("authenticated", True):
                print("🔒 Session locked. Authentication required.")
                break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI session.")
            break

if __name__ == "__main__":
    main()
