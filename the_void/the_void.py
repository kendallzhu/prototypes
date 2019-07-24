import sys, os
import traceback
import random
import datetime
import networkx as nx
# hack to make use same backend
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import Counter
from colorama import init, Fore, Back, Style

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
        self.weighted_visits = Counter()
        # for traversing back
        self.visit_history = []
        # initialize colorama for windows, but not if on eshell
        if os.name == 'nt' and not('EMACS_DIR' in os.environ):
            init()

    # BASIC UTILITIES
    def is_empty(self):
        return not self.things
    
    def contains(self, thing):
        return thing in self.things

    def neighbors(self, node):
        return sorted(list(self.things[node]), key = lambda n: -self.degree(n))

    def degree(self, node):
        return len(self.things[node])

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

    def is_valid_node_name(self, name):
        return name and name[0] != '/'

    # DISPLAY + STYLES
    def print_welcome(self):
        print(Style.BRIGHT + 'Welcome To The Void' + Style.RESET_ALL)
        
    def print_current(self, node, **kwargs):
        print(Fore.GREEN + node + Style.RESET_ALL, **kwargs)

    def print_prompt(self, node, **kwargs):
        print(Style.BRIGHT + node + Style.RESET_ALL, **kwargs)

    def print_default(self, text, **kwargs):
        print(Fore.MAGENTA + text + Style.RESET_ALL, **kwargs)
        
    # INTERACTIONS    
    # get a string from user that can be used as node, abort => None
    def ask_node_name(self, prompt = '', default = None):
        self.print_prompt(prompt, end = '')
        if default:
            self.print_default('(default - {})\n'.format(default), end = '')
        name = input()
        if (not name) and default:
            print(default)
            name = default
        if not self.is_valid_node_name(name):
            print('invalid, aborting\n')
            return None
        return name
    
    # get a string from user that can be used as file name, can return None
    def ask_file_name(self, prompt = '', default = ''):
        print(prompt, end = '')
        if default:
            self.print_default('(default - {})\n'.format(default), end = '')
        name = input()
        if (not name) and default:
            print(default)
            name = default
        if not name or '/' in name or '.' in name or '\\' in name:
            print('invalid file name, aborting\n')
            return None
        return name

    # offer choices in a numbered list - returns None if no answer
    def offer_choice(self, options, **kwargs):
        default = kwargs.get('default', None)
        allow_rng = kwargs.get('allow_rng', False)
        if not options:
            print('no options to choose from')
            return
        if not (type(default) == int and default < len(options)):
            default = None
        # special y/n query for single option, always default
        if len(options) == 1:
            default_string = 'y' if default == 0 else 'n'
            print('0) ' + options[0], end = '')
            self.print_default(' (y/n, default {})\n'.format(default_string), end = '')
            choice = input()
            if choice == 'y' or choice == '0' or choice == options[0] or \
               (choice == '' and default == 0):
                print('y')
                return options[0]
            elif choice == 'n' or default != 0:
                return
            else:
                print('invalid choice, picking no')
                return
        print('')
        for i, r in enumerate(options):
            print (str(i) + ') ' + r)
        # multiple options - numerical list
        if allow_rng:
            self.print_default('(decimal => rng for option 0)')
        if default:
            prompt = 'choose # or search (default - {}):'.format(default)
        else:
            prompt = 'choose # or search:'
        self.print_prompt(prompt)
        choice = input()
        if choice.isdigit() and int(choice) < len(options):
            return options[int(choice)]
        # choosing via typing the exact contents
        elif choice in options:
            return choice
        elif not choice and default:
            print(default)
            return options[default]
        # see if user input probability for first option
        elif allow_rng:
            try:
                probability = float(choice)
            except:
                probability = 0
            # only interpret decimals between 0 and 1 exclusive as probabilities
            if choice[0] == '.' or (probability > 0 and probability < 1):
                if random.random() < probability:
                    return options[0]
                else:
                    if len(options) == 2:
                        return options[1]
                    return self.offer_choice(options[1:], allow_rng = True)
        # try narrow options by search
        else:
            searched_options = [o for o in options if choice.lower() in o.lower()]
            if choice and searched_options:
                print('*narrowed options by search*')
                return self.offer_choice(searched_options, default = 0)
            else:
                print('invalid choice')
                return

    # NAVIGATION
    # search for a node
    def search(self, thing, parent):
        results = [n for n in self.nodes() if thing.lower() in n.lower()]
        if results:
            print('search results:')
            choice = self.offer_choice(results, default = 0)
            if choice:
                self.reset_all_visits()
                self.visit(choice)
            return choice
        else:
            print('search: nothing found')
        
    # return string of neighbors of node
    def choose_neighbor(self, thing):
        if not self.contains(thing):
            return ''
        neighbors = self.neighbors(thing)
        return self.offer_choice(neighbors)

    def visit(self, node):
        assert(self.contains(node))
        # weighted_visits increases as a node is repeatedly visited
        if self.degree(node) > 0:
            self.weighted_visits[node] += 1 / self.degree(node)
        self.visit_history.append(node)

    def reset_all_visits(self):
        self.weighted_visits = Counter()

    def primary_node(self):
        options = self.nodes()
        # largest degree, then shortest name
        options.sort(key = lambda n: (-self.degree(n), len(n)))
        return options[0]
        
    # return neighbor based on least visited (weighted)
    def auto_traverse(self, thing = None):
        if self.is_empty():
            return ''
        if not self.contains(thing) or not self.neighbors(thing):
            # TODO: should visit here or nah?
            return self.primary_node()
        options = self.neighbors(thing)
        # choose by weighted_visits heuristic, then by less neighbors first
        options.sort(key = lambda n: (self.weighted_visits[n], self.degree(n)))
        choice = options[0]
        self.visit(choice)
        return choice

    # to nodes with more neighbors, and more visited (likely where we came from)
    def traverse_back(self, thing):
        if self.is_empty() or not self.visit_history or not self.contains(thing):
            return ''
        if thing == self.visit_history[-1]:
            self.visit_history.pop()
        return self.visit_history.pop()

    # VISUALIZATION
    # draw graph in new window
    def draw(self):
        if self.things:
            print('Drawing Graph...', flush=True)
            # copy graph with line breaks - TODO: factor out edit? map?
            def insert_newlines(string, every):
                lines = []
                start = 0
                while start < len(string):
                    end = start + every
                    while end < len(string) and string[end] !=  ' ':
                        end += 1
                    lines.append(string[start:end])
                    start = end
                return '\n'.join(lines)
            pretty_version = nx.Graph()
            pretty_version.add_nodes_from(self.things)
            pretty_version.add_edges_from(self.things.edges)
            for node in [n for n in pretty_version.nodes()]:
                neighbors = pretty_version[node]
                pretty_version.remove_node(node)
                new = insert_newlines(node, 20)
                pretty_version.add_node(new)
                for n in neighbors:
                    pretty_version.add_edge(new, n)
            nx.draw_kamada_kawai(pretty_version, with_labels=True, font_weight='bold')
            mng = plt.get_current_fig_manager()
            # mng.window.state('zoomed')
            # hack to cause window focus, not sure why it works
            mng.window.state('iconic')
            mng.window.minsize(width = 1080, height = 640)
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

    # change name of session and return it, return None if aborted
    def rename(self):
        new_name = self.ask_file_name('save name: ', self.name)
        if not new_name:
            return
        self.modified = True
        self.name = new_name
        return new_name
    
    # write to file in main session folder
    def save(self):
        new_name = self.rename()
        if not new_name:
            return
        nx.write_gml(self.things, self.SAVE_DIR + self.name)
        self.modified = False
        print('saved!')
        
    # write to file with timestamp into archives folder
    def archive(self):
        new_name = self.rename()
        if not new_name:
            return
        timestamp = datetime.datetime.now()
        time_str =  timestamp.strftime('%m_%d_%y_%H%M%S')
        archive_name = self.name + '_' + time_str
        nx.write_gml(self.things, self.ARCHIVE_DIR + archive_name)
        print('archived!')

    def offer_archive(self):
        if self.nodes() and self.offer_choice(['archive?'], default = 0):
            self.archive()

    def offer_save(self):
        if self.nodes() and self.modified and self.offer_choice(['save?'], default = 0):
            self.save()
            
    def delete_save(self):
        if self.name not in self.saved_sessions(self.SAVE_DIR):
            print('session not saved')
            return
        if self.offer_choice(['delete this save?'], default = 0):
            self.offer_archive()
            os.remove(self.SAVE_DIR + self.name)
            print('deleted!')

    def delete_archive(self):
        if self.name not in self.saved_sessions(self.ARCHIVE_DIR):
            print('session not archived')
            return
        if self.offer_choice(['delete this archive?'], default = 0):            
            os.remove(self.ARCHIVE_DIR + self.name)
            print('deleted!')

    def load(self, archive = False):
        directory = self.ARCHIVE_DIR if archive else self.SAVE_DIR
        name = self.offer_choice(self.saved_sessions(directory))
        if name:
            self.__init__()
            self.things = nx.read_gml(directory + name)
            self.name = name
            print('loaded!')

    def new_session(self):
        self.offer_save()
        self.__init__()
        self.print_welcome()

    # ADVANCED FEATURES
    # replace current node and its neighbors with new node
    def condense(self, thing):
        print('\n')
        neighbors = self.neighbors(thing)
        print(thing)
        for n in neighbors:
            print(n)
        default = neighbors[0] if len(neighbors) == 1 else None
        new = self.ask_node_name('[condense all ^ into single node]: \n', default)
        if not new:
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
                _ = self.condense(n)
        print('Done Compressing!')

    # asks user to choose between random pairs until all but one are eliminated
    def pick_tournament(self):
        print('let\'s pick something! (tournament style)')
        remaining = set(self.nodes())
        least_played = set(remaining)
        while len(remaining) > 1:
            if len(least_played) <= 1:
                least_played = set(remaining)
            a, b = least_played.pop(), least_played.pop()
            choice = None
            while not choice:
                choice = self.offer_choice([a, b], allow_rng = True)
                if not choice and self.offer_choice(['quit picking?'], default = 0):
                    print('Aborted')
                    return
            remaining.remove(a)
            remaining.remove(b)
            remaining.add(choice)
        chosen = remaining.pop()
        print('Chosen: ' + str(chosen))
        return chosen

    # asks user to choose between neighbors from current node outward (faster)
    def pick_branching(self, start_node = None):
        if start_node == None:
            start_node = self.primary_node()
        print('let\'s pick something! (quick branching style)')
        eliminated = set([])
        options = self.neighbors(start_node) + [start_node]
        choice = None
        while len(options) > 1:
            choice = None
            while not choice:
                choice = self.offer_choice(options, allow_rng = True)
                if not choice and self.offer_choice(['quit picking?']):                   
                    print('Aborted')
                    return
            eliminated.update(options)
            next_batch = self.neighbors(choice) + [choice]
            options = [ n for n in next_batch if n not in eliminated ]
        print('Chosen: ' + str(choice))
        return choice

        
    def __str__(self):
        return self.recap()

    def loop(self):
        self.print_welcome()
        old = ''
        while True:
            # spit message and take input
            self.print_prompt('(? for options): ', end = '')
            self.print_current(old)
            new = input()
            # options info
            if new == '?':
                print('''
COMMANDS:
    ?   - help (online docs one day?)
    _   - create new node from here
    RET - auto traverse (less visited neighbor)
    /b  - traverse back
    //_ - search for node
    /+_ - search + connect to node
    /n  - pick neighbor
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
    /pick     - pick a node (tournament-style)
    /pick!    - pick a node (quick-branching-style)
    /compress - condense all leaf nodes in graph
                ''')
            # special commands start with /
            elif new and new[0] == '/':
                if new == '/b':
                    result = self.traverse_back(old)
                    if result:
                        old = result
                elif new == '/n' and old:
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
                    old = self.auto_traverse()
                elif new == '/la':
                    self.load(True)
                    old = self.auto_traverse()
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
                    old = ''
                elif new == '/q':
                    return
                elif new == '/pick':
                    chosen = self.pick_tournament()
                    if chosen:
                        old = chosen
                elif new == '/pick!':
                    chosen = self.pick_branching(old)
                    if chosen:
                        old = chosen
                elif new == '/compress':
                    self.compress()
                else:
                    if len(new) > 1 and new[1] == '+':
                        # search with connection
                        result = self.search(new[2:], old)
                        if result:
                            self.add(result, old)
                            old = result
                    elif len(new) > 1 and new[1] == '/':
                        # normal search
                        result = self.search(new[2:], old)
                        if result:
                            old = result
                    else:
                        print('unrecognized command')
                        if len(new) > 1 and self.offer_choice(['did you mean to search?']):
                            result = self.search(new[2:], old)
                            if result:
                                old = result
            # normal input
            elif new == '':
                old = self.auto_traverse(old)
            elif self.is_valid_node_name(new):
                self.add(new, old)
                # automatically go to new thing when creating
                old = new
            else:
                print('invalid node name, try again\n')

if __name__ == '__main__':
    try:
        # initiate session
        void = Void()
        void.loop()
    except Exception as _:
        print(traceback.format_exc())
