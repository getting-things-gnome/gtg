# Python library for Remember The Milk API

__author__ = 'Sridhar Ratnakumar <http://nearfar.org/>'
__all__ = (
    'API',
    'createRTM',
    'set_log_level',
)


import urllib
from hashlib import md5

from GTG import _
from GTG.tools.logger import Log

_use_jsonlib = False
try:
    import simplejson as json
    assert json
    _use_jsonlib = True
except ImportError:
    try:
        import json as json
        assert json
        _use_jsonlib = True
    except ImportError:
        try:
            from django.utils import simplejson as json
            _use_jsonlib = True
        except ImportError:
            pass

if not _use_jsonlib:
    Log.warning("simplejson module is not available, "
                "falling back to the internal JSON parser. "
                "Please consider installing the simplejson module from "
                "http://pypi.python.org/pypi/simplejson.")

SERVICE_URL = 'http://api.rememberthemilk.com/services/rest/'
AUTH_SERVICE_URL = 'http://www.rememberthemilk.com/services/auth/'


class RTMError(Exception):
    pass


class RTMAPIError(RTMError):
    pass


class AuthStateMachine(object):

    class NoData(RTMError):
        pass

    def __init__(self, states):
        self.states = states
        self.data = {}

    def dataReceived(self, state, datum):
        if state not in self.states:
            error_string = _("Invalid state") + " <%s>"

            raise RTMError(error_string % state)
        self.data[state] = datum

    def get(self, state):
        if state in self.data:
            return self.data[state]
        else:
            raise AuthStateMachine.NoData('No data for <%s>' % state)


class RTM(object):

    def __init__(self, apiKey, secret, token=None):
        self.apiKey = apiKey
        self.secret = secret
        self.authInfo = AuthStateMachine(['frob', 'token'])

        # this enables one to do 'rtm.tasks.getList()', for example
        for prefix, methods in API.items():
            setattr(self, prefix,
                    RTMAPICategory(self, prefix, methods))

        if token:
            self.authInfo.dataReceived('token', token)

    def _sign(self, params):
        "Sign the parameters with MD5 hash"
        pairs = ''.join(['%s%s' % (k, v) for k, v in sortedItems(params)])
        return md5(self.secret + pairs).hexdigest()

    def get(self, **params):
        "Get the XML response for the passed `params`."
        params['api_key'] = self.apiKey
        params['format'] = 'json'
        params['api_sig'] = self._sign(params)

        json_data = openURL(SERVICE_URL, params).read()

        # LOG.debug("JSON response: \n%s" % json)
        if _use_jsonlib:
            data = dottedDict('ROOT', json.loads(json_data))
        else:
            data = dottedJSON(json_data)
        rsp = data.rsp

        if rsp.stat == 'fail':
            raise RTMAPIError('API call failed - %s (%s)' % (
                rsp.err.msg, rsp.err.code))
        else:
            return rsp

    def getNewFrob(self):
        rsp = self.get(method='rtm.auth.getFrob')
        self.authInfo.dataReceived('frob', rsp.frob)
        return rsp.frob

    def getAuthURL(self):
        try:
            frob = self.authInfo.get('frob')
        except AuthStateMachine.NoData:
            frob = self.getNewFrob()

        params = {
            'api_key': self.apiKey,
            'perms': 'delete',
            'frob': frob
        }
        params['api_sig'] = self._sign(params)
        return AUTH_SERVICE_URL + '?' + urllib.urlencode(params)

    def getToken(self):
        frob = self.authInfo.get('frob')
        rsp = self.get(method='rtm.auth.getToken', frob=frob)
        self.authInfo.dataReceived('token', rsp.auth.token)
        return rsp.auth.token


class RTMAPICategory:
    "See the `API` structure and `RTM.__init__`"

    def __init__(self, rtm, prefix, methods):
        self.rtm = rtm
        self.prefix = prefix
        self.methods = methods

    def __getattr__(self, attr):
        if attr in self.methods:
            rargs, oargs = self.methods[attr]
            if self.prefix == 'tasksNotes':
                aname = 'rtm.tasks.notes.%s' % attr
            else:
                aname = 'rtm.%s.%s' % (self.prefix, attr)
            return lambda **params: self.callMethod(
                aname, rargs, oargs, **params)
        else:
            raise AttributeError('No such attribute: %s' % attr)

    def callMethod(self, aname, rargs, oargs, **params):
        # Sanity checks
        for requiredArg in rargs:
            if requiredArg not in params:
                raise TypeError(
                    'Required parameter (%s) missing' % requiredArg)

        for param in params:
            if param not in rargs + oargs:
                Log.error('Invalid parameter (%s)' % param)

        return self.rtm.get(method=aname,
                            auth_token=self.rtm.authInfo.get('token'),
                            **params)


# Utility functions
def sortedItems(dictionary):
    "Return a list of (key, value) sorted based on keys"
    keys = dictionary.keys()
    keys.sort()
    for key in keys:
        yield key, dictionary[key]


def openURL(url, queryArgs=None):
    if queryArgs:
        url = url + '?' + urllib.urlencode(queryArgs)
    # LOG.debug("URL> %s", url)
    return urllib.urlopen(url)


