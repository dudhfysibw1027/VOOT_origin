# import sys, os

# sys.path.append(os.getcwd())
sys.path.append("/git/VOOT_origin/openrave_wrapper")
sys.path.append("/git/VOOT_origin/openrave_wrapper/manipulation")
# sys.path.append('/usr/local/lib/python2.7/site-packages')

from planners.mcts import MCTS

import argparse
import pickle as pickle
import os
import numpy as np
import random
# import socket
import openravepy

# from problem_instantiators.minimum_constraint_removal_instantiator import MinimumConstraintRemovalInstantiator
# from problem_instantiators.conveyor_belt_instantiator import ConveyorBeltInstantiator
from openravepy import RaveSetDebugLevel, DebugLevel

from problem_environments.synthetic_env import ShekelSynthetic, RastriginSynthetic, GriewankSynthetic

# hostname = socket.gethostname()
# if hostname == 'dell-XPS-15-9560' or hostname == 'phaedra' or hostname == 'shakey' or hostname == 'lab':
#     ROOTDIR = './'
# else:
#     ROOTDIR = '/data/public/rw/pass.port/gtamp_results/'


def make_save_dir(args):
    domain = args.domain
    uct_parameter = args.uct
    w = args.w
    sampling_strategy = args.sampling_strategy
    sampling_strategy_exploration_parameter = args.epsilon
    mcts_iter = args.mcts_iter
    n_feasibility_checks = args.n_feasibility_checks
    addendum = args.add
    c1 = args.c1

    save_dir = "" + '/test_results/' + domain + '_results/' + 'mcts_iter_' + str(mcts_iter) + '/'
    save_dir += '/uct_' + str(uct_parameter) + '_widening_' \
                + str(w) + '_' + sampling_strategy \
                + '_n_feasible_checks_' + str(n_feasibility_checks) \
                + '_n_switch_' + str(args.n_switch) \
                + '_max_backup_' + str(args.use_max_backup) \
                + '_pick_switch_' + str(args.pick_switch) \
                + '_n_actions_per_node_' + str(args.n_actions_per_node)

    if domain.find('synthetic') != -1:
        save_dir += '_value_threshold_' + str(args.value_threshold)

    if addendum != '':
        save_dir += '_' + addendum + '/'
    else:
        save_dir += '/'

    if sampling_strategy == 'voo':
        save_dir += '/sampling_mode/' + args.voo_sampling_mode + '/'
        save_dir += '/counter_ratio_' + str(args.voo_counter_ratio) + '/'

    if sampling_strategy != 'unif':
        save_dir += '/eps_' + str(sampling_strategy_exploration_parameter) + '/'

    if not os.path.isdir(save_dir):
        try:
            os.makedirs(save_dir)
        except OSError:
            pass
    return save_dir


def instantiate_mcts(args, problem_env):
    uct_parameter = args.uct
    w = args.w
    sampling_strategy = args.sampling_strategy
    sampling_strategy_exploration_parameter = args.epsilon
    n_feasibility_checks = args.n_feasibility_checks
    c1 = args.c1
    use_progressive_widening = args.pw
    use_ucb = args.use_ucb
    sampling_mode = args.voo_sampling_mode

    mcts = MCTS(w, uct_parameter, sampling_strategy,
                sampling_strategy_exploration_parameter, c1, n_feasibility_checks,
                problem_env, use_progressive_widening, use_ucb, args.use_max_backup, args.pick_switch,
                sampling_mode, args.voo_counter_ratio, args.n_switch)
    return mcts


def set_random_seed(random_seed):
    np.random.seed(random_seed)
    random.seed(random_seed)


def make_plan_pklable(plan):
    for p in plan:
        if p.type == 'two_arm_pick':
            p.discrete_parameters['object'] = p.discrete_parameters['object'].GetName()
        elif p.type == 'two_arm_place':
            p.discrete_parameters['region'] = p.discrete_parameters['region'].name
        elif p.type.find('_paps') != -1:
            for idx, obj in enumerate(p.discrete_parameters['objects']):
                p.discrete_parameters['objects'][idx] = obj.GetName()
            if 'object' in list(p.discrete_parameters.keys()):
                p.discrete_parameters['object'] = p.discrete_parameters['object'].GetName()
    return plan


