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
        self.junks = {}
        self.danger_zone = []
        self.gs_array = None
        self.current_turn = 0
        self.other_bots = None
        self.last_action = "idle"

        self.reward_expectation = 8
        self.risk_of_injury = 2
        self.respawn_time = 10
        self.healing_speed = 10
        self.attack_dammage = 10
        self.enemy_distance_to_flee = 4
        self.capacity = 150


    def get_name(self):
        # Find a name for your bot
        return 'My bot'

    def best_path(self, start, goal):
        players_pos = {}
        for player in self.other_bots:
          players_pos[player['location']] = True

        def can_pass_through(node):
            symbol = self.gs_array[node[0]][node[1]]
            return (symbol == '0' or symbol == 'S' or symbol == 'J') and not (node in players_pos)

        def symbol_weight(node):
            symbol = self.gs_array[node[0]][node[1]]
            if symbol == 'S':
                return 10 / self.risk_of_injury
            return 1

        q = queue.PriorityQueue()
        q.put((0, start, None))
        visited = {}
        node = None
        while not q.empty():
            priority, node, previous = q.get()
            if node in visited:
                continue
            visited[node] = previous
            if node == goal:
                break

            directions = []
            if node[0] >= 0:
                directions.append((-1, 0))
            if node[1] >= 0:
                directions.append((0, -1))
            if node[0] < len(self.gs_array):
                directions.append((1, 0))
            if node[1] < len(self.gs_array[node[0]]):
                directions.append((0, 1))

            for direction in directions:
                next_node = (node[0] + direction[0], node[1] + direction[1])
                if next_node in visited:
                    continue
                if can_pass_through(next_node) or next_node == goal:
                    next_priority = priority + symbol_weight(next_node)
                    q.put((next_priority, next_node, node))

        if node is None or node != goal:
            return None
        path = []
        while node is not None:
            path.append(node)
            previous_node = visited[node]
            node = previous_node

        return list(reversed(path))

    @staticmethod
    def convert_node_to_direction(path):
        if path is None or len(path) < 2:
            return None

        start = path[0]
        next = path[1]
        if start[1] == next[1] + 1:
            return 'W'
        elif start[1] == next[1] - 1:
            return 'E'
        elif start[0] == next[0] + 1:
            return 'N'
        else:
            return 'S'

    def should_return_to_base(self, turn, character_health, character_carrying, distance_to_base, character_position):
        if 1000 - turn <= distance_to_base + 1:
          return True
        """if character_health == 0:
            return True
        risk_of_dying = self.risk_of_injury / character_health * distance_to_base

        # risk in reward loss
        total_risk = (self.reward_expectation * self.respawn_time + character_carrying) * risk_of_dying

        # cost of going back to base
        loss = (distance_to_base * self.reward_expectation + 1 +
                (100 - character_health) / self.healing_speed)
        #print(total_risk, loss)
        return total_risk > loss"""
        return character_carrying > self.capacity


    def neighbor(self, ch_pos, other):
        dx = abs(ch_pos[0] - other[0])
        dy = abs(ch_pos[1] - other[1])
        return (dx == 0 and dy == 1 or dx == 1 and dy == 0)

    def turn(self, game_state, character_state, other_bots):
        self.log_last_gain(character_state)
        self.last_ressources = character_state['carrying']
        self.other_bots = other_bots
        self.current_turn += 1
        super().turn(game_state, character_state, other_bots)
        if not self.gs_array:
            self.gs_array = self.to_array(game_state)

        if character_state['location'] == character_state['base']:
            if character_state['carrying'] != 0:
                self.last_action = "store"
                return self.commands.store()
            if character_state['health'] != 100:
                self.last_action = "rest"
                return self.commands.rest()

        path_to_base = self.best_path(character_state['location'], character_state['base'])
        if self.should_return_to_base(self.current_turn, character_state['health'], character_state['carrying'], len(path_to_base), character_state['location']):
            print("Return to base")
            direction = self.convert_node_to_direction(path_to_base)
            self.last_action = "move"
            return self.commands.move(direction)

        ressource = self.find_best_ressource(character_state)

        for opponent in other_bots:
            reward = self.attack_opponent_reward(character_state, opponent)
            if reward is not None and reward > ressource['reward']:
                direction = self.convert_node_to_direction([character_state['location'], opponent['location']])
                self.last_action = "attack"
                return self.commands.attack(direction)

        print("Farming")
        if character_state['location'] == ressource['pos']:
            self.last_action = "collect"
            return self.commands.collect()
        else:
            path = self.best_path(character_state['location'], ressource['pos'])
            direction = self.convert_node_to_direction(path)
            self.last_action = "move"
            return self.commands.move(direction)

        self.last_action = "idle"
        return self.commands.idle()

    def log_last_gain(self, character_state):
        if "collect" != self.last_action:
            return
        self.junks[character_state['location']].add_observation(character_state['carrying'] - self.last_ressources)

    def attack_opponent_reward(self, ch_state, victim):
        if not self.neighbor(ch_state['location'], victim['location']):
            return None
        if victim['health'] > ch_state['health']:
            return None
        fight_duration = victim['health'] / self.attack_dammage
        reward = victim['carrying'] / fight_duration
        return reward

#(y,x)
#{'location': (7, 1), 'carrying': 0, 'health': 100, 'name': 'My bot', 'points': 0, 'spawn': 0, 'status': 'alive', 'base': (7, 1), 'id': 1}
    def find_best_ressource(self, ch_state):
        best = {"pos":(-1,-1), "reward":0}

        for pos, ml in self.junks.items():
            reward = self.junk_reward(ch_state, pos, ml.params()[0])
            if best["pos"] == (-1,-1) or reward > best["reward"]:
                if not self.is_tile_occupied(pos):
                    best["pos"] = pos
                    best["reward"] = reward

        return best

    def is_tile_occupied(self, tile_position):
        for player in self.other_bots:
            if player["location"] == tile_position:
                return True
        return False

    def junk_reward(self, ch_state, junk_position, junk_average):
        path_to_junk = self.best_path(ch_state['location'], junk_position)
        if path_to_junk is None:
          return 0
        nb_tours = len(path_to_junk)
        #TODO prendre en compte les tiles qu'on sait qu'on va se blesser en y allant
        current_sim_health = ch_state['health'] - nb_tours * self.risk_of_injury
        current_sim_gain = 0
        current_sim_turn = self.current_turn + nb_tours
        path_to_base = self.best_path(junk_position, ch_state['base'])
        if path_to_base is None:
          return 0
        distance_to_base = len(path_to_base)
        current_sim_gain += self.capacity
        nb_tours += self.capacity / junk_average
        nb_tours +=  distance_to_base + 1
        return current_sim_gain / nb_tours

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
        path = self.best_path(character_position, self.other_bots[0]['location'])
        if path is None:
          return 1000000
        min = len(path)
        for i in range(1, len(self.other_bots)):
            dist = self.distance_between_two_points(character_position, self.other_bots[i]['location'])
            if dist < min:
                min = dist
        return min
