#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the class Animater to animate ddos simulations"""

__Lisence__ = "BSD"
__maintainer__ = "Justin Furuness, Anna Gorbenko"
__email__ = "jfuruness@gmail.com, agorbenko97@gmail.com"
__status__ = "Development"

import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import animation
import shutil

from .attacker import Attacker
from .bucket import Bucket
from .manager import Manager
from .sieve_manager import Sieve_Manager
from .user import User

class Animater:
    """animates a DDOS attack"""

    __slots__ = ["_data", "ax", "buckets", "round", "max_users", "fig", "users", "name", "round_text"]
  
    def __init__(self, manager):
        """Initializes simulation"""


        self.buckets = manager.buckets
        self.max_users, self.fig, self.ax = self._format_graph()
        self.users = manager.users
        self._create_bucket_patches()
        self._create_user_patches()
        self.name = manager.__class__.__name__
        assert isinstance(manager, Sieve_Manager), "Can't do that manager yet"

    def capture_data(self, manager: Manager):
        """Captures data for the round"""

        # add to the points array
        for bucket in manager.buckets:
            user_y = User.patch_padding
            for user in bucket.users:
                circle_y = User.patch_radius + user_y
                user.points.append((bucket.patch_center(), circle_y,))
                user.suspicions.append(user.suspicion)
                user_y = circle_y + User.patch_radius + (User.patch_padding * 2)

    def run_animation(self, total_rounds):
        """Graphs data"""

        anim = animation.FuncAnimation(self.fig, self.animate,
                                       init_func=self.init,
                                       frames=total_rounds * 100,
                                       interval=40,
                                       blit=True)
        anim.save('animation.mp4', progress_callback=lambda i, n: print(f'Saving frame {i} of {n}'))
#       must use agg
#        plt.show()

    def _format_graph(self):
        """Formats graph properly"""

        plt.style.use('dark_background')
        # https://stackoverflow.com/a/48958260/8903959
        matplotlib.rcParams.update({'text.color' : "black"})

        fig = plt.figure()
        fig.set_dpi(100)
        fig.set_size_inches(12, 5)

        max_users = max([len(x) for x in self.buckets])

        ax = plt.axes(xlim=(0, len(self.buckets) * Bucket.patch_length()),
                      ylim=(0, max_users * User.patch_length() + 1))
        ax.set_axis_off()

        gradient_image(ax, direction=0, extent=(0, 1, 0, 1), transform=ax.transAxes,
                       cmap=plt.cm.Oranges, cmap_range=(0.1, 0.6))


        return max_users, fig, ax

    def _create_bucket_patches(self):
        """Creates patches of users and buckets"""

        x = Bucket.patch_padding
        for bucket in self.buckets:
            bucket.patch = FancyBboxPatch((x, 0),
                                          Bucket.patch_width,
                                          self.max_users * User.patch_length(),
                                          boxstyle="round,pad=0.1",
                                          fc="b")
            bucket.patch.set_boxstyle("round,pad=0.1, rounding_size=0.5")
            x += Bucket.patch_length()

    def _create_user_patches(self):
        """Creates patches of users"""

        for bucket in self.buckets:
            for user in bucket.users:
                fc = "r" if isinstance(user, Attacker) else "g"
                user.patch = plt.Circle((bucket.patch_center(), 5),
                                        User.patch_radius,
                                        fc=fc)
                if isinstance(user, Attacker):
                    user.horns = plt.Polygon(0 * self.get_horn_array(user), fc="r", **dict(ec="k"))

                user.text = plt.text(bucket.patch_center() - .5,
                                     5,
                                     f"{user.id}:0")

    def init(self):
        """inits the animation"""

        for bucket in self.buckets:
            self.ax.add_patch(bucket.patch)
            bucket.patch.set_zorder(1)
            for user in bucket.users:
                user.patch.center = user.points[0]
                user.patch.set_zorder(3)
                self.ax.add_patch(user.patch)
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
        return [x.patch for x in self.users] + [x.text for x in self.users] + [self.round_text] + horns

    def animate(self, i):
        for user in self.users:
            current_point = user.points[i // 100]
            future_point = user.points[(i // 100) + 1]

            remainder = i - ((i // 100) * 100)
            next_point_x1_contr = current_point[0] * ((100 - remainder) / 100)
            next_point_x2_contr = future_point[0] * (remainder / 100)
            next_point_y1_contr = current_point[1] * ((100 - remainder) / 100)
            next_point_y2_contr = future_point[1] * (remainder / 100)
            next_point = (next_point_x1_contr + next_point_x2_contr,
                          next_point_y1_contr + next_point_y2_contr)
            user.patch.center = next_point
            if isinstance(user, Attacker):
                user.horns.set_xy(self.get_horn_array(user))
            user.text.set_x(next_point[0] - .7)
            user.text.set_y(next_point[1] - .2)
            user.text.set_text(f"{user.id:2.0f}:{user.suspicions[i//100]:.1f}")
        self.round_text.set_visible(False)
        self.round_text.remove()
        self.round_text = plt.text(self.ax.get_xlim()[1] * .37,
                                   self.ax.get_ylim()[1] - .5,
                                   f"{self.name}: Round {i // 100}",
                                   bbox=dict(facecolor='white', alpha=1))
        horns = [x.horns for x in self.users if isinstance(x, Attacker)]
        return [x.patch for x in self.users] + [x.text for x in self.users] + [self.round_text] + horns

    def get_horn_array(self, user):
        horn_array = np.array(
                        [user.patch.center,
                         [user.patch.center[0] - User.patch_radius, user.patch.center[1]],
                         [user.patch.center[0] - User.patch_radius, user.patch.center[1] + User.patch_radius],
                         user.patch.center,
                         [user.patch.center[0] + User.patch_radius, user.patch.center[1]], 
                         [user.patch.center[0] + User.patch_radius, user.patch.center[1] + User.patch_radius],
                         user.patch.center
                        ])
        return horn_array


# https://matplotlib.org/3.1.0/gallery/lines_bars_and_markers/gradient_bar.html
import numpy as np

np.random.seed(19680801)


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
    phi = direction * np.pi / 2
    v = np.array([np.cos(phi), np.sin(phi)])
    X = np.array([[v @ [1, 0], v @ [1, 1]],
                  [v @ [0, 0], v @ [0, 1]]])
    a, b = cmap_range
    X = a + (b - a) / X.max() * X
    im = ax.imshow(X, extent=extent, interpolation='bicubic',
                   vmin=0, vmax=1, **kwargs)
    return im