class dottedDict(object):
    """Make dictionary items accessible via the object-dot notation."""

    def __init__(self, name, dictionary):
        self._name = name

        if type(dictionary) is dict:
            for key, value in dictionary.items():
                if type(value) is dict:
                    value = dottedDict(key, value)
                elif type(value) in (list, tuple) and key != 'tag':
                    value = [dottedDict('%s_%d' % (key, i), item)
                             for i, item in indexed(value)]
                setattr(self, key, value)
        else:
            raise ValueError('not a dict: %s' % dictionary)

    def __repr__(self):
        children = [c for c in dir(self) if not c.startswith('_')]
        return 'dotted <%s> : %s' % (
            self._name,
            ', '.join(children))


def safeEval(string):
    return eval(string, {}, {})


def dottedJSON(json):
    return dottedDict('ROOT', safeEval(json))


def indexed(seq):
    index = 0
    for item in seq:
        yield index, item
        index += 1


# API spec

API = {
    'auth': {
        'checkToken':
        [('auth_token',), ()],
        'getFrob':
        [(), ()],
        'getToken':
        [('frob',), ()]
    },
    'contacts': {
        'add':
    [('timeline', 'contact'), ()],
        'delete':
    [('timeline', 'contact_id'), ()],
        'getList':
    [(), ()]
    },
    'groups': {
        'add':
    [('timeline', 'group'), ()],
        'addContact':
    [('timeline', 'group_id', 'contact_id'), ()],
        'delete':
    [('timeline', 'group_id'), ()],
        'getList':
    [(), ()],
        'removeContact':
    [('timeline', 'group_id', 'contact_id'), ()],
    },
    'lists': {
        'add':
    [('timeline', 'name',), ('filter',)],
        'archive':
    [('timeline', 'list_id'), ()],
        'delete':
    [('timeline', 'list_id'), ()],
        'getList':
    [(), ()],
        'setDefaultList':
    [('timeline'), ('list_id')],
        'setName':
    [('timeline', 'list_id', 'name'), ()],
        'unarchive':
    [('timeline',), ('list_id',)]
    },
    'locations': {
        'getList':
    [(), ()]
    },
    'reflection': {
        'getMethodInfo':
    [('methodName',), ()],
        'getMethods':
    [(), ()]
    },
    'settings': {
        'getList':
    [(), ()]
    },
    'tasks': {
        'add':
    [('timeline', 'name',), ('list_id', 'parse',)],
        'addTags':
    [('timeline', 'list_id', 'taskseries_id', 'task_id', 'tags'),
     ()],
        'complete':
    [('timeline', 'list_id', 'taskseries_id', 'task_id',), ()],
        'delete':
    [('timeline', 'list_id', 'taskseries_id', 'task_id'), ()],
        'getList':
    [(),
     ('list_id', 'filter', 'last_sync')],
        'movePriority':
    [('timeline', 'list_id', 'taskseries_id', 'task_id', 'direction'),
     ()],
        'moveTo':
    [(
    'timeline', 'from_list_id', 'to_list_id', 'taskseries_id', 'task_id'),
        ()],
        'postpone':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ()],
        'removeTags':
        [('timeline', 'list_id', 'taskseries_id', 'task_id', 'tags'),
         ()],
        'setDueDate':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('due', 'has_due_time', 'parse')],
        'setEstimate':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('estimate',)],
        'setLocation':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('location_id',)],
        'setName':
        [('timeline', 'list_id', 'taskseries_id', 'task_id', 'name'),
         ()],
        'setPriority':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('priority',)],
        'setRecurrence':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('repeat',)],
        'setTags':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('tags',)],
        'setURL':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ('url',)],
        'uncomplete':
        [('timeline', 'list_id', 'taskseries_id', 'task_id'),
         ()],
    },
    'tasksNotes': {
        'add':
    [('timeline', 'list_id', 'taskseries_id',
      'task_id', 'note_title', 'note_text'), ()],
        'delete':
    [('timeline', 'note_id'), ()],
        'edit':
    [('timeline', 'note_id', 'note_title', 'note_text'), ()]
    },
    'test': {
        'echo':
    [(), ()],
        'login':
    [(), ()]
    },
    'time': {
        'convert':
    [('to_timezone',), ('from_timezone', 'to_timezone', 'time')],
        'parse':
    [('text',), ('timezone', 'dateformat')]
    },
    'timelines': {
        'create':
    [(), ()]
    },
    'timezones': {
        'getList':
    [(), ()]
    },
    'transactions': {
        'undo':
    [('timeline', 'transaction_id'), ()]
    },
}


def createRTM(apiKey, secret, token=None):
    rtm = RTM(apiKey, secret, token)
#    if token is None:
#        print 'No token found'
#        print 'Give me access here:', rtm.getAuthURL()
#        raw_input('Press enter once you gave access')
#        print 'Note down this token for future use:', rtm.getToken()

    return rtm


def test(apiKey, secret, token=None):
    rtm = createRTM(apiKey, secret, token)

    rspTasks = rtm.tasks.getList(filter='dueWithin:"1 week of today"')
    print [t.name for t in rspTasks.tasks.list.taskseries]
    print rspTasks.tasks.list.id

    rspLists = rtm.lists.getList()
    # print rspLists.lists.list
    print [(x.name, x.id) for x in rspLists.lists.list]


def set_log_level(level):
    '''Sets the log level of the logger used by the module.

    >>> import rtm
    >>> import logging
    >>> rtm.set_log_level(logging.INFO)
    '''

    # LOG.setLevel(level)
