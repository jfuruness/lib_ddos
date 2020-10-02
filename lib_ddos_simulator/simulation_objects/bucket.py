#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the class Bucket, for service bucket in sim"""

__Lisence__ = "BSD"
__maintainer__ = "Justin Furuness"
__email__ = "jfuruness@gmail.com, agorbenko97@gmail.com"
__status__ = "Development"

from .user import User


class Bucket:
    """Simulates a Bucket that provides service for users"""

    # patch used in animations
    __slots__ = ["users", "_max_users", "attacked", "patch",
                 "turns_not_attacked"]

    # Used in animations
    patch_width = User.patch_length()
    patch_padding = .5

    def __init__(self, users: list = [], max_users=100000000, attacked=False):
        """Stores users"""

        assert len(users) < max_users, "Too many users, over max_users"

        self.users = users
        for user in users:
            user.bucket = self
        self._max_users = max_users
        self.attacked = attacked
        self.turns_not_attacked = 0

    def reinit(self, users, max_users=100000000, attacked=False):
        """inits with patch"""

        patch = None
        if hasattr(self, "patch"):
            patch = self.patch
        #self.__init__(users, max_users=max_users, attacked=attacked)
        self.users = users
        for user in self.users:
            user.bucket = self
        self._max_users = max_users
        self.attacked = attacked
        
        self.patch = patch

    def __str__(self):
        """Returns users inside of bucket"""

        return str(self.users)

    def __len__(self):
        """Number of users in bucket"""

        return len(self.users)

    def add_user(self, user):
        """Adds user if not over _max_users, returns True, else False"""

        if len(self.users) > self._max_users:
            assert False, "Not yet implimented"
            return False
        else:
            self.users.append(user)
            return True

    def update_suspicion(self):
        """Updates suspicion level of all users in bucket"""

        multiplier = int(self.attacked)
        for user in self.users:
            user.suspicion += (1 / len(self.users)) * multiplier

    @staticmethod
    def patch_length():
        """Animation object length"""

        return Bucket.patch_width + Bucket.patch_padding * 2

    def patch_center(self):
        """Gets the center of the animation object for moving"""

        return self.patch.get_x() + self.patch.get_width() / 2
