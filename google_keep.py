import gkeepapi
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv


DOMAIN = 'google_keep'

REQUIREMENTS = ['gkeepapi==^0.10.7']

_LOGGER = logging.getLogger(__name__)

CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'
CONF_LIST_NAMES = 'list_name'
DEFAULT_LIST_NAME = 'Groceries'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_LIST_NAMES, default=[]): vol.All(cv.ensure_list, [cv.string])
    })
}, extra=vol.ALLOW_EXTRA)

SERVICE_LIST_NAME = 'title'
SERVICE_LIST_ITEM = 'items'
SERVICE_LIST_COLOR = 'color'
SERVICE_LIST_PIN = 'pin'

SERVICE_LIST_SCHEMA = vol.Schema({
    vol.Optional(SERVICE_LIST_NAME): cv.string,
    vol.Optional(SERVICE_LIST_COLOR): cv.string,
    vol.Optional(SERVICE_LIST_PIN): cv.boolean,
    vol.Required(SERVICE_LIST_ITEM): cv.ensure_list_csv,
})


def setup(hass, config):
    cfg = config.get(DOMAIN)

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    default_list_name = config.get(CONF_LIST_NAMES)

    keep = gkeepapi.Keep()

    # Login
    login = keep.login(username, password)
    if not login:
        _LOGGER.error("Google Keep authentication failed.")
        return False

    def add_to_list(call):
        list_name = call.data.get(SERVICE_LIST_NAME, default_list_name)
        items = call.data.get(SERVICE_LIST_ITEM)

        # Split any items in the list separated by quotes
        items = [x for item in items for x in item.split(' and ')]

        # Sync with Google servers
        keep.sync()

        # Find the target list amongst all the Keep notes/lists
        for l in keep.all():
            if l.title == list_name:
                list_to_update = l
                break
            else:
                _LOGGER.info("List with name {} not found on Keep. Creating new list.".format(list_name))
                list_to_update = keep.createList(list_name)
                _LOGGER.info("Items to add: {}".format(items))
                # For each item,
                for item in items:
                    # ...is the item already on the list?
                    for old_item in list_to_update.items:
                        # Compare the new item to each existing item
                        if old_item.text.lower() == item:
                            # Uncheck the item if it is already on the list.
                            old_item.checked = False
                            break
                        # If the item is not already on the list,
                        else:
                            # ...add the item to the list, unchecked.
                            list_to_update.add(item, False)
                    # Sync with Google servers
                    keep.sync()

    def edit_list(call):
        pass
    # Register the service google_keep.add_to_list with Home Assistant.
    hass.services.register(DOMAIN, 'add_to_list', add_to_list, schema=SERVICE_LIST_SCHEMA)
    hass.services.register(DOMAIN, 'edit_list', edit_list, schema=SERVICE_LIST_SCHEMA)
    hass.services.register(DOMAIN, 'new_list', new_list, schema=SERVICE_LIST_SCHEMA)

    # Return boolean to indicate successful initialization.
    return True
