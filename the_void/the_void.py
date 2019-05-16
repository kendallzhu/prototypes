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

    # return neighbors of node
    def neighbors(self, thing):
        if thing not in self.things:
            return ''
        return self.things[thing]

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
        nx.write_adjlist(self.things, path)

    def load(self, path):
        if not self.things or input('discard current session? (y or n): ') == 'y':
            self.things = nx.read_adjlist(path)

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
        <RET> - random node
        /n - print neighbors
        /_ - go to node _
        /p - print full recap
        /s - save session
        /l - load session
        ''')
    # special commands start with /
    elif new and new[0] == '/':
        if new == '/p':
            print("\n-------------------------RECAP-------------------------")        
            print(void.recap() + '\n')
            void.draw()
        elif new == '/n':
            print(void.neighbors(old))
        elif new == '/s':
            name = input('enter name: ')
            void.save(name + '.txt')
        elif new == '/l':
            name = input('enter name: ')
            void.load(name + '.txt')
        elif void.contains(new[1:]):
            old = new[1:]
    # normal input
    elif new == '':
        old = void.spit(old)
    else:
        for n in new.split('/ '):
            void.add(n, old)
        old = void.spit(old)


