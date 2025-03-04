"""
Base setup for Notification Apps and Types.
"""
from .utils import (
    find_app_in_normalized_apps,
    find_pref_in_normalized_prefs,
)


COURSE_NOTIFICATION_TYPES = {
    'new_comment_on_response': {
        'notification_app': 'discussion',
        'name': 'new_comment_on_response',
        'is_core': True,
        'info': 'Comment on response',
        'content_template': '<p><strong>{replier_name}</strong> replied on your response in '
                            '<strong>{post_title}</strong></p>',
        'content_context': {
            'post_title': 'Post title',
            'replier_name': 'replier name',
        },
        'email_template': '',
    },
    'new_comment': {
        'notification_app': 'discussion',
        'name': 'new_comment',
        'is_core': False,
        'web': True,
        'email': True,
        'push': True,
        'info': 'Comment on post',
        'non-editable': ['web', 'email'],
        'content_template': '<p><strong>{replier_name}</strong> replied on <strong>{author_name}</strong> response '
                            'to your post <strong>{post_title}</strong></p>',
        'content_context': {
            'post_title': 'Post title',
            'author_name': 'author name',
            'replier_name': 'replier name',
        },
        'email_template': '',
    },
    'new_response': {
        'notification_app': 'discussion',
        'name': 'new_response',
        'is_core': False,
        'web': True,
        'email': True,
        'push': True,
        'info': 'Response on post',
        'non-editable': [],
        'content_template': '<p><strong>{replier_name}</strong> responded to your '
                            'post <strong>{post_title}</strong></p>',
        'content_context': {
            'post_title': 'Post title',
            'replier_name': 'replier name',
        },
        'email_template': '',
    },
}

COURSE_NOTIFICATION_APPS = {
    'discussion': {
        'enabled': True,
        'core_info': '',
        'core_web': True,
        'core_email': True,
        'core_push': True,
    }
}


class NotificationPreferenceSyncManager:
    """
    Sync Manager for Notification Preferences
    """

    @staticmethod
    def normalize_preferences(preferences):
        """
        Normalizes preferences to reduce depth of structure.
        This simplifies matching of preferences reducing effort to get difference.
        """
        apps = []
        prefs = []
        non_editable = {}
        core_notifications = {}

        for app, app_pref in preferences.items():
            apps.append({
                'name': app,
                'enabled': app_pref.get('enabled')
            })
            for pref_name, pref_values in app_pref.get('notification_types', {}).items():
                prefs.append({
                    'name': pref_name,
                    'app_name': app,
                    **pref_values
                })
            non_editable[app] = app_pref.get('non_editable', {})
            core_notifications[app] = app_pref.get('core_notification_types', [])

        normalized_preferences = {
            'apps': apps,
            'preferences': prefs,
            'non_editable': non_editable,
            'core_notifications': core_notifications,
        }
        return normalized_preferences

    @staticmethod
    def denormalize_preferences(normalized_preferences):
        """
        Denormalizes preference from simplified to normal structure for saving it in database
        """
        denormalized_preferences = {}
        for app in normalized_preferences.get('apps', []):
            app_name = app.get('name')
            app_toggle = app.get('enabled')
            denormalized_preferences[app_name] = {
                'enabled': app_toggle,
                'core_notification_types': normalized_preferences.get('core_notifications', {}).get(app_name, []),
                'notification_types': {},
                'non_editable': normalized_preferences.get('non_editable', {}).get(app_name, {}),
            }

        for preference in normalized_preferences.get('preferences', []):
            pref_name = preference.get('name')
            app_name = preference.get('app_name')
            denormalized_preferences[app_name]['notification_types'][pref_name] = {
                'web': preference.get('web'),
                'push': preference.get('push'),
                'email': preference.get('email'),
                'info': preference.get('info'),
            }
        return denormalized_preferences

    @staticmethod
    def update_preferences(preferences):
        """
        Creates a new preference version from old preferences.
        New preference is created instead of updating old preference

        Steps to update existing user preference
            1) Normalize existing user preference
            2) Normalize default preferences
            3) Iterate over all the apps in default preference, if app_name exists in
               existing preference, update new preference app enabled value as
               existing enabled value
            4) Iterate over all preferences, if preference_name exists in existing
               preference, update new preference values of web, email and push as
               existing web, email and push respectively
            5) Denormalize new preference
        """
        old_preferences = NotificationPreferenceSyncManager.normalize_preferences(preferences)
        default_prefs = NotificationAppManager().get_notification_app_preferences()
        new_prefs = NotificationPreferenceSyncManager.normalize_preferences(default_prefs)

        for app in new_prefs.get('apps'):
            app_pref = find_app_in_normalized_apps(app.get('name'), old_preferences.get('apps'))
            if app_pref:
                app['enabled'] = app_pref['enabled']

        for preference in new_prefs.get('preferences'):
            pref_name = preference.get('name')
            app_name = preference.get('app_name')
            pref = find_pref_in_normalized_prefs(pref_name, app_name, old_preferences.get('preferences'))
            if pref:
                for channel in ['web', 'email', 'push']:
                    preference[channel] = pref[channel]
        return NotificationPreferenceSyncManager.denormalize_preferences(new_prefs)


