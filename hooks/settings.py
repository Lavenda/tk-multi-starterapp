import sgtk

import datetime

HookBaseClass = sgtk.get_hook_baseclass()


class Settings(HookBaseClass):
    """
    Controls various review settings and formatting.
    """

    def get_title(self, context):
        """
        Returns the title that should be used for the version

        :param context: The context associated with the version.
        :returns: Version title string.
        """
        # rather than doing a version numbering scheme, which we
        # reserve for publishing workflows, the default implementation
        # uses a date and time based naming scheme
        task = context.task['name']
        return 'v{0}_{1}_review'.format('{version:0>3}', task)

    def get_timestamp(self, context):
        return datetime.datetime.now().strftime("%Y%m%d")
