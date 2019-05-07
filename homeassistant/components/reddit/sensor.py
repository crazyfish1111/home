"""Support for Reddit."""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ID, CONF_MAXIMUM, CONF_PASSWORD, CONF_USERNAME)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_CLIENT_ID = 'client_id'
CONF_CLIENT_SECRET = 'client_secret'
CONF_SORT_BY = 'sort_by'
CONF_SUBREDDITS = 'subreddits'

ATTR_BODY = 'body'
ATTR_COMMENTS_NUMBER = 'comments_number'
ATTR_CREATED = 'created'
ATTR_POSTS = 'posts'
ATTR_SUBREDDIT = 'subreddit'
ATTR_SCORE = 'score'
ATTR_TITLE = 'title'
ATTR_URL = 'url'

DEFAULT_NAME = 'Reddit'
DEFAULT_MAXIMUM = 10
DEFAULT_SORTING = 'hot'
DOMAIN = 'reddit'

LIST_TYPES = ['top', 'controversial', 'hot', 'new']

ICON = 'mdi:reddit'

SCAN_INTERVAL = timedelta(seconds=300)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_CLIENT_ID): cv.string,
    vol.Required(CONF_CLIENT_SECRET): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_SUBREDDITS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SORT_BY, default=DEFAULT_SORTING):
        vol.All(cv.string, vol.In(LIST_TYPES)),
    vol.Optional(CONF_MAXIMUM, default=DEFAULT_MAXIMUM): cv.positive_int,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Reddit sensor platform."""
    import praw
    import prawcore

    subreddits = config[CONF_SUBREDDITS]
    user_agent = '{}_home_assistant_sensor'.format(config[CONF_USERNAME])
    limit = config[CONF_MAXIMUM]
    sort_by = config[CONF_SORT_BY]

    try:
        reddit = praw.Reddit(
            client_id=config[CONF_CLIENT_ID],
            client_secret=config[CONF_CLIENT_SECRET],
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
            user_agent=user_agent)
    except praw.exceptions.PRAWException as err:
        _LOGGER.error(err)
        return

    sensors = []
    for subreddit in subreddits:
        sub_sensor = RedditSensor(reddit, subreddit, limit, sort_by)
        try:
            sub_sensor.update()
            sensors.append(sub_sensor)
        except prawcore.exceptions.OAuthException:
            _LOGGER.error("Credentials are not valid")
            return
        except prawcore.exceptions.Redirect:
            _LOGGER.error("Subreddit doesn't exist")
            return

    add_entities(sensors)


class RedditSensor(Entity):
    """Representation of a Reddit sensor."""

    def __init__(self, reddit, subreddit: str, limit: int, sort_by: str):
        """Initialize the Reddit sensor."""
        self._reddit = reddit
        self._subreddit = subreddit
        self._limit = limit
        self._sort_by = sort_by

        self._subreddit_data = []

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'reddit_{}'.format(self._subreddit)

    @property
    def state(self):
        """Return the state of the sensor."""
        return len(self._subreddit_data)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_SUBREDDIT: self._subreddit,
            ATTR_POSTS: self._subreddit_data,
            CONF_SORT_BY: self._sort_by,
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    def update(self):
        """Update data from Reddit API."""
        import praw

        self._subreddit_data = []

        try:
            subreddit = self._reddit.subreddit(self._subreddit)
            if hasattr(subreddit, self._sort_by):
                method_to_call = getattr(subreddit, self._sort_by)

                for submission in method_to_call(limit=self._limit):
                    self._subreddit_data.append({
                        ATTR_BODY: submission.selftext,
                        ATTR_COMMENTS_NUMBER: submission.num_comments,
                        ATTR_CREATED: submission.created,
                        ATTR_ID: submission.id,
                        ATTR_SCORE: submission.score,
                        ATTR_TITLE: submission.title,
                        ATTR_URL: submission.url,
                    })

        except praw.exceptions.PRAWException as err:
            _LOGGER.error(err)
