import numpy as np
import sys
import copy
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../mover_library/')
from .conveyor_belt_problem import create_conveyor_belt_problem
from .problem_environment import ProblemEnvironment
from trajectory_representation.operator import Operator
import pickle as pickle
import re
from mover_library.utils import *
from manipulation.primitives.savers import DynamicEnvironmentStateSaver
from openravepy import DOFAffine, Environment

from mover_library.motion_planner import collision_fn, base_extend_fn, base_sample_fn, base_distance_fn


class ConveyorBelt(ProblemEnvironment):
    def __init__(self, problem_idx, n_actions_per_node):
        self.problem_idx = problem_idx
        ProblemEnvironment.__init__(self, problem_idx)
        obj_setup = None
        self.problem_config = create_conveyor_belt_problem(self.env, obj_setup, problem_idx)
        self.objects = self.problem_config['objects']
        if self.problem_idx == 0:
            self.objects = self.objects[4:]
        else:
            pass

        self.init_base_conf = np.array([0, 1.05, 0])
        self.fetch_planner = None

        self.regions = {'entire_region': self.problem_config['entire_region'],
                        'object_region': self.problem_config['loading_region'],
                        'big_region_1': self.problem_config['big_region_1'],
                        'big_region_2': self.problem_config['big_region_2']}

        self.robot = self.problem_config['env'].GetRobots()[0]
        self.infeasible_reward = -2
        self.curr_state = self.get_state()
        self.n_actions_per_node = n_actions_per_node

        self.init_saver = DynamicEnvironmentStateSaver(self.env)
        self.is_init_pick_node = True
        self.init_operator = 'two_arm_place'
        self.name = 'convbelt'
        self.picks = pickle.load(open('problem_environments/convbelt_picks.pkl', 'r'))

    def check_reachability_precondition(self, operator_instance):
        held = self.robot.GetGrabbed()[0]
        # todo refactor
        if held.GetName().find('big') != -1:
            original_xytheta = get_body_xytheta(self.robot)
            set_robot_config(operator_instance.continuous_parameters['base_pose'], self.robot)
            if self.regions['big_region_1'].contains(held.ComputeAABB()) or \
                    self.regions['big_region_2'].contains(held.ComputeAABB()):
                set_robot_config(original_xytheta, self.robot)
                return None, "NoSolution"
            set_robot_config(original_xytheta, self.robot)

        goal_robot_xytheta = operator_instance.continuous_parameters['base_pose']

        if operator_instance.low_level_motion is not None:
            motion = operator_instance.low_level_motion
            status = 'HasSolution'
            return motion, status

        motion, status = self.get_base_motion_plan(goal_robot_xytheta, None)
        grabbed_obj = self.robot.GetGrabbed()[0]
        obj_name = grabbed_obj.GetName()
        return motion, status

    def get_base_motion_plan(self, goal, region_name=None, n_iterations=None):
        self.robot.SetActiveDOFs([], DOFAffine.X | DOFAffine.Y | DOFAffine.RotationAxis, [0, 0, 1])

        # first plan to the narrow passage
        d_fn = base_distance_fn(self.robot, x_extents=3.9, y_extents=7.1)
        s_fn = base_sample_fn(self.robot, x_extents=4.225, y_extents=5, x=-3.175, y=-3)
        e_fn = base_extend_fn(self.robot)
        c_fn = collision_fn(self.env, self.robot)
        q_init = self.robot.GetActiveDOFValues()

        held = self.robot.GetGrabbed()[0]
        print("Base motion planning...")
        if held.GetName().find('big') != -1:
            n_iterations = [20, 50, 100, 500, 1000]
            path, status = self.get_motion_plan(q_init, goal, d_fn, s_fn, e_fn, c_fn, n_iterations)
        # todo if it is in the big-region, then just to moton planning
        else:
            set_robot_config(goal, self.robot)
            if not self.regions['big_region_1'].contains(held.ComputeAABB()) and \
                    not self.regions['big_region_2'].contains(held.ComputeAABB()):
                n_iterations = [20, 50, 100, 500, 1000]
                set_robot_config(q_init, self.robot)
                path, status = self.get_motion_plan(q_init, goal, d_fn, s_fn, e_fn, c_fn, n_iterations)
            else:
                n_iterations = [20, 50, 100, 500, 1000]
                set_robot_config(q_init, self.robot)
                path, status = self.get_motion_plan(q_init, goal, d_fn, s_fn, e_fn, c_fn, n_iterations)

                """
                subgoal = np.array([-2.8, -0.5, 0])
                angles = np.random.permutation(np.linspace(10, 120, 30))
                is_subgoal_collision = True
                for angle in angles:
                    subgoal[-1] = angle * np.pi/180
                    set_robot_config(subgoal, self.robot)
                    if not self.env.CheckCollision(self.robot):
                        is_subgoal_collision = False
                        break
                set_robot_config(q_init, self.robot)
                if is_subgoal_collision:
                    print 'Subgoal collision'
                    return None, "NoSolution"
                else:
                    n_iterations = [20, 50, 100, 500, 1000, 2000]
                    path1, status = self.get_motion_plan(q_init, subgoal, d_fn, s_fn, e_fn, c_fn, n_iterations)
                    if path1 is None:
                        print 'Path 1 not found'
                        return path1, status
                    print "Path 1 found"
                    set_robot_config(subgoal, self.robot)
                    n_iterations = [20, 50, 100, 500, 1000, 2000]
                    path2, status = self.get_motion_plan(subgoal, goal, d_fn, s_fn, e_fn, c_fn, n_iterations)
                    if path2 is None:
                        set_robot_config(q_init, self.robot)
                        print 'Path 2 not found'
                        return path2, status
                    print "Path 2 found"
                path = path1+path2
                """

        set_robot_config(q_init, self.robot)
        print("Status,", status)
        return path, status

    def reset_to_init_state(self, node):
        assert node.is_init_node, "None initial node passed to reset_to_init_state"
        saver = node.state_saver
        saver.Restore()
        self.curr_state = self.get_state()
        self.objects_currently_not_in_goal = node.objects_not_in_goal

        if node.parent_action is not None:
            is_parent_action_pick = node.parent_action.type == 'two_arm_pick'
        else:
            is_parent_action_pick = False

        if is_parent_action_pick:
            obj = node.parent_action.discrete_parameters['object']
            grab_obj(self.robot, obj)

        self.robot.SetActiveDOFs([], DOFAffine.X | DOFAffine.Y | DOFAffine.RotationAxis, [0, 0, 1])

    def apply_action_and_get_reward(self, operator_instance, is_op_feasible, node):
        if is_op_feasible != 'HasSolution':
            reward = self.infeasible_reward
        else:
            if operator_instance.type == 'two_arm_pick':
                two_arm_pick_object(operator_instance.discrete_parameters['object'],
                                    self.robot, operator_instance.continuous_parameters)
                set_robot_config(self.init_base_conf, self.robot)
                reward = 0
            elif operator_instance.type == 'two_arm_place':
                reward, new_objects_not_in_goal = self.compute_place_reward(operator_instance)
                self.set_objects_not_in_goal(new_objects_not_in_goal)
            elif operator_instance.type.find('_paps') != -1:
                reward, new_objects_not_in_goal = self.compute_place_reward(operator_instance)
                self.set_objects_not_in_goal(new_objects_not_in_goal)
            else:
                raise NotImplementedError

        return reward

    def apply_operator_instance(self, operator_instance, node):
        if not self.check_parameter_feasibility_precondition(operator_instance):
            operator_instance.update_low_level_motion(None)
            return self.infeasible_reward

        status = 'NoSolution'
        if operator_instance.type == 'two_arm_place':
            motion_plan, status = self.check_reachability_precondition(operator_instance)
            operator_instance.update_low_level_motion(motion_plan)
        elif operator_instance.type.find('_paps') != -1:
            # todo refactor
            state_saver = CustomStateSaver(self.env)
            objects = operator_instance.discrete_parameters['objects']
            place_base_poses = operator_instance.continuous_parameters['base_poses']
            motion_plans = []
            for obj, bpose in zip(objects, place_base_poses):
                self.pick_object(obj)
                set_robot_config(self.init_base_conf, self.robot)
                operator_instance.continuous_parameters['base_pose'] = bpose
                motion_plan, status = self.check_reachability_precondition(operator_instance)
                if status == 'NoSolution':
                    release_obj(self.robot, obj)
                    break
                else:
                    motion_plans.append(motion_plan)
                    two_arm_place_object(obj, self.robot, operator_instance.continuous_parameters)
            if status == 'HasSolution':
                if operator_instance.low_level_motion is None:
                    operator_instance.update_low_level_motion(motion_plans)
            state_saver.Restore()
        else:
            status = "HasSolution"

        reward = self.apply_action_and_get_reward(operator_instance, status, node)
        return reward

    def pick_object(self, target_object):
        held = None
        if len(self.robot.GetGrabbed()) > 0:
            held = self.robot.GetGrabbed()[0]
            release_obj(self.robot, held)

        if target_object == held:
            grab_obj(self.robot, held)
        else:
            pick_params = self.get_pick_for_obj(target_object)
            two_arm_pick_object(target_object, self.robot, pick_params)

    def compute_place_reward(self, operator_instance):
        is_op_type_pap = operator_instance.type.find('_paps') != -1
        if is_op_type_pap:
            objects = operator_instance.discrete_parameters['objects']
            place_base_poses = operator_instance.continuous_parameters['base_poses']
            reward = 0
            for idx, obj_bpose in enumerate(zip(objects, place_base_poses)):
                obj = obj_bpose[0]
                bpose = obj_bpose[1]
                self.pick_object(obj)
                operator_instance.continuous_parameters['base_pose'] = bpose
                two_arm_place_object(obj, self.robot, operator_instance.continuous_parameters)
                reward += np.exp(-0.1 * get_trajectory_length(operator_instance.low_level_motion[idx]))
            new_objects_not_in_goal = self.objects_currently_not_in_goal[self.n_actions_per_node:]
        elif operator_instance.type == 'two_arm_place':
            assert len(self.robot.GetGrabbed()) == 1
            object_held = self.robot.GetGrabbed()[0]
            two_arm_place_object(object_held, self.robot, operator_instance.continuous_parameters)
            new_objects_not_in_goal = self.objects_currently_not_in_goal[1:]
            reward = np.exp(-0.1 * get_trajectory_length(operator_instance.low_level_motion))
        else:
            raise NotImplementedError
        return reward, new_objects_not_in_goal

    def is_goal_reached(self):
        return len(self.get_objs_in_region('object_region')) == len(self.objects)

    def load_object_setup(self):
        object_setup_file_name = './problem_environments/conveyor_belt_domain_problems/' + str(
            self.problem_idx) + '.pkl'
        if os.path.isfile(object_setup_file_name):
            obj_setup = pickle.load(
                open('./problem_environments/conveyor_belt_domain_problems/' + str(self.problem_idx) + '.pkl', 'r'))
            return obj_setup
        else:
            return None

    def save_object_setup(self):
        object_configs = {'object_poses': self.problem_config['obj_poses'],
                          'object_shapes': self.problem_config['obj_shapes'],
                          'obst_poses': self.problem_config['obst_poses'],
                          'obst_shapes': self.problem_config['obst_shapes']}
        pickle.dump(object_configs,
                    open('./problem_environments/conveyor_belt_domain_problems/' + str(self.problem_idx) + '.pkl',
                         'wb'))

    def get_applicable_op_skeleton(self, parent_action):
        if parent_action is None:
            op_name = 'two_arm_pick'
        else:
            # use_multipaps = parent_action.discrete_parameters['object'].GetName().find("big") != -1
            use_multipaps = self.n_actions_per_node > 1
            if parent_action.type == 'two_arm_pick':
                if use_multipaps:
                    op_name = str(self.n_actions_per_node) + '_paps'
                else:
                    op_name = 'two_arm_place'
            else:
                op_name = 'two_arm_pick'

        if op_name == 'two_arm_place':
            op = Operator(operator_type=op_name,
                          discrete_parameters={'region': self.regions['object_region'],
                                               'object': self.objects_currently_not_in_goal[0]},
                          continuous_parameters=None,
                          low_level_motion=None)
        elif op_name == 'two_arm_pick':
            op = Operator(operator_type=op_name,
                          discrete_parameters={'object': self.objects_currently_not_in_goal[0]},
                          continuous_parameters=None,
                          low_level_motion=None)
        elif op_name.find('_paps') != -1:
            objects = self.objects_currently_not_in_goal[0:self.n_actions_per_node]
            op = Operator(operator_type=op_name,
                          discrete_parameters={'objects': objects,
                                               'region': self.regions['object_region']
                                               },
                          continuous_parameters=None,
                          low_level_motion=None)
        else:
            raise NotImplementedError
        return op

    def get_pick_for_obj(self, obj):
        obj_number = int(re.search(r'\d+', obj.GetName()).group())
        return self.picks[obj_number]
