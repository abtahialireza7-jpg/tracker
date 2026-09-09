import time
import requests

# ---------------- CONFIG ----------------
WEBHOOK_URL = "https://discord.com/api/webhooks/1547101754884227082/g4LOt_MWAktMs67ToUAXT_ETN0K-4O7KQMCMoAOjr78dD3s37tfbkwppaDa0y82o-Eyd"
ROBLOX_USERNAME = "MutETempp1"
POLL_INTERVAL_SECONDS = 15

BOT_DISPLAY_NAME = "MutETempp"
AVATAR_URL = "https://cdn.discordapp.com/attachments/1547034516239945751/1547102867544875068/image.png?ex=6aa23353&is=6aa0e1d3&hm=768d3b7abfef61cb7e322992a450f58f0b91319b6d6853bbf6956783a264c7f6&"


STATUS_MESSAGES = {
    "Offline": {
        "title": "{username} went offline",
        "description": "Not being used prob",
        "color": 0x95A5A6,
    },
    "Online": {
        "title": "{username} is online",
        "description": "Online but not in game",
        "color": 0x3498DB,
    },
    "In Game": {
        "title": "{username} is playing!",
        "description": "Playing **{place}** | Being used",
        "color": 0x57F287,
    },
    "In Studio": {
        "title": "{username} is in studio",
        "description": "diddy blud in studio doing shit",
        "color": 0xE67E22,
    },
    "Unknown": {
        "title": "{username} status Unknown",
        "description": "Error67",
        "color": 0x2C2F33,
    },
}

STARTUP_MESSAGE = {
    "title": "Tracker started",
    "description": "Current status: **{status}**{place_suffix}",
    "color": 0x9B59B6,
}

ENDED_MESSAGE = {
    "title": "Tracker stopped",
    "description": "No longer Tracking **{username}**",
    "color": 0x992D22,
}

PRESENCE_TYPE_MAP = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio",
}


def get_user_id(username: str) -> int | None:
    url = "https://users.roblox.com/v1/usernames/users"
    resp = requests.post(url, json={"usernames": [username], "excludeBannedUsers": False})
    resp.raise_for_status()
    results = resp.json().get("data", [])
    return results[0]["id"] if results else None


def get_presence(user_id: int) -> dict:
    url = "https://presence.roblox.com/v1/presence/users"
    resp = requests.post(url, json={"userIds": [user_id]})
    resp.raise_for_status()
    return resp.json()["userPresences"][0]


def get_game_name(place_id: int) -> str | None:
    """Resolve a placeId to the actual game (universe) name."""
    try:
        universe_resp = requests.get(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        )
        universe_resp.raise_for_status()
        universe_id = universe_resp.json().get("universeId")
        if not universe_id:
            return None

        games_resp = requests.get(
            "https://games.roblox.com/v1/games", params={"universeIds": universe_id}
        )
        games_resp.raise_for_status()
        games = games_resp.json().get("data", [])
        return games[0]["name"] if games else None
    except requests.RequestException:
        return None


def send_simple_embed(title: str, description: str, color: int):
    embed = {"title": title, "description": description, "color": color}
    payload = {"embeds": [embed]}
    if BOT_DISPLAY_NAME:
        payload["username"] = BOT_DISPLAY_NAME
    if AVATAR_URL:
        payload["avatar_url"] = AVATAR_URL

    resp = requests.post(WEBHOOK_URL, json=payload)
    if resp.status_code >= 300:
        print(f"Webhook post failed: {resp.status_code} {resp.text}")


def send_startup_message(status: str, place_name: str | None):
    place_suffix = f" (playing **{place_name}**)" if status == "In Game" and place_name else ""
    description = STARTUP_MESSAGE["description"].format(
        username=ROBLOX_USERNAME, status=status, place_suffix=place_suffix
    )
    send_simple_embed(STARTUP_MESSAGE["title"], description, STARTUP_MESSAGE["color"])


def send_ended_message():
    description = ENDED_MESSAGE["description"].format(username=ROBLOX_USERNAME)
    send_simple_embed(ENDED_MESSAGE["title"], description, ENDED_MESSAGE["color"])


def send_webhook_update(status: str, place_name: str | None, game_start_time: float | None):
    msg_config = STATUS_MESSAGES.get(status, STATUS_MESSAGES["Unknown"])
    place = place_name or "a game"

    embed = {
        "title": msg_config["title"].format(username=ROBLOX_USERNAME, place=place),
        "description": msg_config["description"].format(username=ROBLOX_USERNAME, place=place),
        "color": msg_config["color"],
    }

    payload = {"embeds": [embed]}

    if status == "In Game":
        start_ts = int(game_start_time) if game_start_time else int(time.time())
        payload["content"] = f"Been in game since <t:{start_ts}:R>"

    if BOT_DISPLAY_NAME:
        payload["username"] = BOT_DISPLAY_NAME
    if AVATAR_URL:
        payload["avatar_url"] = AVATAR_URL

    resp = requests.post(WEBHOOK_URL, json=payload)
    if resp.status_code >= 300:
        print(f"Webhook post failed: {resp.status_code} {resp.text}")


def main():
    if not WEBHOOK_URL or WEBHOOK_URL in ("PASTE_YOUR_WEBHOOK_URL_HERE", "-") or not WEBHOOK_URL.startswith("http"):
        print("Set WEBHOOK_URL near the top of this file to your real Discord webhook URL.")
        input("Press Enter to close...")
        return

    user_id = get_user_id(ROBLOX_USERNAME)
    if user_id is None:
        print(f"Could not find Roblox user '{ROBLOX_USERNAME}'.")
        input("Press Enter to close...")
        return

    print(f"Tracking {ROBLOX_USERNAME} (id={user_id})...")

    last_status = None
    last_place_id = None
    game_start_time = None

    try:
        presence = get_presence(user_id)
        last_status = PRESENCE_TYPE_MAP.get(presence.get("userPresenceType", 0), "Unknown")
        last_place_id = presence.get("placeId")
        startup_place_name = None
        if last_status == "In Game" and last_place_id:
            startup_place_name = get_game_name(last_place_id)
            # We don't know exactly when they started, so treat "now" as the
            # start of the session we're tracking.
            game_start_time = time.time()
        send_startup_message(last_status, startup_place_name)
    except Exception as e:
        print(f"Error while sending startup message: {type(e).__name__}: {e}")

    while True:
        try:
            presence = get_presence(user_id)
            status = PRESENCE_TYPE_MAP.get(presence.get("userPresenceType", 0), "Unknown")
            place_id = presence.get("placeId")

            if status != last_status or place_id != last_place_id:
                place_name = None
                if status == "In Game" and place_id:
                    place_name = get_game_name(place_id)

                if status == "In Game":
                    # New game session (either just started, or switched games) -> reset the clock.
                    game_start_time = time.time()
                else:
                    game_start_time = None

                send_webhook_update(status, place_name, game_start_time)
                last_status = status
                last_place_id = place_id
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping...")
        try:
            send_ended_message()
        except Exception as e:
            print(f"Could not send the stop message: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"\nThe script crashed: {type(e).__name__}: {e}")
        input("Press Enter to close...")