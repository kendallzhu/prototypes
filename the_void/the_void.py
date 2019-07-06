import sys, os
import traceback
import random
import datetime
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter

# undirected graph of thoughts/ideas/questions
class Void:
    SAVE_DIR = './saved_sessions/'
    ARCHIVE_DIR = './saved_sessions/archive/'
    def __init__(self):
        self.modified = False
        self.name = ''
        # nodes are strings
        self.things = nx.Graph()
        # for traversal heuristic
        self.aversion = Counter()

    # BASIC UTILITIES
    def is_empty(self):
        return not self.things
    
    def contains(self, thing):
        return thing in self.things

    def neighbors(self, node):
        return list(self.things[node])

    def degree(self, node):
        return len(self.neighbors(node))

    def delete_node(self, node):
        self.modified = True
        self.things.remove_node(node)

    def nodes(self):
        return sorted(list(self.things), key = lambda n: -self.degree(n))
    
    # insert a new thing into the void from parent
    def add(self, thing, parent = None):
        self.modified = True
        if not self.name:
            self.name = thing
        if not self.contains(thing):
            self.things.add_node(thing)
        if parent and parent not in self.neighbors(thing):
            self.things.add_edge(parent, thing)

    def add_edge(self, n1, n2):
        self.modified = True
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
            if not thing or '/' in thing or '.' in thing or '\\' in thing:
                print('invalid, try again (no dots or slashes) \n')
            else:
                break
        return thing

    # offer choices in a numbered list - returns None if no answer
    def offer_choice(self, options, defaultYes = True):
        if not options:
            print('nothing found')
            return
        # special case for single option
        if len(options) == 1:
            if defaultYes:
                choice = input('0) ' + options[0] + ' (y/n, default y)\n')
            else:
                choice = input('0) ' + options[0] + ' (y/n, default n)\n')
            if choice == 'y' or choice == '0' or choice == options[0] or \
               (choice == '' and defaultYes):
                return options[0]
            elif choice == 'n' or not defaultYes:
                return
            else:
                print('invalid choice, picking no')
                return
        for i, r in enumerate(options):
            print (str(i) + ') ' + r)
        choice = input('choose #:\n')
        # valid numerical choice
        if choice.isdigit() and int(choice) < len(options):
            return options[int(choice)]
        # choosing via typing the exact contents
        elif choice in options:
            return choice
        # try narrow options by search
        else:
            searched_options = [o for o in options if choice.lower() in o.lower()]
            if choice and searched_options:
                print('*narrowed options by search*')
                return self.offer_choice(searched_options)
            else:
                print('invalid choice')
                return

    # NAVIGATION
    # search for a node
    def search(self, thing, parent):
        results = [n for n in self.nodes() if thing.lower() in n.lower()]
        choice = self.offer_choice(results)
        # TODO: add connection
        return choice
        
    # return string of neighbors of node
    def choose_neighbor(self, thing):
        if not self.contains(thing):
            return ''
        neighbors = self.neighbors(thing)
        return self.offer_choice(neighbors, False)

    # return random neighbor (or just random node)
    def spit(self, thing = None):
        if self.is_empty():
            return ''
        options = []
        if self.contains(thing) and self.neighbors(thing):
            options = self.neighbors(thing)
        else:
            options = self.nodes()
        # choose by aversion heuristic, then by less neighbors first
        options.sort(key = lambda n: (self.aversion[n], self.degree(n)))
        choice = options[0]
        # aversion increases as a node is repeatedly visited
        if self.degree(choice) > 0:
            self.aversion[choice] += 1 / self.degree(choice)
        return choice

    # DISPLAY
    # draw graph in new window
    def draw(self):
        if self.things:
            nx.draw_kamada_kawai(self.things, with_labels=True, font_weight='bold')
            plt.show()
        else:
            print('nothing to draw yet')

    # SESSION SAVING - saved files have no extension
    def saved_sessions(self, directory):
        sessions = []
        files = []
        files = os.listdir(directory)
        get_path = lambda f: os.path.join(directory + f)
        files.sort(key = lambda f: os.path.getmtime(get_path(f)))
        for f in files:
            if os.path.isfile(get_path(f)) and '.' not in f:
                sessions.append(f)
        return sessions

    def rename(self):
        self.modified = True
        self.name = self.ask_name_safe('save name', self.name)
    
    # write to file in main session folder
    def save(self):
        self.rename()
        nx.write_gml(self.things, self.SAVE_DIR + self.name)
        self.modified = False
        print('saved!')
        
    # write to file with timestamp into archives folder
    def archive(self):
        self.rename()
        timestamp = datetime.datetime.now()
        time_str =  timestamp.strftime('%m_%d_%y_%H%M%S')
        archive_name = self.name + '_' + time_str
        nx.write_gml(self.things, self.ARCHIVE_DIR + archive_name)
        print('archived!')

    def offer_archive(self):
        if self.nodes() and self.offer_choice(['archive?']):
            self.archive()

    def offer_save(self):
        if self.nodes() and self.modified and self.offer_choice(['save?']):
            self.save()
            
    def delete_save(self):
        if self.name not in self.saved_sessions(self.SAVE_DIR):
            print('session not saved')
            return
        if self.offer_choice(['delete this save?']):
            self.offer_archive()
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
            self.modified = False
            print('loaded!')

    def new_session(self):
        self.offer_save()
        self.__init__()

    # ADVANCED FEATURES
    # replace current node and its neighbors with new node
    def condense(self, thing):
        print('\n')
        neighbors = self.neighbors(thing)
        print(thing)
        for n in neighbors:
            print(n)
        default = neighbors[0] if len(neighbors) == 1 else 'dont condense'
        new = self.ask_name_safe('[condense all ^ into single node]', default)
        if new == 'dont condense':
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

    # offer comprehensive review of graph
    def compress(self):
        self.offer_archive()
        print('Try condensing edge nodes\n')
        for n in self.nodes():
            if n in self.nodes() and self.degree(n) < 2:
                result = self.condense(n)
        print('Done Compressing!')

    # asks user to choose between until all but one are eliminated
    def pick_tournament(self):
        print('let\'s pick something!')
        remaining = set(self.nodes())
        while len(remaining) > 1:
            a, b = remaining.pop(), remaining.pop()
            choice = None
            while not choice:
                choice = self.offer_choice([a, b])
                if not choice and self.offer_choice(['quit picking?']):                   
                    print('Aborted')
                    return
            remaining.add(choice)
        chosen = remaining.pop()
        print('Your mission is to explore: ' + str(chosen))
        return chosen
        
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
                print('''
COMMANDS:
    ?   - help 
    _   - create new node from here
    /_  - search for node
    //_ - search + connect to node
    /n  - pick neighbor
    RET - auto traverse (less visited neighbor)
    /g  - draw graph    
    /c  - condense node w/ neighbors
    /s  - save session
    /l  - load saved session
    /a  - archive session
    /d  - delete session
    /la - load archive
    /da - delete archive
    /ln - new session
    /q  - quit

ADVANCED:
    /pick    - pick a node (tournament-style)
    /compress - condense all leaf nodes in graph
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
                elif new == '/ln':
                    self.new_session()
                    old = 'Welcome To the Void'
                elif new == '/q':
                    return
                elif new == '/pick':
                    chosen = self.pick_tournament()
                    if chosen:
                        old = chosen
                elif new == '/compress':
                    self.compress()
                else:
                    # double slash = search with connection
                    if len(new) > 1 and new[1] == '/':
                        result = self.search(new[2:], old)
                        if result:
                            self.add(result, old)
                            old = result
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
                # automatically go to new thing when creating
                old = new

if __name__ == '__main__':
    try:
        # initiate session
        void = Void()
        void.loop()
    except Exception as _:
        print(traceback.format_exc())
