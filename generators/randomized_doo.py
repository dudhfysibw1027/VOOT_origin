import sys
import numpy as np

sys.path.append('../mover_library/')
from .generator import Generator
from planners.mcts_utils import make_action_executable

from mover_library.utils import pick_parameter_distance, place_parameter_distance
from .doo_utils.doo_tree import BinaryDOOTree
from .doo import DOOGenerator

# import matplotlib.pyplot as plt
import copy


class RandomizedDOOGenerator(DOOGenerator):
    def __init__(self, operator_skeleton, problem_env, explr_p):
        DOOGenerator.__init__(self, operator_skeleton, problem_env, explr_p)
        self.dim_x = self.domain[0].shape[-1]

    def choose_next_point(self):
        next_node = self.doo_tree.get_next_point_and_node_to_evaluate()
        x_to_evaluate = np.random.uniform(next_node.cell_min, next_node.cell_max, (1, self.dim_x)).squeeze()
        next_node.evaluated_x = x_to_evaluate
        x_to_evaluate = self.unnormalize_x_value(x_to_evaluate)
        self.doo_tree.update_evaled_x_to_node(x_to_evaluate, next_node)
        return x_to_evaluate, next_node

    def get_cell_samples(self, n_samples=50):
        next_node = self.doo_tree.get_next_point_and_node_to_evaluate()
        samples = []
        for i in range(n_samples):
            samples.append(np.random.uniform(next_node.cell_min, next_node.cell_max, (1, self.dim_x)).squeeze())
        return samples


