import requests     # Library used to send HTTPS requests (GET data from APIs)
import time         # Library used to handle time-related tasks (e.g., delays)
import urllib3      # Low-level library to silence security warnings
import json         # Library to handle JSON data (parse)

# Disable SSL warnings, Riot Games API uses self-signed certificates
# League of Legends local client uses HTTPS with self-signed certs
# Standard security rules flag this as unsafe, making Python issue warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GameWatcher:
    def __init__(self):
        # Empty dictionary to hold item prices
        # {1001: 300, 1004: 350, ...} (itemID: gold cost)
        self.item_prices = {}

        # Localhost URL for League of Legends client data, port 2999 is default for live client data
        self.live_url = "https://127.0.0.1:2999/liveclientdata"
        print("[Init] Fetching latest item prices from...")
        self._load_item_data()

    def _load_item_data(self):
        """
        Fetches latest patch version and item prices to calculate inventory value
        """

        try:
            # Get latest patch version
            # Riot's public cloud API is called data dragon or ddragon. Provides static game data
            # Calling a requests retrieves item changes in the latest patch
            versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
            # First item in the list is the latest version
            latest_version = versions[0]

            # Get item data for the latest version
            # Use the version to build the URL for item data
            item_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/item.json"

            # Fetch item data (HUGE) and parse JSON
            # ["data"] is used because raw JSONis wrapped in a metadata object
            items_data = requests.get(item_url).json()['data']

            # Extract item prices and store in dictionary
            # item_id is a string, convert to int for easier handling later
            # item_info contains all data about the item(price, stats...), we only need the price
            # Loads price of each itemID into self declared item_prices dict
            for item_id, item_info in items_data.items():
                # Store the total gold cost of the item
                self.item_prices[int(item_id)] = item_info['gold']['total']

            print(f"[Success] Loaded {len(self.item_prices)} items (Patch {latest_version})")

        except Exception as e:
            # Crash gracefully
            print(f"[Error] Could not load item data: {e}")
            exit(1) # Exit code 1 indicates program finished with error

    def get_live_gold_stats(self):
        """
        Rolls local game client to calculate team gold diff
        """
        try:
            # GET request to the local game client for the list of all players
            # verify=False: tells 'requests' not to check if SSL certificate from earlier is valid
            #timeout=1: If game client doesn't answer in 1 second, stop (prevent requests from being stuck)
            response = requests.get(
                f"{self.live_url}/playerlist",
                verify=False,
                timeout=1
            )

            # Parses JSON into python list of dicts
            players = response.json()

            blue_gold = 0
            red_gold = 0

            for player in players:
                # Current gold in inventory of player
                current_unspent = player["currentGold"]
                # Inventory value = sum of values of items in inventory
                inventory_value = 0

                # Item is a list of item objects in player's inventory
                for item in player["items"]:
                    item_id = item["itemID"]
                    # Look up item_id's price in item_prices dict (from GameWatcher class)
                    inventory_value += self.item_prices.get(item_id, 0)

                # Net worth of player = inventory gold + item value
                total_value = current_unspent + inventory_value

                # ORDER = internal code for blue side
                if player["team"] == "ORDER":
                    blue_gold += total_value
                else:
                    red_gold += total_value

            # Return dict (a JSON-like object) with live game state stats
            return {
                "timestamp": time.time(),    # Current unix timestamp
                "blue_total": blue_gold,
                "red_total": red_gold,
                "gold_diff": blue_gold - red_gold,
                "lead_team": "BLUE" if blue_gold > red_gold else "RED"
            }

        except requests.exceptions.ConnectionError:
            # Error occurs if script is ran when League client is closed
            return None

if __name__ == "__main__":
    # Initialize instance of gamewatcher class
    watcher = GameWatcher()
    print("Waiting for League of Legends to start....")

    # Infinite loop to continously check for live stats forever
    while True:
        stats = watcher.get_live_gold_stats()

        if stats:
            # \033[H\033[J is an ANSI code
            print("\033[H\033[J")
            print(f"===LIVE GAME STATE===")

            # :, formats numbers with commas (eg. 10000 -> 10,000)
            print(f"Blue Team: {stats["blue_total"]:,}g")
            print(f"Red Team: {stats["red_total"]:,}g")
            print(f"-------------------------------")
            print(f"GOLD DIFF: {stats['gold_diff']:,} ({stats["lead_team"]} LEADING)")
        else:
            # If stats is None (Game closed), print waiting message
            # end="\r" keeps print on same line, overwriting itself
            print("Game not found... retrying in 2s", end="\r")

        time.sleep(2)
