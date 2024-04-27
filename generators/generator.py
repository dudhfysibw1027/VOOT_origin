import numpy as np
from mover_library.utils import get_pick_domain, get_place_domain

# from .feasibility_checkers.pick_feasibility_checker import PickFeasibilityChecker
# from .feasibility_checkers.place_feasibility_checker import PlaceFeasibilityChecker
# from .feasibility_checkers.multi_pap_feasibility_checker import MultiPapFeasibilityChecker


class Generator:
    def __init__(self, operator_name, problem_env):
        self.problem_env = problem_env
        self.env = problem_env.env
        self.evaled_actions = []
        self.evaled_q_values = []

        if operator_name == 'two_arm_pick':
            self.domain = get_pick_domain()
            # self.feasibility_checker = PickFeasibilityChecker(problem_env)
        elif operator_name == 'two_arm_place':
            if problem_env.name == 'convbelt':
                place_domain = get_place_domain(problem_env.regions['object_region'])
            else:
                place_domain = get_place_domain(problem_env.regions['entire_region'])
            self.domain = place_domain
            # self.feasibility_checker = PlaceFeasibilityChecker(problem_env)
        elif operator_name.find('_paps') != -1:
            assert problem_env.name == 'convbelt'
            self.place_domain = get_place_domain(problem_env.regions['object_region'])
            self.pick_domain = get_pick_domain()
            n_actions = int(operator_name.split('_')[0])

            self.domain = np.vstack([
                                     np.hstack([self.place_domain[0]]*n_actions),
                                     np.hstack([self.place_domain[1]]*n_actions)
                                     ])
            # self.feasibility_checker = MultiPapFeasibilityChecker(problem_env, n_actions)
        elif operator_name.find('synthetic') != -1:
            dim_x = int(operator_name.split('synthetic_')[1])
            if problem_env.name.find('shekel') != -1:
                self.domain = np.array([[-500.] * dim_x, [500.] * dim_x])
            elif problem_env.name.find('rastrigin') != -1:
                self.domain = np.array([[-5.12] * dim_x, [5.12] * dim_x])
            elif problem_env.name.find('griewank'):
                self.domain = np.array([[-600.] * dim_x, [600.] * dim_x])
            else:
                raise NotImplementedError

            class DummyFeasibilityChecker:
                def __init__(self):
                    pass

                def check_feasibility(self, node, action_parameter):
                    action = {}
                    action['is_feasible'] = True
                    action['action_parameters'] = action_parameter
                    return action, 'HasSolution'

            self.feasibility_checker = DummyFeasibilityChecker()
        else:
            print("Generator not implemented for", operator_name)
            raise NotImplementedError

    def update_evaled_values(self, node):
        executed_actions_in_node = list(node.Q.keys())
        executed_action_values_in_node = list(node.Q.values())

        for action, q_value in zip(executed_actions_in_node, executed_action_values_in_node):
            action_parameters = action.continuous_parameters['action_parameters']
            is_in_array = [np.array_equal(action_parameters, a) for a in self.evaled_actions]
            is_action_included = np.any(is_in_array)

            if not is_action_included:
                self.evaled_actions.append(action_parameters)
                self.evaled_q_values.append(q_value)
            else:
                # update the value if the action is included
                self.evaled_q_values[np.where(is_in_array)[0][0]] = q_value

    def sample_next_point(self, node, n_iter):
        raise NotImplementedError

    def sample_from_uniform(self):
        dim_parameters = self.domain.shape[-1]
        domain_min = self.domain[0]
        domain_max = self.domain[1]
        return np.random.uniform(domain_min, domain_max, (1, dim_parameters)).squeeze()

