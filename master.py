import api_session
import google.generativeai
import request_handler
import re
import threading
import os 
import sys
import time
import ui

from constants import * ## Global constants

def get_script_dir():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        fatal_error(ERROR_SCRIPT_DIR)

    return script_dir

class Master:
    def __init__(self):
        self._finished = threading.Event()

        self.cli_lock = threading.Lock()

        self.handler = request_handler.RequestHandler(self.cli_lock, self)

        self.configured_gemini = False

        self.clients = []
        self.sessions = []
        self.query = ''
        self.persistent_chat = False

    def reset(self):
        for session in self.sessions:
            session.client.reset()
        self.query = ''


    def configure(self, aliases):        
        self.populate_clients(aliases)
        self.configure_clients()
        self.populate_sessions()
        self.handler.sessions = self.sessions

    def configure_clients(self):
        for client_id in self.clients:
            if CLIENT_ID_TO_TYPE[client_id] == TYPE_GEMINI:
                if not self.configured_gemini:
                    google.generativeai.configure(api_key=os.environ["GEMINI_API"])
                    self.configured_gemini = True
        
    def populate_clients(self, aliases):
        while True:
            for alias in aliases:
                client_id = ALIAS_TO_CLIENT[alias]

                if client_id not in self.clients:
                    self.clients.append(client_id)
            
            if self.clients:
                return
            
    def populate_sessions(self):
        for client_id in self.clients:
            session = api_session.Session(client_id)
            self.sessions.append(session)

    def remove_clients(self, matches):
        for match in matches:
            try:
                client_id = ALIAS_TO_CLIENT[match]
            except KeyError:
                continue

            if client_id in self.clients:
                self.clients.remove(client_id)

                for session in self.sessions:
                    if session.client.name == client_id:
                        self.sessions.remove(session)
    
    def add_clients(self, matches):
        for match in matches:
            try:
                client_id = ALIAS_TO_CLIENT[match]
            except KeyError:
                continue

            if client_id not in self.clients:
                self.clients.append(client_id)

                session = api_session.Session(client_id)
                self.sessions.append(session)
                self.configure_clients()

    def extract_flags(self):
        query = self.query

        pattern_add_client = r"--add:(\S+)"
        matches = re.findall(pattern_add_client, query)
        if matches:
            self.add_clients(matches)
        query = re.sub(pattern_add_client, '', query)

        pattern_remove_client = r"--rm:(\S+)"
        matches = re.findall(pattern_remove_client, query)
        if matches:
            self.remove_clients(matches)
        query = re.sub(pattern_remove_client, '', query)

        # pattern_restart_chat = r"--reset"
        # match = re.match
        # if matches:
        #     print("resetting")
        #     client
        #     self.clear_sessions()
        #     self.add_client()
        # query = re.sub(pattern_restart_chat, '', query)

        if query:
            self.query = query

    def get_query(self):
        with self.cli_lock:
            ui.c_out("Enter your query (triple click enter to submit):")
            self.query = ui.c_in()

    def main(self):
        while True:
            with self.cli_lock:
                ui.c_out(f"Active clients: {self.clients}")

            while not self.query: # If we already got a query from args, do not ask for one
                self.get_query()

            self.extract_flags()

            if self.sessions:
                with self.cli_lock:
                    ui.c_out("Submitting requests...", isolate=True, indent=1)
            else:
                with self.cli_lock:
                    ui.c_out("No active sessions.", isolate=True, indent=1)
            
            self.handler.submit_requests(self.query)
            self.handler.monitor_requests()

            if self.persistent_chat:
                self.reset()
            else:
                sys.exit()

def fatal_error(error_message):
    ui.c_out("Error: ", color=DRED, endline=False)
    ui.c_out(f"{error_message}", indent=1)
    sys.exit()

def select_aliases():
    aliases = []

    while not aliases:
        ui.c_out("Please enter the clients you wish to use:", bottom_margin=True)
        ui.c_out(f"{"Alias":^10}   {"Client":^10}", indent=1)
        ui.c_out("-"*23, indent=1)

        for alias in sorted(ALIAS_TO_CLIENT.keys()):
            ui.c_out(f"{alias:10}", indent=1, endline=False)
            ui.c_out(" > ", endline=False)
            ui.c_out(ALIAS_TO_CLIENT[alias])
        
        ui.c_out("")
        text = input("> ")
        for alias in sorted(ALIAS_TO_CLIENT.keys()):
            if alias in text:
                aliases.append(alias)

    return aliases

def parse_arguments(args):
    commands = []
    client_aliases = []

    # If first argument is not a client or command, assume it is a query.
    if args[0] not in VALID_COMMANDS and args[0] not in ALIAS_TO_CLIENT.keys():
        query = args.pop(0)
    else:
        query = None

    while args:
        arg = args.pop(0)
        arg = arg.lower()

        if arg.startswith('-'):
            if arg in VALID_COMMANDS:
                commands.append(arg)
            else:
                fatal_error(f"Unknown command: {arg}")          
        elif arg.lower() in ALIAS_TO_CLIENT.keys():
            client_aliases.append(arg)
        else:
            fatal_error(f"Unknown command: {arg}")
    
    if not client_aliases:
        ui.c_out("No client alias provided.")
        ui.c_out(f"\nDefaulting to {GEMINI_FLASH_ID}.")
        client_aliases.append("gflash")   

    return query, commands, client_aliases

if __name__ == '__main__':
    script_dir = get_script_dir()

    master = Master()

    if len(sys.argv) < 2:
        client_aliases = select_aliases()
        master.persistent_chat = True
    else: 
        query, commands, client_aliases = parse_arguments(sys.argv[1:])

        for command in commands:
            if command == '-help':
                ui.c_out(CLI_HELP)
                sys.exit()
            elif command == '-c':
                master.persistent_chat = True

        if not query:
            master.persistent_chat = True

        master.query = query
    
    master.configure(client_aliases)
    master.main()
