import numpy
import random
from collections import deque
from models.base.abmodel import LearningModel
from agents.actions.base.abwrapper import ActionWrapper
from agents.states.abstate import StateBuilder
from utils.error import UnsuportedLibraryError
from utils import constants
from models.memory_representations.neural_network.nnfactory import NeuralNetworkFactory
#from models.memory_representations.neural_network.nnfactory.NeuralNetworkFactory import get_nn_model

class DeepQLearning(LearningModel):
    """
    Generalistic Deep Q Learning Algorithm.

    This implementation of DQL allows the user to seamlessly select which backend Machine Learning 
    Library (Keras, Pytorch, etc) they would like to use with this algorithm by passing them as a parameter.

    This is done through the "lib" parameter, which can receive the name of any ML Library 
    supported by URNAI (full list at urnai.utils.constants.Libraries).

    More advanced users can also easily override any of the default URNAI model builders for Keras, Pytorch etc
    by passing a custom Neural Network class as the "neural_net_class" parameter. This class can have any
    model architecture that you desire, as long as it fits URNAI's overall Neural Network architecture. 
   
    An easy way of building one such class is inheriting from ABNeuralNetwork (urnai.models.memory_representations.abneuralnetwork) 
    or inheriting directly from a Default NN class for a specific ML Library you wish to work with, such as 
    KerasDeepNeuralNetwork or PyTorchDeepNeuralNetwork, and building from there.
    
    An example of a model architecture override can be seen at 
    urnai.models.memory_representations.neural_network.keras 
    in the DNNCustomModelOverrideExample class.


    Parameters:
        action_wrapper: Object
            Object responsible for describing possible actions
        state_builder: Object
            Object responsible for creating states from the game environment
        learning_rate: Float
            Rate at which the deep learning algorithm will learn 
            (alpha on most mathematical representations)
        learning_rate_min: Float
            Minimum value that learning_rate will reach throught training
        learning_rate_decay: Float
            Inverse of the rate at which the learning rate will decay each episode 
            (defaults to 1 so no decay)
        learning_rate_decay_ep_cutoff: Integer
            Episode at which learning rate decay will start (defaults to 0)
        gamma: Float
            Gamma parameter in the Deep Q Learning algorithm
        name: String
            Name of the algorithm implemented
        build_model: Python dict
            A dict representing the NN's layers. Can be generated by the 
            ModelBuilder.get_model_layout() method from an instantiated ModelBuilder object.
        epsilon_start: Float
            Value that the epsilon from epsilon greedy strategy will start from (defaults to 1)
        epsilon_min: Float
            Minimum value that epsilon will reach trough training
        epsilon_decay: Float
            Inverse of the rate at which the epsilon value will decay each step 
            (0.99 => 1% will decay each step)
        per_episode_epsilon_decay:  Bool
            Whether or not the epsilon decay will be done each episode, instead of each step
        use_memory: Bool
            If true the algorithm will keep an internal queue of state, action, 
            reward and next_state tuple to sample from during training
        memory_maxlen: Integer
            Max lenght of the memory queue.
        batch_size: Integer
            Size of our learning batch to be passed to the Machine Learning library
        min_memory_size: Integer
            Minimum length of the memory queue in order to start training (it's customary to 
            acumulate some tuples before commencing training)
        seed_value: Integer (default None)
            Value to assing to random number generators in Python and our ML libraries to try 
            and create reproducible experiments
        cpu_only: Bool
            If true will run algorithm only using CPU, also useful for reproducibility since GPU 
            paralelization creates uncertainty
        lib: String
            Name of the Machine Learning library that should be used with the instanced Deep Q Learning 
            algorithm (names of accepted libraries are defined in urnai.utils.constants.Libraries)
        neural_net_class: Python Class (default None)
            A Python Class representing a Neural Network implementation, useful for advanced users 
            to override any of the default URNAI models. 
            If this parameter is left as None, __init__() will use the "lib" parameter to select 
            one of the standard URNAI model builders, depending on which library was chosen.
        epsilon_linear_decay: Bool
            Flag to decay epsilon linearly instead of exponentially.
        lr_linear_decay: Bool
            Flag to decay learning rate linearly instead of exponentially.
    """

    def __init__(self, action_wrapper: ActionWrapper, state_builder: StateBuilder, learning_rate=0.001, learning_rate_min=0.0001, learning_rate_decay=1, 
                learning_rate_decay_ep_cutoff=0, gamma=0.99, name='DeepQLearning', build_model = None, epsilon_start=1.0, epsilon_min=0.005, epsilon_decay=0.99995, 
                per_episode_epsilon_decay=False, use_memory=True, memory_maxlen=50000, batch_size=32, min_memory_size=2000, seed_value=None, cpu_only=False, lib='keras', neural_net_class=None, epsilon_linear_decay=False, lr_linear_decay=False):
        super().__init__(action_wrapper, state_builder, gamma, learning_rate, learning_rate_min, learning_rate_decay, epsilon_start, epsilon_min, epsilon_decay , per_episode_epsilon_decay, learning_rate_decay_ep_cutoff, name, seed_value, cpu_only, epsilon_linear_decay, lr_linear_decay)
        
        self.batch_size = batch_size
        self.build_model = build_model
        self.lib = lib
        self.neural_net_class = neural_net_class

        if neural_net_class != None:
            self.dnn = neural_net_class(self.action_size, self.state_size, self.build_model, self.gamma, self.learning_rate, self.seed_value, self.batch_size)
        else:
            self.dnn = NeuralNetworkFactory.get_nn_model(self.action_size, self.state_size, self.build_model, self.lib, self.gamma, self.learning_rate, self.seed_value, self.batch_size)

        self.use_memory = use_memory
        if self.use_memory:
            self.memory = deque(maxlen=memory_maxlen)
            self.memory_maxlen = memory_maxlen
            self.min_memory_size = min_memory_size

    def learn(self, s, a, r, s_, done):
        if self.use_memory:
            self.memory_learn(s, a, r, s_, done)
        else:
            self.no_memory_learn(s, a, r, s_, done)

        # if our epsilon rate decay is set to be done every step, we simply decay it. Otherwise, this will only be done
        # at the end of every episode, on self.ep_reset() which is in our LearningModel base class
        if not self.per_episode_epsilon_decay:
            self.decay_epsilon()

    def memory_learn(self, s, a, r, s_, done):
        self.memorize(s, a, r, s_, done)
        if len(self.memory) < self.min_memory_size:
            return

        batch = random.sample(self.memory, self.batch_size)
        states = numpy.array([val[0] for val in batch])
        states = numpy.squeeze(states)
        next_states = numpy.array([(numpy.zeros(self.state_size)
                                if val[3] is None else val[3]) for val in batch])
        next_states = numpy.squeeze(next_states)

        # predict Q(s,a) given the batch of states
        q_s_a = self.dnn.get_output(states)

        # predict Q(s',a') - so that we can do gamma * max(Q(s'a')) below
        q_s_a_d = self.dnn.get_output(next_states)

        # setup training arrays
        target_q_values = numpy.zeros((len(batch), self.action_size))

        for i, (state, action, reward, next_state, done) in enumerate(batch):
            # get the current q values for all actions in state
            current_q = numpy.copy(q_s_a[i])
            if done:
                # if this is the last step, there is no future max q value, so we the new_q is just the reward
                current_q[action] = reward
            else:
                # new Q-value is equal to the reward at that step + discount factor * the max q-value for the next_state
                current_q[action] = reward + self.gamma * numpy.amax(q_s_a_d[i])
            
            target_q_values[i] = current_q

        # update neural network with expected q values
        self.dnn.update(states, target_q_values)

    def no_memory_learn(self, s, a, r, s_, done):
        #get output for current sars array
        # rows = 1 
        # cols = self.action_size
        # target_q_values = numpy.zeros(shape=(rows, cols))

        q_s_a = self.dnn.get_output(s)

        expected_q = 0
        if done:
            expected_q = r
        else:
            expected_q = r + self.gamma * self.__maxq(s_)

        q_s_a[0, a] = expected_q

        self.dnn.update(s, q_s_a)

    def __maxq(self, state):
        values = self.dnn.get_output(state)
        mxq = values.max()
        return mxq

    def choose_action(self, state, excluded_actions=[], is_testing=False):
        if is_testing:
            return self.predict(state, excluded_actions)
        else:
            if numpy.random.rand() <= self.epsilon_greedy:
                random_action = random.choice(self.actions)

                # Removing excluded actions
                while random_action in excluded_actions:
                    random_action = random.choice(self.actions)
                return random_action
            else:
                return self.predict(state, excluded_actions)

    def predict(self, state, excluded_actions=[]):
        q_values = self.dnn.get_output(state)
        action_idx = numpy.argmax(q_values)

        # Removing excluded actions
        # TODO: This is possibly badly optimized, eventually look back into this
        while action_idx in excluded_actions:
            q_values = numpy.delete(q_values, action_idx)
            action_idx = numpy.argmax(q_values)
        
        action = int(action_idx)
        return action

    def memorize(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def save_extra(self, persist_path):
        self.dnn.save(persist_path)

    def load_extra(self, persist_path):
        self.dnn.load(persist_path)
