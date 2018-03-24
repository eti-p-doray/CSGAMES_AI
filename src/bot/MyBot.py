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
        self.best_ressource = (0, 0)
        self.junks = {}
        self.danger_zone = []
        self.gs_array = None
        self.current_turn = 0
        self.other_bots = None

        self.reward_expectation = 1
        self.risk_of_injury = 0.02
        self.respawn_time = 10
        self.healing_speed = 10
        self.attack_dammage = 10
        self.enemy_distance_to_flee = 4


    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def should_return_to_base(self, turn, character_health, character_carrying, distance_to_base, character_position):
        if 1000 - turn <= distance_to_base + 1:
          return True
        risk_of_dying = self.risk_of_injury / character_health * distance_to_base

        # risk in reward loss
        total_risk = (self.reward_expectation * self.respawn_time + character_carrying) * risk_of_dying

        # cost of going back to base
        loss = (distance_to_base * self.reward_expectation + 1 +
                (100 - character_health) / self.healing_speed)
        if total_risk > loss:
            return distance_to_closest_enemy(character_position) <= self.enemy_distance_to_flee
        return False

    def attack_opponent_utility(self,
            character_health, character_carrying,
            opponent_health, opponent_carrying,
            distance_to_opponent):
        if character_health <= opponent_health:
            return 0
        loss = distance_to_opponent + opponent_health / self.attack_dammage
        reward = opponent_carrying
        return reward - loss * self.reward_expectation

    def turn(self, game_state, character_state, other_bots):
        self.other_bots = other_bots
        self.current_turn += 1
        super().turn(game_state, character_state, other_bots)
        if not self.gs_array:
            self.gs_array = self.to_array(game_state)

        if character_state['location'] == character_state['base']:
            if character_state['carrying'] != 0:
                return self.commands.store()
            if character_state['health'] != 100:
                return self.commands.rest()

        self.best_ressource = self.find_best_ressource(character_state)

        # if low on health + high on ressource, go to base

        # if low on ressource + high on health, go to ressource
          # find ressource that maximize utility
            # material:
            # oponent

        #print(str(self.best_ressource))
        direction = self.pathfinder.get_next_direction(self.character_state['location'], self.best_ressource)
        if direction:
            return self.commands.move(direction)
        else:
            return self.commands.idle()


#(y,x)
#{'location': (7, 1), 'carrying': 0, 'health': 100, 'name': 'My bot', 'points': 0, 'spawn': 0, 'status': 'alive', 'base': (7, 1), 'id': 1}
    def find_best_ressource(self, ch_state):
        best = {"pos":(-1,-1), "reward":0}

        for pos, ml in self.junks.items():
            if best["pos"] is (-1,-1):
                best["pos"] = pos
                best["reward"] = self.find_reward_per_junk(ch_state, pos, ml.params()[0])
            else:
                reward = self.find_reward_per_junk(ch_state, pos, ml.params()[0])
                if reward > best["reward"]:
                    best["pos"] = pos
                    best["reward"] = reward
        return best["pos"]

    def find_reward_per_junk(self, ch_state, junk_position, junk_average):
        nb_tours = self.distance_between_two_points(ch_state['location'], junk_position)
        #TODO prendre en compte les tiles qu'on sait qu'on va se blesser en y allant
        current_sim_health = ch_state['health'] - nb_tours * self.risk_of_injury
        current_sim_gain = 0
        current_sim_turn = self.current_turn + nb_tours
        distance_to_base = self.distance_between_two_points(junk_position, ch_state['base'])
        while not self.should_return_to_base(current_sim_turn, current_sim_health, current_sim_gain + ch_state['carrying'], distance_to_base, junk_position):
            current_sim_gain += junk_average
            nb_tours += 1
            current_sim_turn += 1
            current_sim_health -= self.risk_of_injury
        nb_tours +=  distance_to_base + 1
        return current_sim_gain / nb_tours

    def distance_between_two_points(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

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

    def distance_to_closest_enemy(self, character_position):
        min = distance_between_two_points(character_position, self.other_bots[0]['location'])
        for i in range(1, len(self.other_bots)):
            dist = distance_between_two_points(character_position, self.other_bots[i]['location'])
            if dist < min:
                min = dist
        return min
