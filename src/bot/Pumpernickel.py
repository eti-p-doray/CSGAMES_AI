from src.bot.Bot import Bot

import math
import queue
import itertools

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


class PlayerEavesdrop:
    def __init__(self):
        self.previous_ressources = 0

    def update(self, player):
        if player['carrying'] > self.previous_ressources:
            last_reward = player['carrying'] - self.previous_ressources
            self.previous_ressources = player['carrying']
            return last_reward
        self.previous_ressources = player['carrying']
        return None


class Pumpernickel(Bot):

    def __init__(self):
        super().__init__()
        self.junks = {}
        self.danger_zone = []
        self.gs_array = None
        self.current_turn = 0
        self.player_eavesdrops = {}

        self.respawn_time = 10
        self.healing_speed = 10
        self.attack_dammage = 10

        # Adjustable
        self.capacity = 1000
        self.average_reward = 4
        self.risk_of_injury = 4
        self.risk_health = 11


    def get_name(self):
        # Find a name for your bot
        # Mayer, Charlotte (2015). Types of Bread to Name Your Child After. Found at
        # http://reductress.com/post/types-of-bread-to-name-your-child-after/
        return 'Pumpernickel'

    def best_path(self, character_health, character_carrying, start, goal):
        def can_pass_through(node):
            symbol = self.gs_array[node[0]][node[1]]
            return (symbol == '0' or symbol == 'S' or symbol == 'J')

        def symbol_weight(current_ch_health, node):
            weight = 0
            if node in self.players_by_pos:
                fight_duration = self.players_by_pos[node]['health'] / self.attack_dammage
                weight += fight_duration
                if character_health < self.players_by_pos[node]['health']:
                    weight += self.respawn_time + character_carrying / self.average_reward
            symbol = self.gs_array[node[0]][node[1]]
            if symbol == 'S' and current_ch_health > 0:
                weight += 100 / current_ch_health
            return 1 + weight

        q = queue.PriorityQueue()
        q.put((0, start, None, character_health))
        visited = {}
        node = None
        while not q.empty():
            priority, node, previous, current_ch_health = q.get()
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
                    next_priority = priority + symbol_weight(current_ch_health, next_node)
                    next_ch_health = current_ch_health
                    if self.gs_array[next_node[0]][next_node[1]] == 'S':
                        next_ch_health -= 10
                    q.put((next_priority, next_node, node, next_ch_health))

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
        return character_carrying > self.capacity or character_health < self.risk_health


    def neighbor(self, ch_pos, other):
        dx = abs(ch_pos[0] - other[0])
        dy = abs(ch_pos[1] - other[1])
        return (dx == 0 and dy == 1 or dx == 1 and dy == 0)

    def turn(self, game_state, character_state, other_bots):
        super().turn(game_state, character_state, other_bots)

        self.players_by_pos = {}
        for player in self.other_bots:
          self.players_by_pos[player['location']] = player

        self.current_turn += 1
        if not self.gs_array:
            self.gs_array = self.to_array(game_state)
            self.risk_health += min(10 * len(other_bots), 41)
            for player in itertools.chain([character_state], other_bots):
                self.player_eavesdrops[player['id']] = PlayerEavesdrop()

        for player in itertools.chain([character_state], other_bots):
            reward = self.player_eavesdrops[player['id']].update(player)
            if reward is not None and player['location'] in self.junks:
                self.junks[player['location']].add_observation(reward)

        if character_state['location'] == character_state['base']:
            if character_state['carrying'] != 0:
                return self.commands.store()
            if character_state['health'] != 100:
                return self.commands.rest()

        path_to_base = self.best_path(character_state['health'], character_state['carrying'], character_state['location'], character_state['base'])
        if self.should_return_to_base(self.current_turn, character_state['health'], character_state['carrying'], len(path_to_base), character_state['location']):
            print("Return to base")
            direction = self.convert_node_to_direction(path_to_base)
            return self.commands.move(direction)

        ressource = self.find_best_ressource(character_state)

        for opponent in other_bots:
            reward = self.attack_opponent_reward(character_state, opponent)
            if reward is not None and reward > ressource['reward']:
                print("Attacking")
                direction = self.convert_node_to_direction([character_state['location'], opponent['location']])
                return self.commands.attack(direction)

        print("Farming")
        if character_state['location'] == ressource['pos']:
            return self.commands.collect()
        else:
            path = self.best_path(character_state['health'], character_state['carrying'], character_state['location'], ressource['pos'])
            direction = self.convert_node_to_direction(path)
            if path[1] in self.players_by_pos:
                return self.commands.attack(direction)
            return self.commands.move(direction)

        return self.commands.idle()

    def attack_opponent_reward(self, ch_state, victim):
        if not self.neighbor(ch_state['location'], victim['location']):
            return None
        fight_duration = victim['health'] / self.attack_dammage
        reward = victim['carrying'] / fight_duration
        return reward

    def find_best_ressource(self, ch_state):
        best = {"pos":(-1,-1), "reward":0}

        for pos, ml in self.junks.items():
            reward = self.junk_reward(ch_state, pos, ml.params()[0])
            if best["pos"] == (-1,-1) or (reward > best["reward"]):
                if not self.is_tile_occupied(pos, ch_state):
                    best["pos"] = pos
                    best["reward"] = reward

        if best["pos"] == (-1, -1):
            for pos, ml in self.junks.items():
                reward = self.junk_reward(ch_state, pos, ml.params()[0])
                if best["pos"] == (-1,-1) or (reward > best["reward"]):
                    best["pos"] = pos
                    best["reward"] = reward

        return best

    def is_tile_occupied(self, tile_position, ch_state):
        for player in self.other_bots:
            if (player["location"] == tile_position and
               player["health"] + self.risk_health >= ch_state["health"]):
                return True
        return False

    def junk_reward(self, ch_state, junk_position, junk_average):
        path_to_junk = self.best_path(ch_state['health'], ch_state['carrying'], ch_state['location'], junk_position)
        if path_to_junk is None:
          return 0
        nb_tours = len(path_to_junk)
        #TODO prendre en compte les tiles qu'on sait qu'on va se blesser en y allant
        current_sim_gain = 0
        current_sim_turn = self.current_turn + nb_tours
        current_sim_gain += self.capacity
        nb_tours += self.capacity / junk_average
        current_sim_health = ch_state['health'] - nb_tours * self.risk_of_injury
        path_to_base = self.best_path(current_sim_health, current_sim_gain + ch_state['carrying'], junk_position, ch_state['base'])
        if path_to_base is None:
          return 0
        distance_to_base = len(path_to_base)
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
