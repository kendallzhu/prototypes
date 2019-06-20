import os
import random
import datetime
import networkx as nx
import matplotlib.pyplot as plt

# undirected graph of thoughts/ideas/questions
class Void:
    SAVE_DIR = './saved_sessions/'
    ARCHIVE_DIR = './saved_sessions/archive/'
    def __init__(self):
        self.modified = False
        self.name = ''
        self.things = nx.Graph()

    # BASIC UTILITIES
    def empty(self):
        return not self.things
    
    def contains(self, thing):
        return thing in self.things

    def neighbors(self, node):
        return list(self.things[node])

    def delete_node(self, node):
        self.things.remove_node(node)

    def nodes(self):
        return list(self.things)
    
    # insert a new thing into the void from parent
    def add(self, thing, parent = None):
        if not self.name:
            self.name = thing
        if not self.contains(thing):
            self.things.add_node(thing)
        if parent and parent not in self.neighbors(thing):
            self.things.add_edge(parent, thing)

    def add_edge(self, n1, n2):
        self.things.add_edge(n1, n2)

    # INTERACTIONS
    # demand a string from user that can be used as name
    def ask_name_safe(self, prompt = '', default = ''):
        full_prompt = prompt + ':'
        if default:
            full_prompt += ' (default - ' + default + ')\n'
        while True:
            thing = input(full_prompt)
            if (not thing) and default:
                thing = default
            if not thing or thing[0] == '/':
                print('invalid, try again\n')
            else:
                break
        return thing
            
    # offer choices in a numbered list - not guaranteed answer
    def offer_choice(self, options):
        if not options:
            print('nothing found')
            return
        yes_no = len(options) == 1
        print('choose (y/n, default y)' if yes_no else 'choose #: ')
        for i, r in enumerate(options):
            print (str(i) + ') ' + r)
        choice = input()
        if yes_no:
            if choice == 'y' or choice == '':
                return options[0]
            elif choice == 'n':
                return
            else:
                print('invalid choice, picking no')
                return
        # valid numerical choice
        elif choice.isdigit() and int(choice) < len(options):
            return options[int(choice)]
        # choosing via typing the exact contents
        elif choice in options:
            return choice
        # try narrow options by search
        else:
            searched_options = [o for o in options if choice in o]
            if choice and searched_options:
                print('*narrowed options by search*')
                return self.offer_choice(searched_options)
            else:
                print('invalid choice')
                return

    # search for a node
    def search(self, thing, parent):
        results = [n for n in self.nodes() if thing in n]
        results.sort(key = lambda r: -len(self.neighbors(r)))
        choice = self.offer_choice(results)
        # TODO: add connection
        return choice
        
    # return string of neighbors of node
    def choose_neighbor(self, thing):
        if not self.contains(thing):
            return ''
        neighbors = self.neighbors(thing)
        neighbors.sort(key = lambda n: -len(self.neighbors(n)))
        return self.offer_choice(neighbors)

    # replace current node and its neighbors with new node
    def condense(self, thing):
        neighbors = self.neighbors(thing)
        for n in neighbors:
            print(n)
        default = neighbors[0] if len(neighbors) == 1 else 'cancel'
        new = self.ask_name_safe('condense all above ^ into single node', default)
        if new == 'cancel':
            return
        # collect all nodes 2 away                     
        neighbors = self.neighbors(thing)
        two_away = []
        for n in neighbors:
            for n2 in self.neighbors(n):
                if n2 != thing and n2 not in neighbors:
                    two_away.append(n2)
        # remove node and all neighbors
        self.delete_node(thing)
        for n in neighbors:
            self.delete_node(n)
        # add replacement with kept edges
        self.add(new)
        for n in two_away:
            self.add_edge(new, n)
        return new

    # return random neighbor (or just random node)
    def spit(self, thing = None):
        if self.empty():
            return ''
        if self.contains(thing) and self.neighbors(thing):
            return random.choice(self.neighbors(thing))
        return random.choice(self.nodes()) # chance to random?

    # asks user to choose between until all but one are eliminated
    def pick_tournament(self):
        print('let\'s pick something!')
        remaining = set(self.nodes())
        while len(remaining) > 1:
            a, b = remaining.pop(), remaining.pop()
            choice = None
            while not choice:
                print('/q to quit')
                choice = self.offer_choice([a, b])
                if choice == '/q':
                    print('Aborted')
                    return
            remaining.add(choice)
        chosen = remaining.pop()
        print('Your mission is to explore: ' + str(chosen))
        return chosen

    # DISPLAY
    # draw graph in new window
    def draw(self):        
        nx.draw(self.things, with_labels=True, font_weight='bold')
        plt.show()

    # SESSION SAVING
    def saved_sessions(self, directory):
        sessions = []
        files = []
        files = os.listdir(directory)
        get_path = lambda f: os.path.join(directory + f)
        files.sort(key = lambda f: os.path.getmtime(get_path(f)))
        for f in files:
            if os.path.isfile(get_path(f)):
                sessions.append(f)
        return sessions

    def rename(self):
        self.name = self.ask_name_safe('save name', self.name)
    
    # write to file in main session folder
    def save(self):
        self.rename()
        nx.write_gml(self.things, self.SAVE_DIR + self.name)
        print('saved!')
        
    # write to file with timestamp into archives folder
    def archive(self):
        self.rename()
        timestamp = datetime.datetime.now()
        time_str =  timestamp.strftime('%m_%d_%y_%H%M%S')
        archive_name = self.name + '_' + time_str
        nx.write_gml(self.things, self.ARCHIVE_DIR + archive_name)
        print('archived!')

    def delete_save(self):
        if self.name not in self.saved_sessions(self.SAVE_DIR):
            print('session not saved')
            return
        if self.offer_choice(['delete this save?']):
            if self.nodes() and self.offer_choice(['archive first?']):
                self.archive()
            os.remove(self.SAVE_DIR + self.name)
            print('deleted!')

    def delete_archive(self):
        if self.name not in self.saved_sessions(self.ARCHIVE_DIR):
            print('session not archived')
            return
        if self.offer_choice(['delete this archive?']):            
            os.remove(self.ARCHIVE_DIR + self.name)
            print('deleted!')

    def load(self, archive = False):
        directory = self.ARCHIVE_DIR if archive else self.SAVE_DIR
        name = self.offer_choice(self.saved_sessions(directory))
        if name:
            self.things = nx.read_gml(directory + name)
            self.name = name
            print('loaded!')
        
    def __str__(self):
        return self.recap()

    def loop(self):
        print('Welcome to the Void')
        old = ''
        while True:
            # spit message and take input
            new = input('(? for options): ' + old + '\n')
            # options info
            if new == '?':
                print('''COMMANDS:
                ?   - help 
                _   - create new node from here
                /_  - search for node
                //_ - search + connect to node
                /n  - list + goto neighbor
                RET - goto random neighbor
                /g  - draw graph
                /c  - condense node w/ neighbors
                /p  - pick a node (tournament-style)
                /s  - save session
                /l  - load saved session
                /d  - delete session
                /a  - archive session
                /la - load archive
                /da - delete archive
                /q  - quit
                ''')
            # special commands start with /
            elif new and new[0] == '/':
                if new == '/n' and old:
                    result = self.choose_neighbor(old)
                    if result:
                        old = result
                elif new == '/g':
                    self.draw()
                elif new == '/c' and old:
                    result = self.condense(old)
                    if result:
                        old = result
                elif new == '/p':
                    chosen = self.pick_tournament()
                    if chosen:
                        old = chosen                        
                elif new == '/l':
                    self.load()
                    old = self.name if self.contains(self.name) else ''
                elif new == '/la':
                    self.load(True)
                    old = self.name if self.contains(self.name) else ''
                elif new == '/s':
                    self.save()
                elif new == '/d':
                    self.delete_save()
                elif new == '/da':
                    self.delete_archive()
                elif new == '/a':
                    self.archive()
                elif new == '/q':
                    return
                else:
                    # double slash = search with connection
                    if len(new) > 1 and new[1] == '/':
                        result = self.search(new[2:], old)
                        self.add(result, old)
                    else:
                        # single slash = normal search
                        result = self.search(new[1:], old)
                        if result:
                            old = result
            # normal input
            elif new == '':
                old = self.spit(old)
            else:
                void.add(new, old)
                if not old:
                    old = new

if __name__ == '__main__':
    try:
        # initiate session
        void = Void()
        void.loop()
    except Exception as e:
        print(e)
