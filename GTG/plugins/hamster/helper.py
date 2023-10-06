import re

from gi.repository import GLib, Gio


class FactBuilder():
    """ Hamster time tracker fact builder """
    def __init__(self, hamster, preferences):
        self.hamster = hamster
        self.preferences = preferences

    def build(self, task):
        """
        return hamster fact
        """
        title = self._build_activity_title(task)
        category = self._build_category(task)
        description = self._build_description(task)
        tags = self._build_tags(task)
        return f"{title}{category},, {description},{tags}"

    def _build_activity_title(self, task):
        gtg_tags = set(self._get_gtg_tags(task))
        activity = "Other"
        if self.preferences['activity'] == 'tag':
            hamster_activities = {
                str(x[0]).lower()
                for x in self.hamster.GetActivities('(s)', '')
            }
            activity_candidates = hamster_activities.intersection(gtg_tags)
            if len(activity_candidates) >= 1:
                activity = list(activity_candidates)[0]
        elif self.preferences['activity'] == 'title':
            activity = task.get_title()
        # hamster can't handle ',' or '@' in activity name
        activity = activity.replace(',', '')
        activity = re.sub(' +@.*', '', activity)
        return activity

    def _build_category(self, task):
        gtg_title = task.get_title()
        gtg_tags = self._get_gtg_tags(task)

        category = ""
        if self.preferences['category'] == 'auto_tag':
            hamster_activities = {
                str(activity[0]): activity[1]
                for activity in self.hamster.GetActivities('(s)', '')
            }
            if gtg_title in hamster_activities or \
                    gtg_title.replace(",", "") in hamster_activities:
                category = f"{hamster_activities[gtg_title]}"

        if self.preferences['category'] == 'tag' or \
                (self.preferences['category'] == 'auto_tag' and not category):
            # See if any of the tags match existing categories
            categories = dict([(str(x[1]).lower(), str(x[1]))
                               for x in self.hamster.GetCategories()])
            intersection = set(categories.keys()).intersection(set(gtg_tags))
            if len(intersection) > 0:
                category = f"{categories[intersection.pop()]}"
            elif len(gtg_tags) > 0:
                # Force category if not found
                category = gtg_tags[0]
        return f"@{category}" if category else ""

    def _build_description(self, task):
        description = ""
        if self.preferences['description'] == 'title':
            description = task.get_title()
        elif self.preferences['description'] == 'contents':
            description = task.get_excerpt(strip_tags=True,
                                           strip_subtasks=True)
        return description

    def _build_tags(self, task):
        gtg_tags = self._get_gtg_tags(task)
        tag_candidates = []
        try:
            if self.preferences['tags'] == 'existing':
                hamster_tags = {str(x[1]) for x in self.hamster.GetTags('(b)', False)}
                tag_candidates = list(hamster_tags.intersection(set(gtg_tags)))
            elif self.preferences['tags'] == 'all':
                tag_candidates = gtg_tags
        except GLib.Error as e:
            if e.matches(Gio.DBusError.quark(),
                         Gio.DBusError.UNKNOWN_METHOD):
                pass # old hamster version, doesn't support tags
            else:
                raise e
        tag_str = "".join([" #" + x for x in tag_candidates])
        return tag_str

    @staticmethod
    def _get_gtg_tags(task):
        return [
            tag_name.lstrip('@').lower() for tag_name in task.get_tags_name()
        ]