class NotificationTypeManager:
    """
    Manager for notification types
    """

    def __init__(self):
        self.notification_types = COURSE_NOTIFICATION_TYPES

    def get_notification_types_by_app(self, notification_app):
        """
        Returns notification types for the given notification app.
        """
        return [
            notification_type for _, notification_type in self.notification_types.items()
            if notification_type.get('notification_app', None) == notification_app
        ]

    def get_core_and_non_core_notification_types(self, notification_app):
        """
        Returns core notification types for the given app name.
        """
        notification_types = self.get_notification_types_by_app(notification_app)
        core_notification_types = []
        non_core_notification_types = []
        for notification_type in notification_types:
            if notification_type.get('is_core', None):
                core_notification_types.append(notification_type)
            else:
                non_core_notification_types.append(notification_type)
        return core_notification_types, non_core_notification_types

    @staticmethod
    def get_non_editable_notification_channels(notification_types):
        """
        Returns non-editable notification channels for the given notification types.
        """
        non_editable_notification_channels = {}
        for notification_type in notification_types:
            if notification_type.get('non-editable', None):
                non_editable_notification_channels[notification_type.get('name')] = \
                    notification_type.get('non-editable')
        return non_editable_notification_channels

    @staticmethod
    def get_non_core_notification_type_preferences(non_core_notification_types):
        """
        Returns non-core notification type preferences for the given notification types.
        """
        non_core_notification_type_preferences = {}
        for notification_type in non_core_notification_types:
            non_core_notification_type_preferences[notification_type.get('name')] = {
                'web': notification_type.get('web', False),
                'email': notification_type.get('email', False),
                'push': notification_type.get('push', False),
                'info': notification_type.get('info', ''),
            }
        return non_core_notification_type_preferences

    def get_notification_app_preference(self, notification_app):
        """
        Returns notification app preferences for the given notification app.
        """
        core_notification_types, non_core_notification_types = self.get_core_and_non_core_notification_types(
            notification_app,
        )
        non_core_notification_types_preferences = self.get_non_core_notification_type_preferences(
            non_core_notification_types,
        )
        non_editable_notification_channels = self.get_non_editable_notification_channels(non_core_notification_types)
        core_notification_types_name = [notification_type.get('name') for notification_type in core_notification_types]
        return non_core_notification_types_preferences, core_notification_types_name, non_editable_notification_channels


class NotificationAppManager:
    """
    Notification app manager
    """

    def add_core_notification_preference(self, notification_app_attrs, notification_types):
        """
        Adds core notification preference for the given notification app.
        """
        notification_types['core'] = {
            'web': notification_app_attrs.get('core_web', False),
            'email': notification_app_attrs.get('core_email', False),
            'push': notification_app_attrs.get('core_push', False),
            'info': notification_app_attrs.get('core_info', ''),
        }

    def get_notification_app_preferences(self):
        """
        Returns notification app preferences for the given name.
        """
        course_notification_preference_config = {}
        for notification_app_key, notification_app_attrs in COURSE_NOTIFICATION_APPS.items():
            notification_app_preferences = {}
            notification_types, core_notifications, \
                non_editable_channels = NotificationTypeManager().get_notification_app_preference(notification_app_key)
            self.add_core_notification_preference(notification_app_attrs, notification_types)

            notification_app_preferences['enabled'] = notification_app_attrs.get('enabled', False)
            notification_app_preferences['core_notification_types'] = core_notifications
            notification_app_preferences['notification_types'] = notification_types
            notification_app_preferences['non_editable'] = non_editable_channels
            course_notification_preference_config[notification_app_key] = notification_app_preferences
        return course_notification_preference_config


def get_notification_content(notification_type, context):
    """
    Returns notification content for the given notification type with provided context.
    """
    notification_type = NotificationTypeManager().notification_types.get(notification_type, None)
    if notification_type:
        notification_type_content_template = notification_type.get('content_template', None)
        if notification_type_content_template:
            return notification_type_content_template.format(**context)
    return ''
