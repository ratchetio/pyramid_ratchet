"""
Plugin for Pyramid apps to submit errors to Ratchet.io
"""

import json
import logging
import socket
import sys
import threading
import time
import traceback

from pyramid.httpexceptions import WSGIHTTPException
from pyramid.tweens import EXCVIEW
import requests

VERSION = '0.2.4'
DEFAULT_ENDPOINT = 'https://submit.ratchet.io/api/1/item/'


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

    handler = settings.get('handler', 'thread')
    if handler == 'blocking':
        _send_payload(settings, payload)
    elif handler == 'thread':
        thread = threading.Thread(target=_send_payload, args=(settings, payload))
        thread.start()
    elif handler == 'agent':
        _write_for_agent(settings, payload)


def _build_payload(settings, request):
    # basic params
    data = {
        'timestamp': int(time.time()),
        'environment': settings['environment'],
        'level': 'error',
        'language': 'python',
        'framework': 'pyramid',
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

    # build into final payload
    payload = {
        'access_token': settings['access_token'],
        'data': data
    }
    return json.dumps(payload)

    
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


def includeme(config):
    """
    Pyramid entry point
    """
    config.add_tween('pyramid_ratchet.ratchet_tween_factory', under=EXCVIEW)

