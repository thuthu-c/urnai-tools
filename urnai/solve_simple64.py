from absl import app
from pysc2.env import sc2_env
from envs.sc2 import SC2Env
from envs.trainer import Trainer
from agents.sc2_agent import SC2Agent
from agents.actions.sc2_wrapper import SC2Wrapper
from agents.rewards.sc2 import KilledUnitsReward
from agents.states.sc2 import Simple64State_1
from models.dql_tf import DQLTF

def main(unused_argv):
    trainer = Trainer()

    try:
        ## Initializing our StarCraft 2 environment
        players = [sc2_env.Agent(sc2_env.Race.terran), sc2_env.Bot(sc2_env.Race.random, sc2_env.Difficulty.very_easy)]
        env = SC2Env(map_name="Simple64", players=players, render=False, step_mul=16)
        
        action_wrapper = SC2Wrapper()
        state_builder = Simple64State_1()
        dq_network = DQLTF(action_wrapper=action_wrapper, state_builder=state_builder, save_path='urnai/models/saved/terran_dql')

        ## Terran agent with a Deep Q-Learning model
        agent = SC2Agent(dq_network, KilledUnitsReward(), env)

        trainer.train(env, agent, num_episodes=20, save_steps=1, enable_save=False, reward_from_builder=True) #reward from builder
        trainer.play(env, agent, num_matches=2)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    app.run(main)
