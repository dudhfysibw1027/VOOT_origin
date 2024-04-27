import os
import sys
from multiprocessing.pool import ThreadPool  # dummy is nothing but multiprocessing but wrapper around threading
import argparse


def worker_p(config):
    n_iter = config[0]
    problem_idx = config[1]
    algo_name = config[2]
    dim = config[3]
    obj_fcn = config[4]

    command = 'python ./test_scripts/test_optimization_algorithms.py -problem_idx ' \
              + str(problem_idx) \
              + ' -algo_name ' + algo_name \
              + ' -dim_x ' + str(dim) \
              + ' -n_fcn_evals ' + str(n_iter) \
              + ' -obj_fcn ' + str(obj_fcn) \

    print(command)
    os.system(command)


def worker_wrapper_multi_input(multi_args):
    return worker_p(multi_args)


def main():
    # python test_scripts/threaded_test_optimization_algorithms.py stovoo 10 1000 0,20 griewank 1 100,200,300,400,500,1000,5000 2,3,4,10,20,30,100 10,20,30,100
    # python test_scripts/threaded_test_optimization_algorithms.py voo 10 500 0,10 griewank 0 0 
    algo_name = sys.argv[1]
    dim = int(sys.argv[2])
    n_iter = sys.argv[3]
    pidxs = sys.argv[4].split(',')
    pidxs = list(range(int(pidxs[0]), int(pidxs[1])))
    obj_fcn = sys.argv[5]

    configs= []
    for pidx in pidxs:
        configs.append([n_iter, pidx, algo_name, dim, obj_fcn])

    if algo_name == 'gpucb' or algo_name == 'bamsoo' or algo_name == 'rembo_ei':
        n_workers = int(3)
    else:
        n_workers = int(30)

    print(configs)
    pool = ThreadPool(n_workers)
    results = pool.map(worker_wrapper_multi_input, configs)


if __name__ == '__main__':
    main()
