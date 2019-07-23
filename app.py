# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.


import os
from sgtk.platform import Application


class UploadToReview(Application):
    """
    The app entry point. This class is responsible for intializing and tearing down
    the application, handle menu registration etc.
    """

    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed.
        """
        return True

    @property
    def base_hooks(self):
        """
        Exposes the ``base_hooks`` module.

        This module provides base class implementations hooks.

        Access to these classes won't typically be needed when writing hooks as
        they are are injected into the class hierarchy automatically for any
        collector or publish plugins configured.

        :return: A handle on the app's ``base_hooks`` module.
        """
        return self._base_hooks

    def init_app(self):
        """
        Called as the application is being initialized
        """

        # first, we use the special import_module command to access the app module
        # that resides inside the python folder in the app. This is where the actual UI
        # and business logic of the app is kept. By using the import_module command,
        # toolkit's code reload mechanism will work properly.
        # app_payload = self.import_module("tk-multi-uploadtoreview")

        # # now register a *command*, which is normally a menu entry of some kind on a Shotgun
        # # menu (but it depends on the engine). The engine will manage this command and
        # # whenever the user requests the command, it will call out to the callback.

        # # first, set up our callback, calling out to a method inside the app module contained
        # # in the python folder of the app
        # menu_callback = lambda : app_payload.dialog.show_dialog(self)

        # # now register the command with the engine
        # self.engine.register_command("Show Starter Template App...", menu_callback)

        tk_multi_uploadtoreview = self.import_module("tk_multi_uploadtoreview")
        self._base_hooks = tk_multi_uploadtoreview.base_hooks

        # add to nuke node menu
        icon = os.path.join(self.disk_location, "resources", "node_icon.png")

        self.engine.register_command(
            "Upload to Review",
            self.show_app,
            {"type": "node", "icon": icon}
        )

    def show_app(self):
        tk_multi_uploadtoreview = self.import_module("tk_multi_uploadtoreview")
        self.engine.show_dialog(
            "Upload to Review",
            self,
            tk_multi_uploadtoreview.Dialog,
        )
