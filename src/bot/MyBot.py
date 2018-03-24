from src.bot.Bot import Bot

import math

class JunkMLEstimation:
    def __init__(self):
        self.param_score = {}
        for mean in range(5, 20):
            for std in range(1, 10):
                self.param_score[mean, std] = 0
        self.best_param = (12, 5)

    def add_observation(self, observation):
        sum_score = 0
        for (mean, std), param_score in self.param_score.items():
            self.param_score[mean, std] += self.log_likelihood(observation, mean, std)
            sum_score += self.param_score[mean, std]
        for (mean, std), param_score in self.param_score.items():
            self.param_score[mean, std] -= sum_score
            if self.param_score[mean, std] > self.param_score[self.best_param]:
                self.best_param = (mean, std)

    def params(self):
        return self.best_param


    def log_likelihood(self, observation, mean, std):
        variance = std**2
        return (-((observation - mean)**2) / variance -
              math.log(variance * math.sqrt(2*math.pi)))


class MyBot(Bot):

    def __init__(self):
        super().__init__()
        self.closest_ressource = (0, 0)
        self.junks = []
        self.danger_zone = []
        self.gs_array = None

    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def turn(self, game_state, character_state, other_bots):
        # Your bot logic goes here
        super().turn(game_state, character_state, other_bots)
        if not self.gs_array:
            self.gs_array = self.to_array(game_state)

        self.closest_ressource = self.find_closest_ressource(character_state)
        #print(str(self.closest_ressource))
        direction = self.pathfinder.get_next_direction(self.character_state['location'], self.closest_ressource)
        if direction:
            return self.commands.move(direction)
        else:
            return self.commands.idle()


#(y,x)
#{'location': (7, 1), 'carrying': 0, 'health': 100, 'name': 'My bot', 'points': 0, 'spawn': 0, 'status': 'alive', 'base': (7, 1), 'id': 1}
    def find_closest_ressource(self, ch_state):
        closest = (-1,-1)
        for pos, ml in self.junks.items():
            if closest is (-1,-1):
                closest = pos
            else:
                if abs(ch_state['location'][0] - closest[0]) + abs(ch_state['location'][1] -
                        closest[1]) > abs(ch_state['location'][0] - pos[0]) + abs(ch_state['location'][1] - pos[1]):
                    closest = pos
        return closest


    def to_array(self, game_state):
        array = []
        array.append([]);
        i = 0
        for c in game_state:
            if c is not '\n':
                array[i].append(c)
                if c is 'J':
                    self.junks[i, len(array[i])-1] = JunkMLEstimation()
                if c is 'S':
                    self.danger_zone.append((i, len(array[i])-1))
            else:
                array.append([])
                i += 1
        return array
