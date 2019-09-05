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
        self.graph = nx.Graph()
        # for traversal heuristic
        self.weighted_visits = Counter()
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

    def neighbors(self, node):
        return sorted(list(self.graph[node]), key=lambda n: -self.degree(n))

    def degree(self, node):
        return len(self.graph[node])

    def remove_node_and_edges(self, node):
        self.modified = True
        self.graph.remove_node(node)

    def nodes(self):
        return sorted(list(self.graph), key=lambda n: -self.degree(n))

    # insert a new node into the void from parent
    def add(self, node, parent=None):
        if type(node) != str:
            self.print_red('Can only add strings as nodes!')
            return
        if not self.is_valid_node_name(node):
            self.print_red('Invalid node name')
            return
        if node in self.nodes():
            self.print_red('Node name already in graph')
            return
        self.modified = True
        if not self.name:
            self.name = node
        if not self.contains(node):
            self.graph.add_node(node)
            self.set_time_created(node)
        if parent and parent not in self.neighbors(node):
            self.graph.add_edge(parent, node)

    def add_edge(self, n1, n2):
        self.modified = True
        self.graph.add_edge(n1, n2)

    def remove_edge(self, n1, n2):
        if self.degree(n1) == 1 or self.degree(n2) == 1:
            self.print_red('removing edge would orphan node, aborting')
            return
        self.graph.remove_edge(n1, n2)
        if not nx.has_path(self.graph, n1, n2):
            self.print_red('removing edge would disconnect graph, aborting')
            self.graph.add_edge(n1, n2)
            return
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
        neighbors = graph[node]
        graph.remove_node(node)
        graph.add_node(new)
        for n in neighbors:
            graph.add_edge(new, n)

    def edit_node(self, node, new):
        self.modified = True
        Void.edit_networkX_node(self.graph, node, new)

    def is_valid_node_name(self, name):
        return name and name[0] != '/'

    def get_recent(self, number):
        nodes_by_time = sorted(self.nodes(), key=self.get_time_created)
        nodes_by_time.reverse()
        num_return = min(number, len(nodes_by_time))
        return nodes_by_time[0:num_return]

    def debug_print(self):
        print(self.graph.nodes.data())

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

    def print_with_neighbors(self, node):
        self.print_bold("\nneighbors - [# connections]:")
        for neighbor in self.neighbors(node):
            s = neighbor + ' [' + str(self.degree(neighbor) - 1) + ']'
            print(s)
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
        if not (type(default) == int and default < len(options)):
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
        if default:
            prompt = 'choose # or search (default - {}):'.format(default)
        else:
            prompt = 'choose # or search:'
        self.print_bold(prompt)
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

    def choose_neighbor(self, node):
        if not self.contains(node):
            return ''
        neighbors = self.neighbors(node)
        self.print_bold('Choose Neighbor:')
        return self.offer_choice(neighbors)

    def choose_recent(self):
        print('Recently Changed:')
        recents = self.get_recent(5)
        return self.offer_choice(recents)

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
        options.sort(key=lambda n: (-self.degree(n), len(n)))
        return options[0]

    # return neighbor based on least visited (weighted)
    def auto_traverse(self, node=None):
        if self.is_empty():
            return ''
        if not self.contains(node) or not self.neighbors(node):
            # TODO: should visit here or nah?
            return self.primary_node()
        options = self.neighbors(node)
        # choose by weighted_visits heuristic, then by less neighbors first
        options.sort(key=lambda n: (self.weighted_visits[n], self.degree(n)))
        choice = options[0]
        self.visit(choice)
        return choice

    # to nodes with more neighbors and more visited (likely where we came from)
    def traverse_back(self, node):
        if self.is_empty() or not self.visit_history or \
           not self.contains(node):
            return ''
        if node == self.visit_history[-1]:
            self.visit_history.pop()
        return self.visit_history.pop()

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
            for node in [n for n in pretty_version.nodes()]:
                text = format_node_text(node)
                Void.edit_networkX_node(pretty_version, node, text)
            nx.draw_kamada_kawai(
                pretty_version,
                with_labels=True,
                font_weight='bold',
                node_color='#00a400',
                # node_color='#ff6200'
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
        if not new_name:
            return
        nx.write_gml(self.graph, self.SAVE_DIR + self.name)
        self.modified = False
        print('saved!')

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
            self.name = name
            print('loaded!')

    def new_session(self):
        self.offer_save()
        self.__init__()
        self.print_welcome()

    # ADVANCED FEATURES
    # add completely new node and connect as many others to it as desired
    def add_new(self):
        new = self.ask_node_name('new node: ')
        if not new:
            self.print_red('aborting add new')
            return
        num_added = 0
        while True:
            query = self.ask_node_name('Find New Connection:')
            if not query:
                if num_added > 0:
                    break
                else:
                    query = ''
            new_connection = self.search(query)
            if self.is_valid_node_name(new_connection):
                self.add(new_connection, new)
                num_added += 1
            elif num_added > 0:
                break
        print('done adding connections!\n')
        return new

    # relabel the current node
    def edit(self, node):
        new = self.ask_node_name('edit node to: ', node)
        if new is None or (not new.strip()):
            self.print_red('invalid')
            return
        self.edit_node(node, new)
        return new

    # allow repicking the connections of a node
    def move(self, node):
        assert(node in self.nodes())
        while True:
            query = self.ask_node_name('New Connection (? - search any): ')
            if not query:
                break
            new_connection = self.search('' if query == '?' else query)
            if not self.is_valid_node_name(new_connection):
                break
            self.add(new_connection, node)
        print('done adding connections!\n')
        while self.degree(node) > 1:
            self.print_bold('Remove Existing Connection?')
            to_remove = self.offer_choice(self.neighbors(node))
            if not to_remove:
                break
            self.remove_edge(node, to_remove)
        if (self.degree(node) <= 1):
            print('only one connection left, cannot remove')
        print('Done Moving!')

    def can_delete(self, node):
        neighbors = self.neighbors(node)
        disconnected = False
        # remove node, check if disconnected, then put everything back
        self.graph.remove_node(node)
        for n1 in neighbors:
            for n2 in neighbors:
                if not nx.has_path(self.graph, n1, n2):
                    disconnected = True
        self.graph.add_node(node)
        for n in neighbors:
            self.graph.add_edge(node, n)
        for n in self.neighbors(node):
            if self.degree(n) == 1:
                assert(disconnected)
        return not disconnected

    # delete the current node - only works if 2 or less neighbors
    def delete_node(self, node):
        if not self.can_delete(node):
            self.print_red('deleting would disconnect graph (can try condense)')
            return
        neighbors = self.graph[node]
        self.graph.remove_node(node)
        for n1 in neighbors:
            for n2 in neighbors:
                if n1 != n2:
                    self.graph.add_edge(n1, n2)
        print('deleted!')
        self.modified = True
        return list(neighbors)[0] if neighbors else None

    # replace current node and its neighbors with new node
    def condense(self, node):
        neighbors = self.neighbors(node)
        for n in neighbors:
            print(n)
        self.print_green(node)
        new = self.ask_node_name('[condense all ^ into]: ', default=node)
        if not new:
            self.print_red('did not condense')
            return
        # collect all nodes 2 away
        neighbors = self.neighbors(node)
        two_away = []
        for n in neighbors:
            for n2 in self.neighbors(n):
                if n2 != node and n2 not in neighbors:
                    two_away.append(n2)
        # remove node and all neighbors
        self.graph.remove_node(node)
        for n in neighbors:
            self.graph.remove_node(n)
        # add replacement with kept edges
        self.add(new)
        for n in two_away:
            self.add_edge(new, n)
        self.modified = True
        return new

    # offer comprehensive review + refactor of graph
    def refactor(self):
        self.offer_snapshot()
        print('\nRefactor!\n')
        print('Step 1: Add New Nodes')
        while True:
            new = self.add_new()
            if not new:
                print('Done Adding New Nodes!')
                break
        print('\nStep 2: Refactor Each Node\n')
        # go from least degree first, to give chances to move leaves
        for n in reversed(self.nodes()):
            if not self.contains(n):
                continue
            while True:
                self.print_with_neighbors(n)
                self.print_bold('\nActions:')
                action = self.offer_choice([
                    'add children',
                    'edit',
                    'delete',
                    'move',
                    'condense',
                    'abort refactor'
                ])
                if action is None:
                    print('Done with Node!')
                    break
                elif action == 'edit':
                    n = self.edit(n)
                elif action == 'delete':
                    if self.can_delete(n):
                        self.remove_node_and_edges(n)
                        break
                    else:
                        self.print_red('can\'t delete, try move instead?')
                elif action == 'move':
                    self.move(n)
                elif action == 'add children':
                    while True:
                        child = self.ask_node_name('new child?: ')
                        if not child:
                            print('Done adding children!')
                            break
                        self.add(child, n)
                elif action == 'condense':
                    n = self.condense(n)
                elif action == 'abort refactor':
                    self.print_red('Refactor aborted!')
                    return
        print('Done Refactoring!')

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

    # asks user to choose between neighbors from current node outward (faster)
    def pick_branching(self, start_node=None):
        if start_node is None:
            start_node = self.primary_node()
        print('let\'s pick something! (quick branching style)')
        eliminated = set([])
        options = self.neighbors(start_node) + [start_node]
        choice = None
        while len(options) > 1:
            choice = None
            while not choice:
                choice = self.offer_choice(options, allow_rng=True)
                if not choice and self.offer_choice(['quit picking?']):
                    self.print_red('Aborted')
                    return
            eliminated.update(options)
            next_batch = self.neighbors(choice) + [choice]
            options = [n for n in next_batch if n not in eliminated]
        print('Chosen: ' + str(choice))
        return choice

    def __str__(self):
        return self.recap()

    def loop(self):
        self.print_welcome()
        old = ''
        while True:
            # spit message and take input
            self.print_bold('(? for options): ', end='')
            self.print_green(old)
            new = input().strip()
            # options info
            if new == '?':
                print('''
BASIC COMMANDS:
    ?   - help (online docs one day?)
    _   - create new node as child
    //_ - search for node
    RET - auto traverse (less visited neighbor)
    /b  - traverse back
    /g  - draw graph
    /r  - recent nodes
    /n  - choose neighbor
    /a  - add new node (fresh, not child)
    /e  - edit node
    /d  - delete node
    /m  - move node (add/remove connections)
    /c  - condense node w/ neighbors

SESSIONS + SNAPSHOTS:
    /s  - save session
    /l  - load session
    /x  - delete session
    /ss - save snapshot
    /ls - load snapshot
    /xs - delete snapshot
    /ln - new session
    /q  - quit

INTERACTIVE PROCESSES:
    /pick     - pick a node (tournament)
    /pick!    - pick a node (branch-from-current)
    /refactor - review + refactor entire graph
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
                elif new == '/r' and old:
                    result = self.choose_recent()
                    if result:
                        old = result
                elif new == '/g':
                    self.draw()
                elif new == '/a':
                    result = self.add_new()
                    if result:
                        old = result
                elif new == '/e':
                    result = self.edit(old)
                    if result:
                        old = result
                elif new == '/d' and old:
                    result = self.delete_node(old)
                    if result:
                        old = result
                elif new == '/m':
                    result = self.move(old)
                    if result:
                        old = result
                elif new == '/c' and old:
                    result = self.condense(old)
                    if result:
                        old = result
                elif new == '/s':
                    self.save()
                elif new == '/l':
                    self.load()
                    old = self.auto_traverse()
                elif new == '/x':
                    self.delete_save()
                    old = ''
                elif new == '/ss':
                    self.snapshot()
                elif new == '/ls':
                    self.load(True)
                    old = self.auto_traverse()
                elif new == '/xs':
                    self.delete_snapshot()
                elif new == '/ln':
                    self.new_session()
                    old = ''
                elif new == '/q':
                    self.offer_save()
                    return
                elif new == '/pick':
                    chosen = self.pick_tournament()
                    if chosen:
                        old = chosen
                elif new == '/pick!':
                    chosen = self.pick_branching(old)
                    if chosen:
                        old = chosen
                elif new == '/refactor':
                    self.refactor()
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
            elif self.is_valid_node_name(new):
                self.add(new, old)
                # automatically go to new thing when creating
                old = new
            else:
                self.print_red('invalid node name, try again\n')


if __name__ == '__main__':
    try:
        # initiate session
        void = Void()
        void.loop()
    except Exception:
        print(traceback.format_exc())
