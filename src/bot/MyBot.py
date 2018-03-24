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

        self.reward_expectation = 8
        self.risk_of_injury = 2
        self.respawn_time = 10
        self.healing_speed = 10
        self.attack_dammage = 10
        self.enemy_distance_to_flee = 4


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

    def path_distance(self, start, goal):
        path = self.best_path(start, goal)
        return len(path)

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

    def should_return_to_base(self, turn, character_health, character_carrying, distance_to_base):
        if 1000 - turn <= distance_to_base + 1:
          return True
        risk_of_dying = self.risk_of_injury / character_health * distance_to_base

        # risk in reward loss
        total_risk = (self.reward_expectation * self.respawn_time + character_carrying) * risk_of_dying

        # cost of going back to base
        loss = (distance_to_base * self.reward_expectation + 1 +
                (100 - character_health) / self.healing_speed)
        #print(total_risk, loss)
        return total_risk > loss

    # To check, might fuck things up because it is coming back with health lower than 0 or something
    def should_presently_return_to_base(self, turn, character_health, character_carrying, distance_to_base, character_position):
        if 1000 - turn <= distance_to_base + 1:
          return True
        risk_of_dying = self.risk_of_injury / character_health * distance_to_base

        # risk in reward loss
        total_risk = (self.reward_expectation * self.respawn_time + character_carrying) * risk_of_dying

        # cost of going back to base
        loss = (distance_to_base * self.reward_expectation + 1 +
                (100 - character_health) / self.healing_speed)
        if total_risk > loss:
            return self.distance_to_closest_enemy(character_position) <= self.enemy_distance_to_flee
        return False

    def attack_opponent_reward(self, ch_state, opponent):
        if ch_state['health'] <= opponent['health']:
            return 0
        path_to_opponent = self.best_path(ch_state['location'], opponent['location'])
        distance_to_opponent = len(path_to_opponent)
        fight_duration = opponent_health / self.attack_dammage
        loss = distance_to_opponent + fight_duration + opponent_health / self.risk_of_injury
        reward = opponent_carrying
        return 0#reward - loss * self.reward_expectation


    def neighbor(self, ch_pos, other):
        dx = abs(ch_pos[0] - other[0])
        dy = abs(ch_pos[1] - other[1])
        return (dx == 0 and dy == 1 or dx == 1 and dy == 0)

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

        path_to_base = self.best_path(character_state['location'], character_state['base'])
        if self.should_presently_return_to_base(self.current_turn, character_state['health'], character_state['carrying'], len(path_to_base), character_state['location']):
            print("Return to base")
            direction = self.convert_node_to_direction(path_to_base)
            return self.commands.move(direction)

        ressource = self.find_best_ressource(character_state)
        victim = self.find_best_victim(character_state, other_bots)

        if ressource['reward'] > victim['reward']:
            print("Farming")
            if character_state['location'] == ressource['pos']:
                return self.commands.collect()
            else:
                path = self.best_path(character_state['location'], ressource['pos'])
                direction = self.convert_node_to_direction(path)
                return self.commands.move(direction)
        elif victim['reward'] > 10:
            print("Attacking")
            victim_location = other_bots[victim['idx']]['location']
            if self.neighbor(character_state['location'], victim_location):
                direction = self.convert_node_to_direction([character_state['location'], victim_location])
            else:
                path = self.best_path(character_state['location'], victim_location)
                direction = self.convert_node_to_direction(path)
                return self.commands.move(direction)

        else:
            direction = self.convert_node_to_direction(path_to_base)
            return self.commands.move(direction)

        return self.commands.idle()


#(y,x)
#{'location': (7, 1), 'carrying': 0, 'health': 100, 'name': 'My bot', 'points': 0, 'spawn': 0, 'status': 'alive', 'base': (7, 1), 'id': 1}
    def find_best_ressource(self, ch_state):
        best = {"pos":(-1,-1), "reward":0}

        for pos, ml in self.junks.items():
            if best["pos"] is (-1,-1):
                best["pos"] = pos
                best["reward"] = self.junk_reward(ch_state, pos, ml.params()[0])
            else:
                reward = self.junk_reward(ch_state, pos, ml.params()[0])
                if reward > best["reward"]:
                    best["pos"] = pos
                    best["reward"] = reward

        for bot in self.other_bots:
            reward = self.attack_opponent_reward(ch_state, bot)
            if reward > best["reward"]:
                best["pos"] = pos
                best["reward"] = reward

        return best

    def find_best_victim(self, ch_state, other_bots):
        best = {"idx":0, "reward":0}

        for i, bot in enumerate(other_bots):
            reward = self.attack_opponent_reward(ch_state, bot)
            if reward > best["reward"]:
                best["idx"] = i
                best["reward"] = reward

        return best

    def junk_reward(self, ch_state, junk_position, junk_average):
        path_to_junk = self.best_path(ch_state['location'], junk_position)
        nb_tours = len(path_to_junk)
        #TODO prendre en compte les tiles qu'on sait qu'on va se blesser en y allant
        current_sim_health = ch_state['health'] - nb_tours * self.risk_of_injury
        current_sim_gain = 0
        current_sim_turn = self.current_turn + nb_tours
        path_to_base = self.best_path(junk_position, ch_state['base'])
        distance_to_base = len(path_to_base)
        while not self.should_return_to_base(current_sim_turn, current_sim_health, current_sim_gain + ch_state['carrying'], distance_to_base):
            current_sim_gain += junk_average
            nb_tours += 1
            current_sim_turn += 1
            current_sim_health -= self.risk_of_injury
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
        min = len(path)
        for i in range(1, len(self.other_bots)):
            dist = self.distance_between_two_points(character_position, self.other_bots[i]['location'])
            if dist < min:
                min = dist
        return min
