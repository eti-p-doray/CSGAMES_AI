from src.bot.Bot import Bot


class MyBot(Bot):

    def __init__(self):
        super().__init__()
        self.closest_ressource = (0, 0)
        self.junks = []

    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def turn(self, game_state, character_state, other_bots):
        # Your bot logic goes here
        super().turn(game_state, character_state, other_bots)
        gs_array = self.to_array(game_state)
        self.closest_ressource = self.find_closest_ressource(character_state)
        #print(str(self.closest_ressource))
        return self.commands.idle()

#(y,x)
#{'location': (7, 1), 'carrying': 0, 'health': 100, 'name': 'My bot', 'points': 0, 'spawn': 0, 'status': 'alive', 'base': (7, 1), 'id': 1}
    def find_closest_ressource(self, ch_state):
        closest = (-1,-1)
        for junk in self.junks:
            if closest is (-1,-1):
                closest = junk
            else:
                if abs(ch_state['location'][0] - closest[0]) + abs(ch_state['location'][1] -
                        closest[1]) > abs(ch_state['location'][0] - junk[0]) + abs(ch_state['location'][1] - junk[1]):
                    closest = junk
        return closest


    def to_array(self, game_state):
        array = []
        array.append([]);
        i = 0
        for c in game_state:
            if c is not '\n':
                array[i].append(c)
                if c is 'J':
                    self.junks.append((i, len(array[i])-1))
            else:
                array.append([])
                i += 1
        return array
