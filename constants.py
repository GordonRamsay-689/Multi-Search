
CONFIG_FILENAME = "config.env"

# Valid Commands
VALID_COMMANDS = ["-c", "-setup"]

# Client IDs
GOOGLE_ID = "google"
GEMINI_FLASH_ID = "gemini-1.5-flash"
GEMINI_PRO_ID = "gemini-1.5-pro"

# Client Aliases
ALIAS_TO_CLIENT = {
    "gemini": GEMINI_FLASH_ID,
    "gflash": GEMINI_FLASH_ID,
    "gpro": GEMINI_PRO_ID,
    "google": GOOGLE_ID,
}

# Client TYPES
TYPE_GEMINI = "gemini"
TYPE_GOOGLE = "google"

TYPES = [TYPE_GEMINI, TYPE_GOOGLE]
REQUIRES_KEY = [TYPE_GEMINI]

CLIENT_ID_TO_TYPE = {
    GEMINI_PRO_ID: TYPE_GEMINI,
    GEMINI_FLASH_ID: TYPE_GEMINI,
    GOOGLE_ID: TYPE_GOOGLE
}

# OUTPUT STRINGS (instructions, warnings, information..)

CLI_EXAMPLE_USAGE = f'''Example Usage (args are not positional): 
msearch
msearch -setup
msearch CLIENT
msearch "query" CLIENT
msearch "query" -c CLIENT
msearch "query" // Defaults to gemini-flash

To select a specific client/model use any of the following aliases:

ALIAS - CLIENT
{ALIAS_TO_CLIENT}

'msearch "query" gpro' will select {GEMINI_PRO_ID}..
'msearch "query" gflash' will select {GEMINI_FLASH_ID}..
and so on

Adding '-c' before the arguments specifying clients will start a persistent
chat.

msearch is a suggested enviroment alias, replace with python3 request_handler.py
if running directly from script directory.
'''

ERROR_SCRIPT_DIR = "Failed to get script directory."

SCRIPT_NAME = "MSearch"