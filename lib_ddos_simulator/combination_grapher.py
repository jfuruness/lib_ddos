#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the class Combination_Grapher to graph ddos simulations"""

__Lisence__ = "BSD"
__maintainer__ = "Justin Furuness, Anna Gorbenko"
__email__ = "jfuruness@gmail.com, agorbenko97@gmail.com"
__status__ = "Development"

import os

import matplotlib.pyplot as plt
import shutil
import logging
from statistics import mean, variance
from math import sqrt
from tqdm import tqdm

from .manager import Manager
from .sieve_manager import Sieve_Manager
from .protag_manager import Protag_Manager

from .kpo_manager import Kpo_Manager
from .miad_manager import Miad_Manager
from .bounded_manager import Bounded_Manager



from . import utils
from .ddos_simulator import DDOS_Simulator


class Combination_Grapher:

    __slots__ = ["stream_level", "graph_path"]

    def __init__(self, stream_level=logging.INFO, graph_path="/tmp/lib_ddos/"):
        utils.config_logging(stream_level)
        self.stream_level = stream_level
        self.graph_path = graph_path

    def run(self,
            managers=Sieve_Manager.runnable_managers[:1] + [Protag_Manager,
                                                            Kpo_Manager,
                                                            #Miad_Manager,
                                                            Bounded_Manager],
            num_buckets_list=[10],
            users_per_bucket_list=[10 ** i for i in range(1,2)],
            num_rounds_list=[10 ** i for i in range(1,2)]):

        for num_buckets in num_buckets_list:
            for users_per_bucket in users_per_bucket_list:
                for num_rounds in num_rounds_list:
                    self.get_graph_data(num_buckets,
                                        users_per_bucket,
                                        num_rounds,
                                        managers)

    def get_graph_data(self,
                       num_buckets,
                       users_per_bucket,
                       num_rounds,
                       managers):

        scenario_data = {manager: {"X": [],
                                   "Y": [],
                                   "YERR": []}
                         for manager in managers}
        trials = 100
        percent_attackers_list = [i / 100 for i in range(1,50)]

        with tqdm(total=len(managers) * len(percent_attackers_list) * trials,
                  desc="Running scenarios") as pbar:
            for manager in managers:
                manager_data = scenario_data[manager]
                for percent_attackers in percent_attackers_list:
                    manager_data["X"].append(percent_attackers)
                    Y = []
                    # TRIALS
                    for _ in range(trials):
                        # Get the utility for each trail and append it
                        Y.append(self.run_scenario(num_buckets,
                                                   users_per_bucket,
                                                   num_rounds,
                                                   percent_attackers,
                                                   manager))
                        pbar.update()
                    manager_data["Y"].append(mean(Y))
                    err_length = 1.645 * 2 * (sqrt(variance(Y))/sqrt(len(Y)))
                    manager_data["YERR"].append(err_length)
                                    

        self.graph_scenario(scenario_data,
                            num_buckets,
                            users_per_bucket,
                            num_rounds)

    def run_scenario(self,
                     num_buckets,
                     users_per_bucket,
                     num_rounds,
                     percent_attackers,
                     manager):

        users = num_buckets * users_per_bucket
        attackers = int(users * percent_attackers)
        good_users = users - attackers
        # No longer used, but maybe in the future
        threshold = 0
        simulator = DDOS_Simulator(good_users,
                                   attackers,
                                   num_buckets,
                                   threshold,
                                   [manager],
                                   self.stream_level,
                                   self.graph_path)
        # dict of {manager: final utility}
        utilities_dict =  simulator.run(num_rounds, graph_trials=False)
        return utilities_dict[manager]

    def graph_scenario(self, scenario_data, num_buckets, users_per_bucket, num_rounds):

        fig, axs, title = self._get_formatted_fig_axs(scenario_data,
                                                      num_buckets,
                                                      users_per_bucket,
                                                      num_rounds)

        for manager_index, manager in enumerate(scenario_data):
#            for x, y, yerr in zip(scenario_data[manager]["X"],
#                                  scenario_data[manager]["Y"],
#                                  scenario_data[manager]["YERR"]):
                
            axs.errorbar(scenario_data[manager]["X"],  # X val
                         scenario_data[manager]["Y"],  # Y value
                         yerr=scenario_data[manager]["YERR"],
                         label=manager.__name__,
                         ls=self.styles(manager_index),
                         marker=self.markers(manager_index))

        # https://stackoverflow.com/a/4701285/8903959
        box = axs.get_position()
        axs.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        handles, labels = axs.get_legend_handles_labels()

        # Put a legend to the right of the current axis
        axs.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5))
#        plt.show()
        plt.savefig(os.path.join(self.graph_path, f"{title}.png"))

        import tikzplotlib

#        tikzplotlib.save(os.path.join(self._path, "test.tex"))

    def styles(self, index):
        """returns styles and markers for graph lines"""

        styles = ["-", "--", "-.", ":", "solid", "dotted", "dashdot", "dashed"]
        return styles[index]

    def markers(self, index):

        markers = [".", "1", "*", "x", "d", "2", "3", "4"]
        return markers[index]

    def _get_formatted_fig_axs(self, scenario_data, num_buckets, users_per_bucket, num_rounds):
        """Creates and formats axes"""

        fig, axs = plt.subplots(figsize=(20,10))
        title = f"Scenario: buckets: {num_buckets}, users: {users_per_bucket * num_buckets}, rounds: {num_rounds}"
        fig.suptitle(title)
        for manager, manager_data in scenario_data.items():
            max_y_limit = 0
            if max(manager_data["Y"]) > max_y_limit:
                max_y_limit = max(manager_data["Y"])
        axs.set_ylim(-1, max_y_limit + (max_y_limit // 3))
        axs.set(xlabel="Percent Attackers", ylabel="Utility")

        return fig, axs, title