from src.bot.Bot import Bot

import math
import queue

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
        self.junks = {}
        self.gs_array = None

        self.reward_expectation = 1
        self.risk_of_injury = 0.02
        self.respawn_time = 10
        self.healing_speed = 10

    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def should_return_to_base(self, turn, character_health, character_carrying, distance_to_base):
        if 1000 - turn <= distance_to_base + 1:
          return True
        risk_of_dying = risk_of_injury / character_health * distance_to_base

        # risk in reward loss
        total_risk = (self.reward_expectation * self.respawn_time + character_carrying) * risk_of_dying

        # cost of going back to base
        loss = (distance_to_base * self.reward_expectation + 1 +
                (100 - character_health) / self.healing_speed)
        return total_risk > loss

    def turn(self, game_state, character_state, other_bots):
        # Your bot logic goes here
        super().turn(game_state, character_state, other_bots)
        if not self.gs_array:
            self.gs_array = self.to_array(game_state)

        self.closest_ressource = self.find_closest_ressource(character_state)

        # if low on health + high on ressource, go to base

        # if low on ressource + high on health, go to ressource
          # find ressource that maximize utility
            # material:
            # oponent

        #print(str(self.closest_ressource))
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
            else:
                array.append([])
                i += 1
        return array
