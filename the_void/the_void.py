import os
import traceback
import random
import datetime
import networkx as nx
from collections import Counter
from colorama import init, Fore, Style
# hack to make use same backend
import matplotlib
matplotlib.use('TkAgg')


# undirected graph of thoughts/ideas/questions
class Void:
    SAVE_DIR = './saved_sessions/'
    SNAPSHOT_DIR = './saved_sessions/snapshots/'

    def __init__(self):
        self.modified = False
        self.name = ''
        # nodes are strings
        self.graph = nx.DiGraph()
        # for traversal heuristic
        self.num_visits = Counter()
        # for traversing back
        self.visit_history = []
        # for getting recent additions
        self.recently_added = []
        # initialize colorama for windows, but not if on eshell
        if os.name == 'nt' and not('EMACS_DIR' in os.environ):
            init()

    # BASIC UTILITIES
    def is_empty(self):
        return not self.graph

    def contains(self, node):
        return node in self.graph

    def degree(self, node):
        return self.graph.degree(node)

    def in_degree(self, node):
        return self.graph.in_degree(node)

    def out_degree(self, node):
        return self.graph.out_degree(node)

    def nodes(self):
        all_nodes = [n for n in self.graph]
        # put node with fewest parents first (source of the graph)
        return sorted(all_nodes, key=lambda n: len(self.parents(n)))

    def children(self, node):
        return [n for n in self.graph
                if n in self.graph[node] and
                node not in self.graph[n]]

    def siblings(self, node):
        return [n for n in self.graph
                if n in self.graph[node] and
                node in self.graph[n]]

    def parents(self, node):
        return [n for n in self.graph
                if node in self.graph[n] and
                n not in self.graph[node]]

    def neighbors(self, node):
        return self.children(node) + self.siblings(node) + self.parents(node)

    def is_valid_node_name(self, name):
        return name and name[0] != '/'

    def add_parent(self, node, node_from=None):
        self.modified = True
        if not self.name:
            self.name = node
        if not self.contains(node):
            self.graph.add_node(node)
            self.set_time_created(node)
        if node_from and node_from not in self.neighbors(node):
            self.graph.add_edge(node, node_from)
        return node

    def add_child(self, node, node_from=None):
        self.modified = True
        if not self.name:
            self.name = node
        if not self.contains(node):
            self.graph.add_node(node)
            self.set_time_created(node)
        if node_from and node_from not in self.neighbors(node):
            self.graph.add_edge(node_from, node)
        return node

    def add_sibling(self, node, node_from=None):
        self.modified = True
        if not self.name:
            self.name = node
        if not self.contains(node):
            self.graph.add_node(node)
            self.set_time_created(node)
        if node_from and node_from not in self.siblings(node):
            for s in self.siblings(node_from):
                self.graph.add_edge(s, node)
                self.graph.add_edge(node, s)
            for p in self.parents(node_from):
                self.graph.add_edge(p, node)
            self.graph.add_edge(node_from, node)
            self.graph.add_edge(node, node_from)
        return node

    def add_node(self, node, node_from=None, relationship='sibling'):
        if type(node) != str:
            self.print_red('Can only add strings as nodes!')
            return
        if not self.is_valid_node_name(node):
            self.print_red('Invalid node name')
            return
        if node in self.nodes():
            self.print_red('Node name already in graph')
            if not self.offer_choice(['connect to existing?'], default=0):
                return
        # reset navigation counters when adding a new node
        self.reset_all_visits()
        if node_from and relationship == 'child':
            return self.add_child(node, node_from)
        elif node_from and relationship == 'parent':
            return self.add_parent(node, node_from)
        else:
            assert(relationship == 'sibling')
            return self.add_sibling(node, node_from)

    def remove_node_and_edges(self, node):
        self.modified = True
        self.graph.remove_node(node)

    def add_edge(self, n1, n2):
        self.modified = True
        self.graph.add_edge(n1, n2)

    def can_remove_edge(self, n1, n2):
        test_graph = nx.Graph(self.graph.copy())
        test_graph.remove_edge(n1, n2)
        return nx.is_connected(test_graph)

    def remove_edge(self, n1, n2):
        if not self.can_remove_edge(n1, n2):
            self.print_red('removing edge would disconnect graph, aborting')
            return
        self.graph.remove_edge(n1, n2)
        self.modified = True

    # functions for creation timestamps (to keep the constants in one place)
    def set_time_created(self, node):
        assert(node in self.graph)
        epoch = datetime.datetime.utcfromtimestamp(0)
        timestamp = datetime.datetime.now()
        epoch_time = (timestamp - epoch).total_seconds()
        self.graph.nodes[node]['timeCreated'] = epoch_time

    def get_time_created(self, node):
        if 'time_created' in self.graph.nodes[node]:
            return self.graph.nodes[node]['timeCreated']
        else:
            return datetime.datetime.min

    # not really a class function but I think clearer to put here
    @staticmethod
    def edit_networkX_node(graph, node, new):
        edges = [e for e in graph.edges() if node in e]
        graph.remove_node(node)
        graph.add_node(new)
        for e in edges:
            if e[0] == node:
                assert(e[1] != node)
                graph.add_edge(new, e[1])
            elif e[1] == node:
                graph.add_edge(e[0], new)
            else:
                assert(False)

    def edit_node(self, node, new):
        self.modified = True
        Void.edit_networkX_node(self.graph, node, new)

    def get_recent(self, number):
        nodes_by_time = sorted(self.nodes(), key=self.get_time_created)
        nodes_by_time.reverse()
        num_return = min(number, len(nodes_by_time))
        return nodes_by_time[0:num_return]

    def debug_print(self):
        print(self.graph.nodes.data())
        print(self.num_visits)

    # DISPLAY + STYLES
    def print_welcome(self):
        print(Style.BRIGHT + 'Welcome To The Void' + Style.RESET_ALL)

    def print_green(self, node, **kwargs):
        print(Fore.GREEN + node + Style.RESET_ALL, **kwargs)

    def print_bold(self, node, **kwargs):
        print(Style.BRIGHT + node + Style.RESET_ALL, **kwargs)

    def print_purple(self, text, **kwargs):
        print(Fore.MAGENTA + text + Style.RESET_ALL, **kwargs)

    def print_red(self, text, **kwargs):
        print(Fore.RED + text + Style.RESET_ALL, **kwargs)

    def print_with_family(self, node):
        self.print_bold("\nparents - [# children]:")
        for n in self.parents(node):
            s = n + ' [' + str(len(self.children(n))) + ']'
            print(s)
        if self.parents(node) == []:
            print("None")
        self.print_bold("\nsiblings - [# children]:")
        for n in self.siblings(node):
            s = n + ' [' + str(len(self.children(n))) + ']'
            print(s)
        if self.siblings(node) == []:
            print("None")
        self.print_bold("\nchildren - [# children]:")
        for n in self.children(node):
            s = n + ' [' + str(len(self.children(n))) + ']'
            print(s)
        if self.children(node) == []:
            print("None")
        self.print_green(node)

    # INTERACTIONS
    # get a string from user that can be used as node, abort => None
    def ask_node_name(self, prompt='', default=None):
        self.print_bold(prompt, end='')
        if default:
            self.print_purple('(default - {})\n'.format(default), end='')
        name = input()
        if (not name) and default:
            print(default)
            name = default
        if not self.is_valid_node_name(name):
            self.print_red('invalid, aborting\n')
            return None
        return name

    # get a string from user that can be used as file name, can return None
    def ask_file_name(self, prompt='', default=''):
        print(prompt, end='')
        if default:
            self.print_purple('(default - {})\n'.format(default), end='')
        name = input()
        if (not name) and default:
            print(default)
            name = default
        if not name or '/' in name or '.' in name or '\\' in name:
            self.print_red('invalid file name, aborting\n')
            return None
        return name

    # offer choices in a numbered list - returns None if no answer
    def offer_choice(self, options, **kwargs):
        default = kwargs.get('default', None)
        allow_rng = kwargs.get('allow_rng', False)
        if not options:
            self.print_red('no options to choose from')
            return
        if default is not None and \
           not (type(default) == int and default < len(options)):
            self.print_red('BUG - invalid default given to offer_choice')
            default = None
        # special y/n query for single option, always default
        if len(options) == 1:
            print('0) ' + options[0], end='')
            def_s = 'y' if default == 0 else 'n'
            self.print_purple(' (y/n, default {})\n'.format(def_s), end='')
            choice = input()
            if choice == 'y' or choice == '0' or choice == options[0]:
                return options[0]
            if choice == '' and default == 0:
                self.print_purple('defaulting - yes')
                return options[0]
            if choice == 'n':
                return
            if choice == '' and default != 0:
                self.print_purple('defaulting - no')
                return
            self.print_red('invalid choice, picking no')
            return
        for i, r in enumerate(options):
            print(str(i) + ') ' + r)
        # multiple options - numerical list
        if allow_rng:
            self.print_purple('(decimal => rng for option 0)')
        if default is not None:
            prompt = 'choose # or search (default - {}):'.format(
                options[default])
        else:
            prompt = 'choose # or search:'
        self.print_bold(prompt)
        choice = input()
        if choice.isdigit() and int(choice) < len(options):
            return options[int(choice)]
        # choosing via typing the exact contents
        elif choice in options:
            return choice
        elif not choice and default is not None:
            print(options[default])
            return options[default]
        # see if user input probability for first option
        elif allow_rng and choice:
            try:
                probability = float(choice)
            except ValueError:
                probability = 0
            # only interpret decimals between 0 and 1 exclusive as probability
            if choice[0] == '.' or (probability > 0 and probability < 1):
                if random.random() < probability:
                    print(options[0])
                    return options[0]
                else:
                    if len(options) == 2:
                        print(options[1])
                        return options[1]
                    return self.offer_choice(options[1:], allow_rng=True)
        # try narrow options by search
        else:
            searched = [o for o in options if choice.lower() in o.lower()]
            if choice and searched:
                print('*narrowed options by search*')
                return self.offer_choice(searched, default=0)
            else:
                self.print_red('invalid choice')
                return

    # NAVIGATION
    # search for a node
    def search(self, node):
        node = node.strip()
        results = [n for n in self.nodes() if node.lower() in n.lower()]
        if results:
            self.print_bold('Search Results:')
            choice = self.offer_choice(results, default=0)
            if choice:
                self.reset_all_visits()
                self.visit(choice)
            return choice
        else:
            self.print_red('search: nothing found')

    def choose_recent(self):
        print('Recently Changed:')
        recents = self.get_recent(5)
        return self.offer_choice(recents)

    def visit(self, node):
        assert(self.contains(node))
        self.num_visits[node] += 1
        self.visit_history.append(node)

    def reset_all_visits(self):
        self.num_visits = Counter()

    def primary_node(self):        
        return self.nodes()[0]

    def auto_traverse(self, node=None):
        if self.is_empty():
            return ''
        if not self.contains(node) or not self.neighbors(node):
            p = self.primary_node()
            return p
        options = []
        # choose less visits, prioritizing siblings then children then parents
        options += sorted(
            self.neighbors(node),
            key=lambda n:
            (self.num_visits[n], n in self.parents(n), n in self.children(n)))
        choice = options[0]
        return choice

    def traverse_back(self, node):
        if self.is_empty() or not self.visit_history or \
           not self.contains(node):
            return ''
        while self.visit_history:
            prev = self.visit_history.pop()
            if prev in self.nodes() and prev != node:
                return prev
        return node

    # VISUALIZATION
    # draw graph in new window
    def draw(self):
        if self.graph:
            print('Drawing Graph... \n(Close window to resume)', flush=True)

            # copy prettified version of the map
            def insert_newlines(string, every):
                lines = []
                start = 0
                while start < len(string):
                    end = start + every
                    while end < len(string) and string[end] != ' ':
                        end -= 1
                        if end == start:
                            end = start + every
                            break
                    lines.append(string[start:end])
                    start = end
                return '\n'.join(lines)

            def format_node_text(string):
                return insert_newlines(string, 22)
            pretty_version = self.graph.copy()
            # color todo
            color_map = []
            for n in pretty_version.nodes():
                color_map.append('#00a400')

            # format text
            for node in [n for n in pretty_version.nodes()]:
                text = format_node_text(node)
                Void.edit_networkX_node(pretty_version, node, text)

            distances = dict()
            for n in pretty_version.nodes():
                distances[n] = dict()
                for n2 in pretty_version.nodes():
                    if n != n2:
                        undirected = nx.Graph(pretty_version)
                        d = nx.shortest_path_length(undirected, n, n2)
                        distances[n][n2] = 2 + d
            pos = nx.kamada_kawai_layout(pretty_version, dist = distances)
            nx.draw(
                pretty_version,
                pos,
                with_labels=True,
                font_weight='bold',
                node_color=color_map,
                edge_color='gray'
            )
            mng = matplotlib.pyplot.get_current_fig_manager()
            # mng.window.state('zoomed')
            # hack to cause window focus, not sure why it works
            mng.window.state('iconic')
            mng.window.minsize(width=1080, height=640)
            matplotlib.pyplot.margins(x=.12)
            matplotlib.pyplot.show()
        else:
            self.print_red('nothing to draw yet')

    # SESSION SAVING - saved files have no extension
    def saved_sessions(self, directory):
        sessions = []
        files = []
        files = os.listdir(directory)

        def get_path(name):
            return os.path.join(directory + name)
        files.sort(key=lambda f: os.path.getmtime(get_path(f)))
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
        while (self.name in self.saved_sessions(self.SAVE_DIR)):
            if self.offer_choice(['overwrite existing save of same name?']):
                break
            else:
                new_name = self.rename()
        if not new_name:
            return
        nx.write_gml(self.graph, self.SAVE_DIR + self.name)
        self.modified = False
        print('saved!')

    def auto_save(self):
        if self.modified:
            nx.write_gml(self.graph, self.SAVE_DIR + 'auto_save')
            self.print_red('auto-saved!')

    # write to file with timestamp into snapshots folder
    def snapshot(self):
        new_name = self.rename()
        if not new_name:
            return
        timestamp = datetime.datetime.now()
        time_str = timestamp.strftime('%m_%d_%y_%H%M%S')
        snapshot_name = self.name + '_' + time_str
        nx.write_gml(self.graph, self.SNAPSHOT_DIR + snapshot_name)
        print('snapshot taken!')

    def offer_snapshot(self):
        if self.nodes() and self.offer_choice(['take snapshot?']):
            self.snapshot()

    def offer_save(self):
        if self.nodes() and self.modified and \
           self.offer_choice(['session modified, save?']):
            self.save()

    def delete_save(self):
        if self.name not in self.saved_sessions(self.SAVE_DIR):
            print('session not saved')
            return
        if self.offer_choice(['delete this save?'], default=0):
            self.offer_snapshot()
            os.remove(self.SAVE_DIR + self.name)
            print('Deleted!')
            self.modified = False
            self.new_session()

    def delete_snapshot(self):
        if self.name not in self.saved_sessions(self.SNAPSHOT_DIR):
            self.print_red('snapshot aborted')
            return
        if self.offer_choice(['delete this snapshot?'], default=0):
            os.remove(self.SNAPSHOT_DIR + self.name)
            self.modified = False
            print('deleted!')

    def load(self, snapshot=False):
        self.offer_save()
        directory = self.SNAPSHOT_DIR if snapshot else self.SAVE_DIR
        self.print_bold('Load Session:')
        name = self.offer_choice(self.saved_sessions(directory))
        if name:
            self.__init__()
            self.graph = nx.read_gml(directory + name)
            self.graph = nx.to_directed(self.graph)
            self.name = name
            print('loaded!')
            return name

    def new_session(self):
        self.offer_save()
        self.__init__()
        self.print_welcome()

    # ADVANCED FEATURES
    def user_edit(self, node):
        new = self.ask_node_name('edit node to: ', node)
        if new is None or (not new.strip()):
            self.print_red('invalid')
            return
        self.edit_node(node, new)
        return new

    # allow repicking the connections of a node, return all new connections
    def user_add_connection(self, node):
        assert(node in self.nodes())
        query = input('Search New Connection: ')
        if query != '' and (not self.is_valid_node_name(query)):
            self.print_red('invalid query, aborting add connection')
            return
        options = [n for n in self.nodes() if n != node]
        options = [n for n in options if query.lower() in n.lower()]
        options = [n for n in options if n not in self.neighbors(node)]
        new_connection = self.offer_choice(options, default=0)
        if not new_connection:
            self.print_red('no new connection made')
            return
        self.print_bold('Choose Connection Type:')
        connection_type = self.offer_choice(
            ['sibling', 'child', 'parent'], default=0)
        if connection_type == 'sibling':
            self.add_sibling(node, new_connection)            
            return self.siblings(new_connection) + [new_connection]
        elif connection_type == 'child':
            self.add_child(node, new_connection)
            return new_connection
        elif connection_type == 'parent':
            self.add_child(new_connection, node)
            return new_connection
        self.print_red('invalid choice, no new connection made')

    def user_remove_connection(self, node, exclude=[]):
        assert(node in self.nodes())
        # find which nodes we can disconnect without breaking the graph
        # (by removing and checking if path remains, then put it back)
        removable = [n for n in self.neighbors(node)
                     if self.can_remove_edge(node, n) and n not in exclude]
        if removable == []:
            self.print_red('no removable connections')
            return
        self.print_bold('Pick Connection to Remove: ')
        all_string = 'Remove All Connections'
        choice = self.offer_choice([all_string] + removable, default=0)
        if not choice:
            self.print_red('no connection removed')
            return
        to_remove = []
        if choice == all_string:
            to_remove = removable
        else:
            to_remove = [choice]
        for r in to_remove:
            if r in self.children(node):
                self.remove_edge(node, r)
            if r in self.siblings(node):
                self.remove_edge(node, r)
                self.remove_edge(r, node)
            if r in self.parents(node):
                self.remove_edge(r, node)

    def user_move(self, node):
        new_connections = self.user_add_connection(node)
        self.user_remove_connection(node, new_connections)
        print('Done Moving!')

    def can_delete(self, node):
        if len(self.nodes()) <= 1:
            return False
        test_graph = nx.Graph(self.graph.copy())
        test_graph.remove_node(node)
        return nx.is_connected(test_graph)

    # delete the current node - only works if 2 or less neighbors
    def delete_node(self, node):
        if not self.can_delete(node):
            self.print_red('deleting would disconnect graph')
            return
        neighbors = self.neighbors(node)
        self.graph.remove_node(node)
        print('deleted!')
        self.modified = True
        return list(neighbors)[0] if neighbors else None

    def user_pick(self):
        return self.user_pick_tournament(self.nodes())

    def user_pick_child(self, node):
        if not self.children(node):
            self.print_red('No Children to Pick From, Aborting')
            return
        return self.user_pick_tournament(self.children(node))

    def user_pick_sibling(self, node):
        return self.user_pick_tournament(self.siblings(node) + [node])

    # asks user to choose between random pairs until all but one are eliminated
    def user_pick_tournament(self, nodes):        
        print('let\'s pick something! (tournament style)')
        remaining = set(nodes)
        least_played = set(remaining)
        while len(remaining) > 1:
            if len(least_played) <= 1:
                least_played = set(remaining)
            a, b = least_played.pop(), least_played.pop()
            choice = None
            while not choice:
                print('')
                choice = self.offer_choice([a, b], allow_rng=True)
                if not choice and self.offer_choice(['quit pick?'], default=0):
                    self.print_red('Aborted')
                    return
            remaining.remove(a)
            remaining.remove(b)
            remaining.add(choice)
        chosen = remaining.pop()
        print('Chosen: ' + str(chosen))
        return chosen

    def __str__(self):
        return self.recap()

    def loop(self):
        self.print_welcome()
        old = ''
        while True:
            # spit message and take input
            self.print_bold('(? for options): ', end='')
            self.print_green(old)
            if self.contains(old):
                self.visit(old)
            new = input().strip()
            # options info
            if new == '?':
                print('''
NAVIGATION:
    ?   - help (online docs one day?)
    _   - create new node as sibling
    >_  - create new node as child
    //_ - search for node
    RET - auto traverse
    /b  - traverse back
    /g  - draw graph
    /r  - recent nodes
    /n  - show neighbors
    /p  - pick any a node (tournament-style)
    /pc - pick a child (tournament-style)
    /ps - pick a sibling (tournament-style)

BASIC OPERATIONS:
    /e  - edit node
    /d  - delete node
    /+  - add connection
    /-  - remove connection
    /m  - move node (add, then remove connection)

SESSIONS + SNAPSHOTS:
    /s  - save session
    /l  - load session
    /x  - delete session
    /ss - save snapshot
    /ls - load snapshot
    /xs - delete snapshot
    /ln - new session
    /q  - quit
                ''')
            # special commands start with /
            elif new and new[0] == '/':
                if new == '/b':
                    result = self.traverse_back(old)
                    if result:
                        old = result
                elif new == '/n' and old:
                    self.print_with_family(old)
                elif new == '/r' and old:
                    result = self.choose_recent()
                    if result:
                        old = result
                elif new == '/g':
                    self.draw()
                elif new == '/e':
                    result = self.user_edit(old)
                    if result:
                        old = result
                elif new == '/d' and old:
                    result = self.delete_node(old)
                    if result:
                        old = result
                elif new == '/+':
                    self.user_add_connection(old)
                    # more intuitive to stay on same node?
                elif new == '/-':
                    self.user_remove_connection(old)
                elif new == '/m':
                    result = self.user_move(old)
                    if result:
                        old = result
                # SESSION COMMANDS
                elif new == '/s':
                    self.save()
                elif new == '/l':
                    if self.load():
                        old = self.auto_traverse()
                elif new == '/x':
                    self.delete_save()
                    old = ''
                elif new == '/ss':
                    self.snapshot()
                elif new == '/ls':
                    if self.load(True):
                        old = self.auto_traverse()
                elif new == '/xs':
                    self.delete_snapshot()
                elif new == '/ln':
                    self.new_session()
                    old = ''
                elif new == '/q':
                    self.offer_save()
                    return
                elif new == '/p':
                    chosen = self.user_pick()
                    if chosen:
                        old = chosen
                elif new == '/pc':
                    chosen = self.user_pick_child(old)
                    if chosen:
                        old = chosen
                elif new == '/ps':
                    chosen = self.user_pick_sibling(old)
                    if chosen:
                        old = chosen
                elif new == '/debug':
                    self.debug_print()
                else:
                    if len(new) > 1 and new[1] == '/':
                        result = self.search(new[2:])
                        if result:
                            old = result
                    else:
                        self.print_red('unrecognized command')
                        if len(new) > 1 and \
                           self.offer_choice(['did you mean to search?']):
                            result = self.search(new[2:])
                            if result:
                                old = result
            # normal input
            elif type(new) == str and new.strip() == '':
                old = self.auto_traverse(old)
            elif new and new[0] == '>':
                child = new[1:]
                if self.add_node(child, old, "child"):
                    self.print_purple("added as child!")
                    old = child
            elif new and new[0] == '<':
                parent = new[1:]
                if self.add_node(parent, old, "parent"):
                    self.print_purple("added as parent!")
                    old = parent
            elif self.is_valid_node_name(new):
                if self.add_node(new, old):
                    self.print_purple("added as sibling!")
                    old = new
            else:
                self.print_red('invalid node name, try again\n')


if __name__ == '__main__':
    # initiate session
    void = Void()
    try:
        void.loop()
    except Exception:
        void.auto_save()
        print(traceback.format_exc())
