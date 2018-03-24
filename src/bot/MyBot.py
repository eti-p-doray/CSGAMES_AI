from src.bot.Bot import Bot


class MyBot(Bot):

    def __init__(self):
        super().__init__()
        self.next_ressource = (0, 0)

    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def turn(self, game_state, character_state, other_bots):
        # Your bot logic goes here
        super().turn(game_state, character_state, other_bots)
        gs_array = self.to_array(game_state)
        self.next_ressource = self.find_next_ressource(gs_array)
        return self.commands.idle()

    def find_next_ressource(self, gs_array):
        print(gs_array)




    def to_array(self, game_state):
        array = []
        array.append([]);
        i = 0
        for c in game_state:
            if c is not '\n':
                array[i].append(c)
            else:
                array.append([])
                i += 1
        return array
