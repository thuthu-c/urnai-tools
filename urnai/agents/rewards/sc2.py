'''
This file is a repository with reward classes for all StarCraft 2 games/minigames we've solved.
'''
from .abreward import RewardBuilder

class SparseReward(RewardBuilder):
    def get_reward(self, obs, reward, done):
        '''
        Always returns 0, unless the game has ended.
        '''
        if not done:
            return 0
        return reward

class GeneralReward(RewardBuilder):
    def __init__(self):
        self.our_reward = 0
        #self.last_own_units_score = 0
        #self.last_own_structures_score = 0
        self.last_killed_units_score = 0
        self.last_killed_structures_score = 0
        #self.last_mineral_rate = 0
        #self.last_vespene_rate = 0

    def get_reward(self, obs, reward, done):
        currentscore = -1
        #currentscore += self.last_own_units_score - obs.score_cumulative.total_value_units
        #currentscore += self.last_own_structures_score - obs.score_cumulative.total_value_structures
        currentscore += obs.score_cumulative.killed_value_units - self.last_killed_units_score
        currentscore += obs.score_cumulative.killed_value_structures - self.last_killed_structures_score
        #currentscore += self.last_mineral_rate - obs.score_cumulative.collection_rate_minerals
        #currentscore += self.last_vespene_rate - obs.score_cumulative.collection_rate_vespene

        #self.last_own_units_score = obs.score_cumulative.total_value_units
        #self.last_own_structures_score = obs.score_cumulative.total_value_structures
        self.last_killed_units_score = obs.score_cumulative.killed_value_units
        self.last_killed_structures_score = obs.score_cumulative.killed_value_structures
        #self.last_mineral_rate = obs.score_cumulative.collection_rate_minerals
        #self.last_vespene_rate = obs.score_cumulative.collection_rate_vespene

        if not done:
            if currentscore != -1:
                self.our_reward = currentscore
                return currentscore
            elif currentscore == -1:
                currentscore = self.our_reward
                self.our_reward = 0
                return currentscore
            return self.our_reward
        return reward*1000
        

class KilledUnitsReward(RewardBuilder):
    def __init__(self):
        # Properties keep track of the change of values used in our reward system
        self._previous_killed_unit_score = 0
        self._previous_killed_building_score = 0

        self._kill_unit_reward = 1
        self._kill_building_reward = 2

    # When the episode is over, the values we use to compute our reward should be reset.
    def reset(self):
        self._previous_killed_unit_score = 0
        self._previous_killed_building_score = 0

    def get_reward(self, obs, reward, done):
        # Getting values from PySC2's cumulative score system
        current_killed_unit_score = obs.score_cumulative[5]
        current_killed_building_score = obs.score_cumulative[6]

        new_reward = 0

        if current_killed_unit_score > self._previous_killed_unit_score:
            new_reward += self._kill_unit_reward

        if current_killed_building_score > self._previous_killed_building_score:
            new_reward += self._kill_building_reward

        # Saving the previous values for killed units and killed buildings.
        self._previous_killed_unit_score = current_killed_unit_score
        self._previous_killed_building_score = current_killed_building_score

        if done:
            self.reset()

        return new_reward