def main():
    parser = argparse.ArgumentParser(description='MCTS parameters')
    parser.add_argument('-uct', type=float, default=0.0)
    parser.add_argument('-w', type=float, default=5.0)
    parser.add_argument('-epsilon', type=float, default=0.3)
    parser.add_argument('-sampling_strategy', type=str, default='unif')
    parser.add_argument('-problem_idx', type=int, default=-1)
    parser.add_argument('-domain', type=str, default='minimum_displacement_removal')
    parser.add_argument('-planner', type=str, default='mcts')
    parser.add_argument('-v', action='store_true', default=False)
    parser.add_argument('-debug', action='store_true', default=False)
    parser.add_argument('-use_ucb', action='store_true', default=False)
    parser.add_argument('-pw', action='store_true', default=False)
    parser.add_argument('-mcts_iter', type=int, default=1500)
    parser.add_argument('-max_time', type=float, default=np.inf)
    parser.add_argument('-c1', type=float, default=1)  # weight for measuring distances in SE(2)
    parser.add_argument('-n_feasibility_checks', type=int, default=50)
    parser.add_argument('-random_seed', type=int, default=-1)
    parser.add_argument('-voo_sampling_mode', type=str, default='uniform')
    parser.add_argument('-voo_counter_ratio', type=int, default=1)
    parser.add_argument('-n_switch', type=int, default=10)
    parser.add_argument('-add', type=str, default='')
    parser.add_argument('-use_max_backup', action='store_true', default=False)
    parser.add_argument('-pick_switch', action='store_true', default=False)
    parser.add_argument('-n_actions_per_node', type=int, default=1)
    parser.add_argument('-value_threshold', type=float, default=40.0)

    args = parser.parse_args()
    RaveSetDebugLevel(DebugLevel.Error)

    if args.domain == 'convbelt':
        args.mcts_iter = 3000
        args.n_switch = 10
        args.pick_switch = False
        args.use_max_backup = True
        args.n_feasibility_checks = 50
        args.problem_idx = 3
        args.n_actions_per_node = 3
        if args.pw:
            args.sampling_strategy = 'unif'
            args.pw = True
            args.use_ucb = True
        else:
            args.w = 5.0
            if args.sampling_strategy == 'voo':
                args.voo_sampling_mode = 'uniform'
            elif args.sampling_strategy == 'randomized_doo':
                pass
                # args.epsilon = 1.0
        if args.pw:
            args.add = 'pw_reevaluates_infeasible'
        else:
            args.add = 'no_averaging'

    elif args.domain == 'minimum_displacement_removal':
        args.mcts_iter = 2000
        args.n_switch = 10
        args.pick_switch = True
        args.use_max_backup = True
        args.n_feasibility_checks = 50
        args.problem_idx = 0
        args.n_actions_per_node = 1
        if args.pw:
            args.sampling_strategy = 'unif'
            args.pw = True
            args.use_ucb = True
        else:
            args.w = 5.0
            if args.sampling_strategy == 'voo':
                args.voo_sampling_mode = 'uniform'
            elif args.sampling_strategy == 'randomized_doo':
                pass
                # args.epsilon = 1.0
            elif args.sampling_strategy == 'doo':
                pass
                # args.epsilon = 1.0
        if args.pw:
            args.add = 'pw_reevaluates_infeasible'
        else:
            args.add = 'no_averaging'
    else:
        if args.problem_idx == 0:
            args.mcts_iter = 10000
            args.n_switch = 5
        elif args.problem_idx == 1:
            args.mcts_iter = 10000
            args.n_switch = 5
        elif args.problem_idx == 2:
            args.mcts_iter = 10000
            args.n_switch = 3
        else:
            raise NotImplementedError

        if args.pw:
            args.sampling_strategy = 'unif'
            args.pw = True
            args.use_ucb = True
        else:
            args.w = 100

        if args.domain == 'synthetic_rastrigin' and args.problem_idx == 1:
            args.value_threshold = -50

        args.voo_sampling_mode = 'centered_uniform'
        args.use_max_backup = True

    if args.pw:
        assert args.w > 0 and args.w <= 1
    else:
        pass

    if args.sampling_strategy != 'unif':
        assert args.epsilon >= 0.0

    if args.random_seed == -1:
        args.random_seed = args.problem_idx

    print("Problem number ", args.problem_idx)
    print("Random seed set: ", args.random_seed)
    set_random_seed(args.random_seed)

    save_dir = make_save_dir(args)
    print("Save dir is", save_dir)
    stat_file_name = save_dir + '/rand_seed_' + str(args.random_seed) + '_pidx_' + str(args.problem_idx) + '.pkl'
    if os.path.isfile(stat_file_name):
        print("already done")
        return -1

    if args.domain == 'minimum_displacement_removal':
        problem_instantiator = MinimumConstraintRemovalInstantiator(args.problem_idx, args.domain)
        environment = problem_instantiator.environment
    elif args.domain == 'convbelt':
        # todo make root switching in conveyor belt domain
        problem_instantiator = ConveyorBeltInstantiator(args.problem_idx, args.domain, args.n_actions_per_node)
        environment = problem_instantiator.environment
    else:
        if args.domain.find("rastrigin") != -1:
            environment = RastriginSynthetic(args.problem_idx, args.value_threshold)
        elif args.domain.find("griewank") != -1:
            environment = GriewankSynthetic(args.problem_idx)
        elif args.domain.find("shekel") != -1:
            environment = ShekelSynthetic(args.problem_idx)

    if args.v:
        environment.env.SetViewer('qtcoin')

    mcts = instantiate_mcts(args, environment)
    search_time_to_reward, best_v_region_calls, plan = mcts.search(args.mcts_iter)
    plan = make_plan_pklable(plan)

    print("Number of best-vregion calls: ", best_v_region_calls)
    pickle.dump({'search_time': search_time_to_reward, 'plan': plan, 'pidx': args.problem_idx},
                open(stat_file_name, 'wb'))

    if args.domain != 'synthetic':
        environment.env.Destroy()
        openravepy.RaveDestroy()


if __name__ == '__main__':
    main()
