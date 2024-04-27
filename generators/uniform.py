from .generator import Generator


class UniformGenerator(Generator):
    def __init__(self, operator_name, problem_env):
        Generator.__init__(self, operator_name, problem_env)

    def sample_next_point(self, node, n_iter):
        for i in range(n_iter):
            action_parameters = self.sample_from_uniform()
            action, status = self.feasibility_checker.check_feasibility(node,  action_parameters)
            if status == 'HasSolution':
                #print "Found feasible sample"
                break
        return action

