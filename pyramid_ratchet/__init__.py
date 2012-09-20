"""
Plugin for Pyramid apps to submit errors to Ratchet.io
"""

import json
import logging
import socket
import sys
import threading
import time
import types
import traceback
import uuid

from pyramid.httpexceptions import WSGIHTTPException
from pyramid.tweens import EXCVIEW
import requests

VERSION = '0.3.2'
DEFAULT_ENDPOINT = 'https://submit.ratchet.io/api/1/item/'
DEFAULT_WEB_BASE = 'https://ratchet.io'


log = logging.getLogger(__name__)
agent_log = None


def handle_error(settings, request):
    """
    Handle an error.

    Wrapper around _handle_error. Unless debug mode is on, calls _handle_error in a try-catch
    so that errors while reporting the error do not cause the application itself to crash.
    """
    if settings.get('debug') == 'true':
        _handle_error(settings, request)
    else:
        try:
            _handle_error(settings, request)
        except:
            log.exception("Error while reporting error to ratchet")


def _handle_error(settings, request):
    payload = _build_payload(settings, request)
    # set environment variable to be picked up by the debug toolbar
    request.environ['ratchet.uuid'] = payload['data']['uuid']
    
    payload_data = json.dumps(payload)

    handler = settings.get('handler', 'thread')
    if handler == 'blocking':
        _send_payload(settings, payload_data)
    elif handler == 'thread':
        thread = threading.Thread(target=_send_payload, args=(settings, payload_data))
        thread.start()
    elif handler == 'agent':
        _write_for_agent(settings, payload_data)



def _build_payload(settings, request):
    # basic params
    data = {
        'timestamp': int(time.time()),
        'environment': settings['environment'],
        'level': 'error',
        'language': 'python',
        'framework': 'pyramid',
        'uuid': str(uuid.uuid4()),
        'notifier': {
            'name': 'pyramid_ratchet',
            'version': VERSION,
        }
    }

    # exception info
    cls, exc, trace = sys.exc_info()
    # most recent call last
    raw_frames = traceback.extract_tb(trace)
    frames = [{'filename': f[0], 'lineno': f[1], 'method': f[2], 'code': f[3]} for f in raw_frames]
    data['body'] = {
        'trace': {
            'frames': frames,
            'exception': {
                'class': cls.__name__,
                'message': str(exc),
            }
        }
    }

    # request data
    data['request'] = {
        'url': request.url,
        'GET': dict(request.GET),
        'user_ip': _extract_user_ip(request),
        'headers': dict(request.headers),
    }

    if request.matchdict:
        data['request']['params'] = request.matchdict
    
    # workaround for webob bug when the request body contains binary data but has a text
    # content-type
    try:
        data['request']['POST'] = dict(request.POST)
    except UnicodeDecodeError:
        data['request']['body'] = request.body

    # server environment
    data['server'] = {
        'host': socket.gethostname(),
        'branch': settings.get('branch'),
        'root': settings.get('root'),
    }
    
    # 'person': try request.ratchet_person first. if not defined, build using request.user_id
    try:
        if hasattr(request, 'ratchet_person'):
            data['person'] = request.ratchet_person
        elif hasattr(request, 'user_id'):
            # if it looks like a function, call it.
            user_id_prop = request.user_id
            if isinstance(user_id_prop, (types.MethodType, types.FunctionType)):
                user_id = user_id_prop()
            else:
                user_id = user_id_prop

            data['person'] = {'id': str(request.user_id)}
    except:
        log.exception("Exception while preparing 'person' data for Ratchet payload")

    # build into final payload
    payload = {
        'access_token': settings['access_token'],
        'data': data
    }
    return payload

    
def _send_payload(settings, payload):
    resp = requests.post(settings.get('endpoint', DEFAULT_ENDPOINT), data=payload, timeout=1)
    if resp.status_code != 200:
        log.warning("Got unexpected status code from Ratchet.io api: %s\nResponse:\n%s",
            resp.status_code, resp.text)


def _write_for_agent(settings, payload):
    # create log if it doesn't exist
    global agent_log
    if not agent_log:
        agent_log = logging.getLogger('ratchet_agent')
        handler = logging.FileHandler(settings.get('agent.log_file', 'log.ratchet'), 'a', 'utf-8')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        agent_log.addHandler(handler)
        agent_log.setLevel(logging.WARNING)

    # write json line
    agent_log.error(json.dumps(payload))


def _extract_user_ip(request):
    # some common things passed by load balancers... will need more of these.
    real_ip = request.headers.get('X-Real-Ip')
    if real_ip:
        return real_ip
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for
    return request.remote_addr


def parse_settings(settings):
    prefix = 'ratchet.'
    out = {}
    for k, v in settings.iteritems():
        if k.startswith(prefix):
            out[k[len(prefix):]] = v
    return out


def ratchet_tween_factory(pyramid_handler, registry):
    settings = parse_settings(registry.settings)

    whitelist = ()
    blacklist = (WSGIHTTPException,)

    def ratchet_tween(request):
        # for testing out the integration
        try:
            if (settings.get('allow_test', 'true') == 'true' and 
                request.GET.get('pyramid_ratchet_test') == 'true'):
                try:
                    raise Exception("pyramid_ratchet test exception")
                except:
                    handle_error(settings, request)
        except:
            log.exception("Error in pyramid_ratchet_test block")
            
        try:
            response = pyramid_handler(request)
        except whitelist:
            handle_error(settings, request)
            raise
        except blacklist:
            raise
        except:
            handle_error(settings, request)
            raise
        return response

    return ratchet_tween


def patch_debugtoolbar(settings):
    """
    Patches the pyramid_debugtoolbar (if installed) to display a link to the related ratchet item.
    """
    try:
        from pyramid_debugtoolbar import tbtools
    except ImportError:
        return

    ratchet_web_base = settings.get('ratchet.web_base', DEFAULT_WEB_BASE)
    if ratchet_web_base.endswith('/'):
        ratchet_web_base = ratchet_web_base[:-1]
    
    def insert_ratchet_console(request, html):
        # insert after the closing </h1>
        item_uuid = request.environ.get('ratchet.uuid')
        if not item_uuid:
            return html
        
        url = '%s/item/uuid/?uuid=%s' % (ratchet_web_base, item_uuid)
        link = '<a style="color:white;" href="%s">View in Ratchet.io</a>' % url
        new_data = "<h2>Ratchet.io: %s</h2>" % link
        insertion_marker = "</h1>"
        replacement = insertion_marker + new_data
        return html.replace(insertion_marker, replacement, 1)

    # patch tbtools.Traceback.render_full
    old_render_full = tbtools.Traceback.render_full
    def new_render_full(self, request, *args, **kw):
        html = old_render_full(self, request, *args, **kw)
        return insert_ratchet_console(request, html)
    tbtools.Traceback.render_full = new_render_full


def includeme(config):
    """
    Pyramid entry point
    """
    config.add_tween('pyramid_ratchet.ratchet_tween_factory', under=EXCVIEW)

    # run patch_debugtoolbar, unless they disabled it
    settings = config.registry.settings
    if settings.get('ratchet.patch_debugtoolbar', 'true') == 'true':
        patch_debugtoolbar(settings)

