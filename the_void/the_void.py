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
        self.name = ""
        self.things = nx.Graph()

    # INTERACTIONS
    def contains(self, thing):
        return thing in self.things

    # insert a new thing into the void from parent
    def add(self, thing, parent = None):
        if not self.name:
            self.name = thing
        if thing not in self.things:
            self.things.add_node(thing)
        if parent in self.things:
            self.things.add_edge(parent, thing)

    # search for a node
    def search(self, thing, parent):
        results = [n for n in self.things if thing in n]
        print("choose # to go to node, + to add connection:") 
        for i, r in enumerate(results):
            print (str(i) + ') ' + r)
        if len(results) == 0:
            print('nothing found')
            return
        choice = input()
        try:
            is_connection = choice[-1] == '+'
            number = int(choice[:-1] if is_connection else choice)
            if number < len(results):
                result = results[number]
                if is_connection:
                    self.add(result, parent)
                return result
            print("invalid choice")
        except Exception as e:
            print(e)

    # return string of neighbors of node
    def neighbors(self, thing):
        if thing not in self.things:
            return ''
        return '\n'.join([str(t) for t in self.things[thing]])

    # replace current node and its neighbors with new node
    def condense(self, thing, new):
        # collect all nodes 2 away                     
        neighbors = [n for n in self.things[thing]]
        two_away = []
        for n in neighbors:
            for n2 in self.things[n]:
                if n2 != thing and n2 not in neighbors:
                    two_away.append(n2)
        # remove node and all neighbors
        self.things.remove_node(thing)
        for n in neighbors:
            self.things.remove_node(n)
        # add replacement with kept edges
        self.things.add_node(new)
        self.things.add_edges_from([(new, n) for n in two_away])

    # return random neighbor (or just random node)
    def spit(self, thing = None):
        if not self.things:
            return ''
        if thing in self.things and self.things[thing]:
            return random.choice(list(self.things[thing]))
        return random.choice(list(self.things.nodes)) # chance to random?

    # asks user to choose between until all but one are eliminated
    def user_pick_node(self):
        remaining = set(self.things.nodes)
        while len(remaining) > 1:
            a, b = remaining.pop(), remaining.pop()
            print('right now, would you rather explore (1) or (2):')
            print('(1) ' + str(a))
            print('(2) ' + str(b))
            choice = input()
            while choice not in ['1', '2', '/q']:
                choice = input('enter 1 or 2: ')
            if choice == '/q':
                return 'Aborted'
            if choice == '1':
                remaining.add(a)
            else:
                remaining.add(b)
        return remaining.pop()

    # DISPLAY
    # draw graph in new window
    def draw(self):        
        nx.draw(self.things, with_labels=True, font_weight='bold')
        plt.show()
        
    # return string of items sorted by degree
    def recap(self):
        recap = []
        for n in self.things.nodes:
            recap.append((n, list(self.things[n])))
        recap.sort(key = lambda x: -len(x[1]))
        return '\n'.join(map(lambda x: str(x), recap))

    # SESSION SAVING
    def list_sessions(self):
        for f in os.listdir(self.SAVE_DIR):
            if os.path.isfile(os.path.join(self.SAVE_DIR + f)):
                print(f)
                
    # write to file in main session folder
    def save(self, name = None):
        if name:
            self.name = name
        if not self.name:
            print('invalid name')
            return
        nx.write_gml(self.things, self.SAVE_DIR + self.name)

    # write to file with timestamp into archives folder
    def archive(self):
        timestamp = datetime.datetime.now()
        time_str =  timestamp.strftime('%m_%d_%y_%H%M%S')
        archive_name = self.name + '_' + time_str
        nx.write_gml(self.things, self.ARCHIVE_DIR + archive_name)

    def load(self, name):
        if not self.things:
            try:                
                self.things = nx.read_gml(self.SAVE_DIR + name)
                self.name = name
            except Exception as e:
                print(e)
                print('not found')

    def __str__(self):
        return self.recap()

    def loop(self):
        old = 'Welcome to the Void'
        while True:
            # spit message and take input
            new = input("(? for options): " + old + "\n")
            # options info
            if new == '?':
                # TODO: more navigation options? delete?
                print('''COMMANDS:
                _ - create new node
                /_  - search for node
                /c - condense node w/ neighbors
                /n - show neighbors
                /p - print list
                /g - draw graph
                /a - action picker
                /s - save session
                /l - load session
                /q - quit
                ''')
                # special commands start with /
            elif new and new[0] == '/':
                if new == '/p':
                    print("\n-----------------------RECAP-------------------------")        
                    print(self.recap() + '\n')
                elif new == '/g':
                    self.draw()
                elif new == '/n':
                    print(self.neighbors(old))
                elif new == '/c':
                    print(self.neighbors(old))
                    thing = input('condense ^ into (/q to cancel): \n')
                    if thing != '/q':
                        self.condense(old, thing)
                        old = thing
                elif new == '/s':
                    name = input('save name (default ' + self.name + '):')
                    self.save(name)
                elif new == '/l':
                    self.list_sessions()
                    name = input('load name: ')
                    self.load(name)
                elif new == '/a':
                    print('let\'s do something!')
                    chosen = self.user_pick_node()
                    print('Your mission is to explore: ' + str(chosen))
                    old = chosen
                elif new == '/q':
                    # auto-save for data collection
                    # self.archive()
                    return
                else:
                    result = self.search(new[1:], old)
                    if result:
                        old = result
            # normal input
            elif new == '':
                old = self.spit(old)
            else:
                void.add(new, old)
                old = self.spit(old)

if __name__ == "__main__":
    try:
        # initiate session
        void = Void()
        void.loop()
    except Exception as e:
        print(e)
        # auto-save for data collection
        void.archive()
