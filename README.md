# prototypes

The Void - minimalist command line mind-mapping tool. Designed for brainstorming, note-taking and todos.
- To install dependencies, run ```pip install -r requirements.txt```
- To run the void, cd into the_void and type: ```python the_void.py```
- Recommended usage: type things and press Enter to cycle through
  - By default things get connected as siblings, use > to create a child in its own group
- Graph structure created as you go, which you can view with /g (type ? for all commands)
- Save, load, snapshot and create new sessions (/s, /l, /ss, /ln)
- Features include search, smart navigation, node editing and rearrangement, condensing node w/ neighbors, and connecting nodes
- Interactive commands guide the user through a process:
  - /pick - Tournament-style bracket to pick a node (useful for todos!)
