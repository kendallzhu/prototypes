import random
import networkx as nx
import matplotlib.pyplot as plt

# dict of thought/idea/question: neighbors
class Void:
    def __init__(self):
        self.things = nx.Graph()

    def contains(self, thing):
        return thing in self.things

    # insert a new thing into the void from parent
    def add(self, thing, parent = None):            
        if thing not in self.things:
            self.things.add_node(thing)
        if parent in self.things:
            self.things.add_edge(parent, thing)

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

    def save(self, path):
        nx.write_gml(self.things, path)

    def load(self, path):
        if not self.things or input('discard unsaved changes? (y or n): ') == 'y':
            try:
                self.things = nx.read_gml(path)
            except:
                print('not found')

    def __str__(self):
        return self.recap()
    
# initiate session
void = Void()
old = 'Welcome to The Void'

while True:
    # spit message and take input
    new = input("(? for options): " + old + "\n")
    # options info
    if new == '?':
        # TODO: more navigation options? delete?
        print('''COMMANDS:
        _ - create new node _ 
        /c - condense node w/ neighbors
        /n - show neighbors
        /p - print list
        /g - draw graph
        /s - save session
        /l - load session
        /q - quit
        ''')
    # special commands start with /
    elif new and new[0] == '/':
        if new == '/p':
            print("\n-------------------------RECAP-------------------------")        
            print(void.recap() + '\n')
        elif new == '/g':
            void.draw()
        elif new == '/n':
            print(void.neighbors(old))
        elif new == '/c':
            print(void.neighbors(old))
            thing = input('condense ^ into (/c to cancel): \n')
            if thing != '/c':
                void.condense(old, thing)
            old = thing
        elif new == '/s':
            name = input('enter name: ')
            void.save(name + '.txt')
        elif new == '/l':
            name = input('enter name: ')
            void.load(name + '.txt')
        elif new == '/q':
            # warn/suggest save?
            break
        else:
            print('unrecognized command')
    # normal input
    elif new == '':
        old = void.spit(old)
    else:
        for n in new.split('/ '):
            void.add(n, old)
        old = void.spit(old)


