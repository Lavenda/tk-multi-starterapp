import shutil
import os
import sgtk
import datetime
from sgtk.platform.qt import QtCore, QtGui

from .ui.dialog import Ui_Dialog

logger = sgtk.platform.get_logger(__name__)

overlay = sgtk.platform.import_framework("tk-framework-qtwidgets", "overlay_widget")
sg_data = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_data")
task_manager = sgtk.platform.import_framework("tk-framework-shotgunutils", "task_manager")


class Dialog(QtGui.QWidget):
    """
    Main dialog window for the App
    """

    (DATA_ENTRY_UI, UPLOAD_COMPLETE_UI) = range(2)

    def __init__(self, parent=None):
        """
        :param nuke_review_node: Selected nuke gizmo to render.
        :param parent: The parent QWidget for this control
        """
        QtGui.QWidget.__init__(self, parent)

        self._bundle = sgtk.platform.current_bundle()
        # self._group_node = nuke_review_node

        self._context = self._bundle.context
        self._title = self._generate_title()

        self._task_manager = task_manager.BackgroundTaskManager(
            parent=self,
            start_processing=True,
            max_threads=2
        )

        # set up data retriever
        self.__sg_data = sg_data.ShotgunDataRetriever(
            self,
            bg_task_manager=self._task_manager
        )
        self.__sg_data.work_completed.connect(self.__on_worker_signal)
        self.__sg_data.work_failure.connect(self.__on_worker_failure)
        self.__sg_data.start()

        # set up the UI
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.context_widget.set_up(self._task_manager)
        self.ui.context_widget.set_context(self._context)
        self.ui.context_widget.context_label.hide()
        self.ui.context_widget.restrict_entity_types_by_link("Version", "entity")

        self.ui.context_widget.context_changed.connect(self._on_context_change)

        self._overlay = overlay.ShotgunOverlayWidget(self)
        self.ui.submit.clicked.connect(self._submit)
        self.ui.cancel.clicked.connect(self.close)
        self.ui.browse_button.released.connect(self.browse)

        # set up basic UI
        self.ui.version_name.setText(self._title)
        # self.ui.start_frame.setText(str(self._get_first_frame()))
        # self.ui.end_frame.setText(str(self._get_last_frame()))

        self._setup_playlist_dropdown()

    def _setup_playlist_dropdown(self):
        """
        Sets up the playlist dropdown widget
        """
        self.ui.playlists.setToolTip(
            "<p>Shows the 10 most recently updated playlists for "
            "the project that have a viewing date "
            "set to the future.</p>"
        )

        self.ui.playlists.addItem("Add to playlist", 0)

        from tank_vendor.shotgun_api3.lib.sgtimezone import LocalTimezone
        datetime_now = datetime.datetime.now(LocalTimezone())

        playlists = self._bundle.shotgun.find(
            "Playlist",
            [
                ["project", "is", self._bundle.context.project],
                {
                    "filter_operator": "any",
                    "filters": [
                        ["sg_date_and_time", "greater_than", datetime_now],
                        ["sg_date_and_time", "is", None]
                    ]
                }
            ],
            ["code", "id", "sg_date_and_time"],
            order=[{"field_name": "updated_at", "direction": "desc"}],
            limit=10,
        )

        for playlist in playlists:

            if playlist.get("sg_date_and_time"):
                # 'Add to playlist dailies (Today 12:00)'
                caption = "%s (%s)" % (
                    playlist["code"],
                    self._format_timestamp(playlist["sg_date_and_time"])
                )
            else:
                caption = playlist["code"]

            self.ui.playlists.addItem(caption, playlist["id"])

    def _format_timestamp(self, datetime_obj):
        """
        Formats the given datetime object in a short human readable form.

        :param datetime_obj: Datetime obj to format
        :returns: date str
        """
        from tank_vendor.shotgun_api3.lib.sgtimezone import LocalTimezone
        datetime_now = datetime.datetime.now(LocalTimezone())

        datetime_tomorrow = datetime_now + datetime.timedelta(hours=24)

        if datetime_obj.date() == datetime_now.date():
            # today - display timestamp - Today 01:37AM
            return datetime_obj.strftime("Today %I:%M%p")

        elif datetime_obj.date() == datetime_tomorrow.date():
            # tomorrow - display timestamp - Tomorrow 01:37AM
            return datetime_obj.strftime("Tomorrow %I:%M%p")

        else:
            # 24 June 01:37AM
            return datetime_obj.strftime("%d %b %I:%M%p")

    def closeEvent(self, event):
        """
        Executed when the dialog is closed.
        """
        try:
            self.ui.context_widget.save_recent_contexts()
            self.__sg_data.stop()
            self._task_manager.shut_down()
        except Exception:
            logger.exception("Error running Loader App closeEvent()")

        # okay to close dialog
        event.accept()

    def _generate_title(self):
        """
        Create a title for the version
        """
        return self._bundle.execute_hook_method(
            "settings_hook",
            "get_title",
            context=self._context,
            base_class=self._bundle.base_hooks.ReviewSettings
        )

    def _generate_timestamp(self):
        return self._bundle.execute_hook_method(
            "settings_hook",
            "get_timestamp",
            context=self._context,
            base_class=self._bundle.base_hooks.ReviewSettings
        )

    def _navigate_panel_and_close(self, panel_app, version_id):
        """
        Navigates to the given version in the given panel app
        and then closes this window.

        :param panel_app: Panel app instance to navigate.
        :prarm int version_id: Version id to navigate to
        """
        self.close()
        panel_app.navigate("Version", version_id, panel_app.PANEL)

    def _navigate_sg_and_close(self, version_id):
        """
        Navigates to the given version in shotgun and closes
        the window.

        :prarm int version_id: Version id to navigate to
        """
        self.close()
        # open sg media center playback overlay page
        url = "%s/page/media_center?type=Version&id=%d" % (
            self._bundle.sgtk.shotgun.base_url,
            version_id
        )
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _on_context_change(self, context):
        """
        Called when user selects a new context

        :param context: Context which was selected
        """
        logger.debug("Setting version context to %s" % context)
        self._context = context
        self._title = self._generate_title()
        self.ui.version_name.setText(self._title)

    def browse(self):
        root = self.ui.browse_lineedit.text()
        fileDialog = QtGui.QFileDialog(self)
        fileDialog.setDirectory(root.split(',')[0])
        fileDialog.setFileMode(QtGui.QFileDialog.ExistingFiles)
        fileExtsPattern = ' '.join(['*.{0}'.format(ext) for ext in ['mov']])
        filterPattern = 'Files ({0})'.format(fileExtsPattern)
        fileDialog.setNameFilter(self.tr(filterPattern))

        if fileDialog.exec_():
            filePaths = fileDialog.selectedFiles()
            filePath = filePaths[0]
            self.ui.browse_lineedit.setText(filePath)

        return filePath

    def _submit(self):
        """
        Submits the render for review.
        """
        try:
            self._overlay.start_spin()
            self._version_id = self._run_submission()
        except Exception, e:
            logger.exception("An exception was raised.")
            self._overlay.show_error_message("An error was reported: %s" % e)

    def _upload_to_shotgun(self, shotgun, data):
        """
        Upload quicktime to Shotgun.

        :param shotgun: Shotgun API instance
        :param: parameter dictionary
        """
        logger.debug("Uploading movie to Shotgun...")
        try:
            shotgun.upload(
                "Version",
                data["version_id"],
                data["file_name"],
                "sg_uploaded_movie"
            )
            logger.debug("...Upload complete!")
        finally:
            sgtk.util.filesystem.safe_delete_file(data["file_name"])

    def _run_submission(self):
        """
        Carry out the render and upload.
        """
        # get inputs - these come back as unicode so make sure convert to utf-8
        version_name = self.ui.version_name.text()
        if isinstance(version_name, unicode):
            version_name = version_name.encode("utf-8")

        description = self.ui.description.toPlainText()
        if isinstance(description, unicode):
            description = description.encode("utf-8")

        # copy review path
        src_path = self.ui.browse_lineedit.text()
        fields = {
            'Step': self._context.step['name'],
            'Task': self._context.task['name'],
            'timestamp': self._generate_timestamp()
        }

        if self._context.entity['type'] == 'Shot':
            shotFilter = [('id', 'is', self._context.entity['id'])]
            shot = self._bundle.shotgun.find_one('Shot', shotFilter, fields=['sg_sequence'])
            entityFields = {
                'Sequence': shot['sg_sequence']['name'],
                'Shot': self._context.entity['name'],
            }
            template = self._bundle.engine.sgtk.templates['shot_review_mov_publish']
        else:
            assetFilter = [('id', 'is', self._context.entity['id'])]
            asset = self._bundle.shotgun.find_one('Asset', assetFilter, fields=['sg_asset_type'])
            entityFields = {
                'Asset_Type': asset['sg_asset_type'],
                'Asset': self._context.entity['name'],
            }
            template = self._bundle.engine.sgtk.templates['asset_review_mov_publish']

        fields.update(entityFields)
        dst_path, fields = self.getNextPublishPath(template, fields)
        dst_dir = os.path.dirname(dst_path)
        if not os.path.isdir(dst_dir):
            os.makedirs(dst_dir)
        shutil.copy(src_path, dst_path)

        # create sg version
        data = {
            "code": version_name.format(version=fields['version']),
            "description": description,
            "project": self._context.project,
            "entity": self._context.entity,
            "sg_task": self._context.task,
            "created_by": sgtk.util.get_current_user(self._bundle.sgtk),
            "user": sgtk.util.get_current_user(self._bundle.sgtk),
            "sg_path_to_movie": dst_path
            # "sg_movie_has_slate": True
        }

        if self.ui.playlists.itemData(self.ui.playlists.currentIndex()) != 0:
            data["playlists"] = [{
                "type": "Playlist",
                "id": self.ui.playlists.itemData(self.ui.playlists.currentIndex())
            }]

        # call pre-hook
        data = self._bundle.execute_hook_method(
            "events_hook",
            "before_version_creation",
            sg_version_data=data,
            base_class=self._bundle.base_hooks.ReviewEvents
        )

        # create in shotgun
        entity = self._bundle.shotgun.create("Version", data)
        logger.debug("Version created in Shotgun %s" % entity)

        # call post hook
        self._bundle.execute_hook_method(
            "events_hook",
            "after_version_creation",
            sg_version_id=entity["id"],
            base_class=self._bundle.base_hooks.ReviewEvents
        )

        data = {"version_id": entity["id"], "file_name": dst_path}
        self.__sg_data.execute_method(self._upload_to_shotgun, data)

        return entity["id"]

    def getNextPublishPath(self, publishTemplate, fields):
        publishPath = ''
        fields['version'] = 0
        _version = 1000

        while _version > 1:
            fields['version'] = _version - 1
            publishPath = publishTemplate.apply_fields(fields)

            if os.path.exists(publishPath):
                break

            _version = fields['version']

        fields['version'] = _version
        publishPath = publishTemplate.apply_fields(fields)
        return publishPath, fields

    def __on_worker_failure(self, uid, msg):
        """
        Asynchronous callback - the worker thread errored.
        """
        self._overlay.show_error_message("An error was reported: %s" % msg)
        self.ui.submit.hide()
        self.ui.cancel.setText("Close")

    def __on_worker_signal(self, uid, request_type, data):
        """
        Signaled whenever the worker completes something.
        """
        # call post hook - note that we don't do this in
        # the thread because calls to the nuke API sometimes
        # crash when executed from a thread, so for maximum
        # safety and stability, call post hook from main thread.
        self._bundle.execute_hook_method(
            "events_hook",
            "after_upload",
            sg_version_id=self._version_id,
            base_class=self._bundle.base_hooks.ReviewEvents
        )

        # hide spinner
        self._overlay.hide()

        # show success screen
        self.ui.stack_widget.setCurrentIndex(self.UPLOAD_COMPLETE_UI)

        # show 'jump to panel' button if we have panel loaded
        found_panel = False
        for app in self._bundle.engine.apps.values():
            if app.name == "tk-multi-shotgunpanel":
                # panel is loaded
                launch_panel_fn = lambda panel_app=app: self._navigate_panel_and_close(
                    panel_app,
                    self._version_id
                )
                self.ui.jump_to_panel.clicked.connect(launch_panel_fn)
                found_panel = True

        if not found_panel:
            # no panel, so hide button
            self.ui.jump_to_panel.hide()

        # always show 'jump to sg' button
        launch_sg_fn = lambda: self._navigate_sg_and_close(
            self._version_id
        )
        self.ui.jump_to_shotgun.clicked.connect(launch_sg_fn)

        # hide submit button, turn cancel button into a close button
        self.ui.submit.hide()
        self.ui.cancel.setText("Close")