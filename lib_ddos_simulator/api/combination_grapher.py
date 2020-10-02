#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the Combination_Grapher to graph ddos simulations"""

__Lisence__ = "BSD"
__maintainer__ = "Justin Furuness"
__email__ = "jfuruness@gmail.com, agorbenko97@gmail.com"
__status__ = "Development"

import logging
import os

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from statistics import mean, variance
from math import sqrt
from multiprocessing import cpu_count
from pathos.multiprocessing import ProcessingPool
import json

from .base_grapher import Base_Grapher

from ..attackers import Attacker
from ..managers import Bounded_Manager
# Done this way to avoid circular imports
from .. import ddos_simulator
from ..managers import KPO_Manager
from ..managers import Miad_Manager
from ..managers import Protag_Manager
from ..managers import Sieve_Manager_Base



class Worst_Case_Attacker:
    """placeholder

    Later used to graph the worst case attacker graph"""
    pass


class Combination_Grapher(Base_Grapher):
    """Compares managers against each other

    Plots total utility over all rounds on the Y axis
    Plots % of users that are attackers on the X axis
    """

    __slots__ = ["second_legend"]

    def run(self,
            managers=(Sieve_Manager_Base.runnable_managers +
                      [Protag_Manager, KPO_Manager, Bounded_Manager]), #+
                      #Miad_Manager.runnable_managers),
            attackers=Attacker.runnable_attackers,
            num_buckets_list=[10],
            users_per_bucket_list=[10 ** i for i in range(1, 2)],
            num_rounds_list=[10 ** i for i in range(1, 2)],
            trials=100):
        """Runs in parallel every possible scenario

        Looks complicated, but no real way to simplify it
        so deal with it"""

        # Initializes graph path
        self.make_graph_dir(destroy=True)

        # Total number of scenarios
        pbar_total = (len(num_buckets_list) *
                      len(users_per_bucket_list) *
                      len(num_rounds_list) *
                      len(attackers))

        _pathos_num_buckets_list = []
        _pathos_users_per_bucket = []
        _pathos_num_rounds = []
        for num_buckets in num_buckets_list:
            for users_per_bucket in users_per_bucket_list:
                for num_rounds in num_rounds_list:
                    for attacker in attackers + [Worst_Case_Attacker]:
                        self.get_attacker_graph_dir(attacker)

                    _pathos_num_buckets_list.append(num_buckets)
                    _pathos_users_per_bucket.append(users_per_bucket)
                    _pathos_num_rounds.append(num_rounds)

        p = ProcessingPool(nodes=cpu_count())
        total = len(_pathos_num_rounds)
        full_args = [[attackers] * total,
                     _pathos_num_buckets_list,
                     _pathos_users_per_bucket,
                     _pathos_num_rounds,
                     [managers] * total,
                     [trials] * total,
                     list(range(total)),
                     list([pbar_total] * total)]


        # https://stackoverflow.com/a/1987484/8903959
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            for i in range(total):
                try:
                    current_args = [x[i] for x in full_args]
                    self.get_graph_data(*current_args)
                except Exception as e:
                    print(current_args)
                    raise e
        else:
            p.map(self.get_graph_data, *full_args)
            p.close()
            p.join()
            p.clear()
        # Get rid of carriage returns
        print()

    def get_graph_data(self,
                       attackers,
                       num_buckets,
                       users_per_bucket,
                       num_rounds,
                       managers,
                       trials,
                       num,
                       total_num):
        """Gets data for graphing and graphs it"""

        scenario_data = {manager: {attacker: {"X": [],
                                              "Y": [],
                                              "YERR": []}
                                   for attacker in attackers}
                         for manager in managers}

        for attacker in attackers:
            self.print_progress(attacker, total_num)
            percent_attackers_list = [i / 100 for i in range(1, 50)]

            for manager in managers:
                manager_data = scenario_data[manager][attacker]
                for percent_attackers in percent_attackers_list:
                    manager_data["X"].append(percent_attackers)
                    Y = []
                    # TRIALS
                    for _ in range(trials):
                        # Get the utility for each trail and append it
                        Y.append(self.run_scenario(attacker,
                                                   num_buckets,
                                                   users_per_bucket,
                                                   num_rounds,
                                                   percent_attackers,
                                                   manager))
                    manager_data["Y"].append(mean(Y))
                    err_length = 1.645 * 2 * (sqrt(variance(Y))/sqrt(len(Y)))
                    manager_data["YERR"].append(err_length)

            self.graph_scenario(scenario_data,
                                num_buckets,
                                users_per_bucket,
                                num_rounds,
                                attacker)
         

        # Graphs worst case scenario
        worst_case_data = self.worst_case_data(managers,
                                               scenario_data,
                                               attackers)
        self.graph_scenario(worst_case_data,
                            num_buckets,
                            users_per_bucket,
                            num_rounds,
                            Worst_Case_Attacker,
                            write_json=True)

    def run_scenario(self,
                     attacker,
                     num_buckets,
                     users_per_bucket,
                     num_rounds,
                     percent_attackers,
                     manager):
        """Runs a trial for simulation"""

        # print("Running scenario!")
        users = num_buckets * users_per_bucket
        attackers = int(users * percent_attackers)
        good_users = users - attackers
        # No longer used, but maybe in the future
        threshold = 0
        simulator = ddos_simulator.DDOS_Simulator(good_users,
                                                  attackers,
                                                  num_buckets,
                                                  threshold,
                                                  [manager],
                                                  self.stream_level, 
                                                  attacker_cls=attacker)
        # dict of {manager: final utility}
        utilities_dict = simulator.run(num_rounds, graph_trials=False)
        return utilities_dict[manager]

    def worst_case_data(self, managers, scenario_data, attackers):
        """Creates a json of worst case attacker data"""

        # Create json of worst case attackers
        worst_case_scenario_data = {manager: {Worst_Case_Attacker: {"X": [],
                                                                    "Y": [],
                                                                    "YERR": [],
                                                                    "ATKS": []}
                                              }
                                    for manager in managers}
        for manager, manager_data in scenario_data.items():
            xs = manager_data[attackers[0]]["X"]
            for i, x in enumerate(xs):
                # should be changed to be abs max but whatevs
                min_utility = 100000000000000000000000
                worst_case_atk = None
                yerr = None
                for attacker in attackers:
                    if manager_data[attacker]["Y"][i] < min_utility:
                        min_utility = manager_data[attacker]["Y"][i]
                        worst_case_atk = attacker
                        yerr = manager_data[attacker]["YERR"][i]
                atk = Worst_Case_Attacker
                cur_data_point = worst_case_scenario_data[manager][atk]
                cur_data_point["X"].append(x)
                cur_data_point["Y"].append(min_utility)
                cur_data_point["YERR"].append(yerr)
                cur_data_point["ATKS"].append(worst_case_atk.__name__)

        return worst_case_scenario_data


    def graph_scenario(self,
                       scenario_data,
                       num_buckets,
                       users_per_bucket,
                       num_rounds,
                       attacker,
                       write_json=False):

        fig, axs, title = self._get_formatted_fig_axs(scenario_data,
                                                      num_buckets,
                                                      users_per_bucket,
                                                      num_rounds, attacker)

        for manager_i, manager in enumerate(scenario_data):
            self.populate_axs(axs,
                              scenario_data,
                              manager,
                              attacker,
                              manager_i,
                              write_json=write_json)

        self.add_legend(axs)

        graph_dir = self.get_attacker_graph_dir(attacker)
        graph_path = os.path.join(graph_dir, f"{title}.png")
        self.save_graph(os.path.join(graph_dir, f"{title}.png"), plt)

        if write_json:
            self.write_json(graph_path, scenario_data)

    def _get_formatted_fig_axs(self,
                               scenario_data,
                               num_buckets,
                               users_per_bucket,
                               num_rounds,
                               attacker):
        """Creates and formats axes"""

        fig, axs = plt.subplots(figsize=(20, 10))
        title = (f"Scenario: buckets: {num_buckets}, "
                 f"users: {users_per_bucket * num_buckets}, "
                 f"rounds: {num_rounds}, attacker_cls: {attacker.__name__}")
        fig.suptitle(title)

        # Gets maximum y value to set axis
        max_y_limit = 0
        for _, manager_data in scenario_data.items():
            if max(manager_data[attacker]["Y"]) > max_y_limit:
                max_y_limit = max(manager_data[attacker]["Y"])
        # Sets y limit
        axs.set_ylim(-1, max_y_limit + 5)
        # Add labels to axis
        axs.set(xlabel="Percent Attackers", ylabel="Utility")

        return fig, axs, title

    def get_attacker_graph_dir(self, attacker):
        """Returns attacker graph dir"""

        graph_dir = os.path.join(self.graph_dir, attacker.__name__)
        if not os.path.exists(graph_dir):
            os.makedirs(graph_dir)
        return graph_dir


    def print_progress(self, attacker, total_num):
        """Prints total number of files generated"""

        # https://stackoverflow.com/a/16910957/8903959
        cpt = sum([len(files) for r, d, files in os.walk(self.graph_dir)])
        print(f"Starting: {cpt + 1}/{total_num}", end="      \r")

    def populate_axs(self,
                     axs,
                     scenario_data,
                     manager,
                     attacker,
                     manager_i,
                     write_json=False):
        """Plots error bar"""

        axs.errorbar(scenario_data[manager][attacker]["X"],  # X val
                     scenario_data[manager][attacker]["Y"],  # Y value
                     yerr=scenario_data[manager][attacker]["YERR"],
                     label=f"{manager.__name__}",
                     ls=self.styles(manager_i),
                     # https://stackoverflow.com/a/26305286/8903959
                     marker="none" if write_json else self.markers(manager_i))
        # This means we are graphing worst case
        if write_json:
            # Get list of colors
            color_dict = self.get_worst_case_atk_color_dict()
            colors = [color_dict[atk_name] for atk_name in
                      scenario_data[manager][attacker]["ATKS"]]
            axs.scatter(scenario_data[manager][attacker]["X"],
                        scenario_data[manager][attacker]["Y"],
                        c=colors,
                        s=40,
                        zorder=3,
                        marker=self.markers(manager_i))

            legend_elements = [Line2D([0],
                                      [0],
                                      marker=self.markers(manager_i),
                                      color=color_dict[atk],
                                      label=atk,
                                      markerfacecolor=color_dict[atk],
                                      markersize=15)
                               for atk in set(scenario_data[manager][attacker]["ATKS"])]

            self.second_legend = legend_elements


    def get_worst_case_atk_color_dict(self):
        """Returns a dictionary of attacker to colors"""

        # https://matplotlib.org/3.1.1/gallery/color/named_colors.html
        colors = ["black", "dimgray", "lightcoral", "firebrick", "sienna",
                  "bisque", "gold", "olive", "lawngreen", "turquoise", "teal",
                  "deepskyblue", "midnightblue", "mediumpurple", "darkviolet",
                  "deeppink", "lightpink", "chocolate", "darkkhaki",
                  "powderblue"]

        
        new_colors_needed = len(Attacker.runnable_attackers) - len(colors)
        assert new_colors_needed <= 0, f"Add {new_colors_needed} more colors"
        return {attacker.__name__: colors[i]
                for i, attacker in enumerate(Attacker.runnable_attackers)}

    def add_legend(self, axs):
        """Adds legend. Potentially combine with grapher class"""

        # https://stackoverflow.com/a/4701285/8903959
        box = axs.get_position()
        axs.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        handles, labels = axs.get_legend_handles_labels()

        # Put a legend to the right of the current axis
        first = axs.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5))
        if hasattr(self, "second_legend"):
            # https://riptutorial.com/matplotlib/example/32429/multiple-legends-on-the-same-axes
            # https://matplotlib.org/3.1.1/gallery/text_labels_and_annotations/custom_legends.html
            axs.legend(handles=self.second_legend, loc='upper right', bbox_to_anchor=(1, 1))
            axs.add_artist(first)

    def write_json(self, graph_path, scenario_data):
        """Writes json file"""

        with open(graph_path.replace("png", "json"), "w") as f:
            data = {m.__name__: {atk.__name__: end_dict
                                 for atk, end_dict in m_data.items()}
                    for m, m_data in scenario_data.items()}
            json.dump(data, f)