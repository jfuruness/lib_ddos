#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the class Animater to animate ddos simulations"""

__Lisence__ = "BSD"
__maintainer__ = "Justin Furuness"
__email__ = "jfuruness@gmail.com, agorbenko97@gmail.com"
__status__ = "Development"

from copy import deepcopy
import os

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import animation
import numpy as np
from tqdm import tqdm

from .base_grapher import Base_Grapher

from ..attackers import Attacker
from ..simulation_objects import Bucket, User
from ..managers import Manager, Sieve_Manager_Base


class Animater(Base_Grapher):
    """animates a DDOS attack"""

    slots__ = ["_data", "ax", "round", "max_users", "fig",
                 "name", "round_text", "frames_per_round",
                 "total_rounds", "manager", "ogbuckets", "ogusers"]

    def __init__(self, manager, **kwargs):
        """Initializes simulation"""

        super(Animater, self).__init__(**kwargs)
        assert self.tikz is False, "Can't save animation as tikz afaik"
        self.manager = manager
        self.ogbuckets = deepcopy(manager.buckets)
        self.max_users, self.fig, self.ax = self._format_graph()
        self.ogusers = deepcopy(manager.users)

        self._create_bucket_patches()
        self._create_user_patches()
        self.name = manager.__class__.__name__
        self.frames_per_round = 100
        self.total_rounds = 0
        #assert isinstance(manager, Sieve_Manager_Base), "Can't do that manager yet"

    @property
    def users(self):
        return self.manager.users + self.manager.eliminated_users

    @property
    def buckets(self):
        return self.manager.buckets

    def capture_data(self, manager: Manager):
        """Captures data for the round"""

        self.total_rounds += 1

        # add to the points array
        for bucket in manager.buckets:
            user_y = User.patch_padding
            for user in bucket.users:
                circle_y = User.patch_radius + user_y
                user.points.append((bucket.patch_center(), circle_y,))
                user.suspicions.append(user.suspicion)
                user_y = circle_y + User.patch_radius
                user_y += (User.patch_padding * 2)

        for user in manager.eliminated_users:
            user.points.append((-10, -10,))
            user.suspicions.append(0)


    def run_animation(self, total_rounds):
        """Graphs data

        Saves all data to an mp4 file. Note, you can increase or
        decrease total number of frames in this function"""

        frames = total_rounds * self.frames_per_round
        anim = animation.FuncAnimation(self.fig, self.animate,
                                       init_func=self.init,
                                       frames=frames,
                                       interval=40,
                                       blit=True)

        self.save_graph(anim)


    def save_graph(self, anim):
        """Saves animation, overwrites Base_Grapher method"""

        # self.save is an attr of Base_Grapher
        if self.save:

            pbar = tqdm(desc="Saving video",
                        total=self.frames_per_round * (self.total_rounds - 1))
            # Callback function for saving animation
            def callback(current_frame_number, total_frames):
                pbar.update()

            # graph_dir comes from inherited class
            path = os.path.join(self.graph_dir, f'{self.name}_animation.mp4')

            anim.save(path, progress_callback=callback)
            pbar.close()
        else:
            plt.show()

    def _format_graph(self):
        """Formats graph properly

        Basically makes graph colorful"""

        if self.save:
            matplotlib.use("Agg")
        plt.style.use('dark_background')
        # https://stackoverflow.com/a/48958260/8903959
        matplotlib.rcParams.update({'text.color': "black"})

        fig = plt.figure()
        # This could also be changed for higher resolution
        fig.set_dpi(100)
        fig.set_size_inches(50, 50)

        max_users = max([len(x) for x in self.buckets])

        ax = plt.axes(xlim=(0, len(self.buckets) * Bucket.patch_length()),
                      ylim=(0, max_users * User.patch_length() * 3 + 1))
        ax.set_axis_off()

        gradient_image(ax,
                       direction=0,
                       extent=(0, 1, 0, 1),
                       transform=ax.transAxes,
                       cmap=plt.cm.Oranges,
                       cmap_range=(0.1, 0.6))

        return max_users, fig, ax

    def _create_bucket_patches(self):
        """Creates patches of users and buckets"""

        self.bucket_patches = []
        x = Bucket.patch_padding
        for bucket in self.buckets:
            bucket.patch = FancyBboxPatch((x, 0),
                                          Bucket.patch_width,
                                          self.max_users * User.patch_length() * 3,
                                          boxstyle="round,pad=0.1",
                                          fc="b")
            bucket.patch.set_boxstyle("round,pad=0.1, rounding_size=0.5")
            x += Bucket.patch_length()
            self.bucket_patches.append(bucket.patch)

    def _create_user_patches(self):
        """Creates patches of users"""

        self.user_patches = []
        for bucket in self.buckets:
            for user in bucket.users:
                fc = "r" if isinstance(user, Attacker) else "g"
                user.patch = plt.Circle((bucket.patch_center(), 5),
                                        User.patch_radius,
                                        fc=fc)
                if isinstance(user, Attacker):
                    user.horns = plt.Polygon(0 * self.get_horn_array(user),
                                             fc="r",
                                             **dict(ec="k"))

                user.text = plt.text(bucket.patch_center() - .5,
                                     5,
                                     f"{user.id}:0")
                self.user_patches.append(user.patch)

    def init(self):
        """inits the animation

        Sets z order: bucket->horns->attacker/user->text"""

        for bucket in self.buckets:
            self.ax.add_patch(bucket.patch)
            bucket.patch.set_zorder(1)
        for user in self.users:
            user.patch.center = user.points[0]

            self.ax.add_patch(user.patch)
            user.patch.set_zorder(3)
            if isinstance(user, Attacker):
                user.horns.set_zorder(2)
                self.ax.add_patch(user.horns)
                user.horns.set_xy(self.get_horn_array(user))
            user.text.set_y(user.points[0][1])
            user.text.set_zorder(4)


        self.round_text = plt.text(self.ax.get_xlim()[1] * .37,
                                   self.ax.get_ylim()[1] - .5,
                                   f"{self.name}: Round 0")
        horns = [x.horns for x in self.users if isinstance(x, Attacker)]
        objs = [x.patch for x in self.users] + [x.text for x in self.users]
        objs += [self.round_text] + horns

        return objs

    def animate(self, i):
        """Animates the frame

        moves all objects partway to the next point. Basically,
        determines the final destination, and moves 1/frames_per_round
        of the way there. It only moves users, and so must move horns
        and text of the user as well
        """

        #input("start of animate")
        for user in self.users:
            current_point = user.points[i // self.frames_per_round]
            future_point = user.points[(i // self.frames_per_round) + 1]

            remainder = i - ((i // self.frames_per_round)
                             * self.frames_per_round)
            next_point_x1_contr = current_point[0] * (
                (self.frames_per_round - remainder) / self.frames_per_round)
            next_point_x2_contr = future_point[0] * (
                remainder / self.frames_per_round)
            next_point_y1_contr = current_point[1] * (
                (self.frames_per_round - remainder) / self.frames_per_round)
            next_point_y2_contr = future_point[1] * (
                remainder / self.frames_per_round)
            next_point = (next_point_x1_contr + next_point_x2_contr,
                          next_point_y1_contr + next_point_y2_contr)
            user.patch.center = next_point
            if isinstance(user, Attacker):
                user.horns.set_xy(self.get_horn_array(user))
            user.text.set_x(next_point[0] - .7)
            user.text.set_y(next_point[1] - .2)
            text = f"{user.suspicions[i//self.frames_per_round]:.1f}"
            user.text.set_text(f"{user.id:2.0f}:{text}")
        self.round_text.set_visible(False)
        self.round_text.remove()
        # This is why it works best with that sizing
        self.round_text = plt.text(self.ax.get_xlim()[1] * .37,
                                   self.ax.get_ylim()[1] - .5,
                                   (f"{self.name}: "
                                    f"Round {i // self.frames_per_round}"),
                                   bbox=dict(facecolor='white', alpha=1))
        horns = [x.horns for x in self.users if isinstance(x, Attacker)]
        objs = [x.patch for x in self.users] + [x.text for x in self.users]
        objs += [self.round_text] + horns
        #input("End of animate")
        return objs

    def get_horn_array(self, user):
        """Returns the horn array for the attackers"""

        horn_array = np.array(
                        [user.patch.center,
                         [user.patch.center[0] - User.patch_radius,
                          user.patch.center[1]],
                         [user.patch.center[0] - User.patch_radius,
                          user.patch.center[1] + User.patch_radius],
                         user.patch.center,
                         [user.patch.center[0] + User.patch_radius,
                          user.patch.center[1]],
                         [user.patch.center[0] + User.patch_radius,
                          user.patch.center[1] + User.patch_radius],
                         user.patch.center
                         ])
        return horn_array


# Basically just makes the colors pretty
# https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/gradient_bar.html
def gradient_image(ax, extent, direction=0.3, cmap_range=(0, 1), **kwargs):
    """
    Draw a gradient image based on a colormap.

    Parameters
    ----------
    ax : Axes
        The axes to draw on.
    extent
        The extent of the image as (xmin, xmax, ymin, ymax).
        By default, this is in Axes coordinates but may be
        changed using the *transform* kwarg.
    direction : float
        The direction of the gradient. This is a number in
        range 0 (=vertical) to 1 (=horizontal).
    cmap_range : float, float
        The fraction (cmin, cmax) of the colormap that should be
        used for the gradient, where the complete colormap is (0, 1).
    **kwargs
        Other parameters are passed on to `.Axes.imshow()`.
        In particular useful is *cmap*.
    """

    np.random.seed(19680801)
    phi = direction * np.pi / 2
    v = np.array([np.cos(phi), np.sin(phi)])
    X = np.array([[v @ [1, 0], v @ [1, 1]],
                  [v @ [0, 0], v @ [0, 1]]])
    a, b = cmap_range
    X = a + (b - a) / X.max() * X
    im = ax.imshow(X, extent=extent, interpolation='bicubic',
                   vmin=0, vmax=1, **kwargs)
    return im