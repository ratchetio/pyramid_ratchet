pyramid_ratchet
===============

pyramid_ratchet is a simple middleware for reporting errors from Pyramid apps to Ratchet.io_. 

If pyramid_debugtoolbar is available, it will be monkey-patched so that exception pages show a link to the relevant item in Ratchet.io.


Requirements
------------
pyramid_ratchet requires:

- Python 2.6 or 2.7
- Pyramid 1.2+
- requests 0.12+
- a Ratchet.io `error reporting`_ account


Installation
------------
Install using pip::
    
    pip install pyramid_ratchet


Configuration
-------------
Add pyramid_ratchet to the *end* of your ``pyramid.includes``::
    
    [app:main]
    pyramid.includes =
        pyramid_debugtoolbar
        pyramid_ratchet

Add the bare minimum configuration variables::

    [app:main]
    ratchet.access_token = 32charactertoken

Most users will want a few extra settings to take advantage of more features::

    [app:main]
    ratchet.access_token = 32charactertoken
    ratchet.environment = production
    ratchet.branch = master
    ratchet.root = %(here)s

Here's the full list of configuration variables:

access_token
    Access token from your Ratchet.io project
handler
    One of:

    - blocking -- runs in main thread
    - thread -- spawns a new thread
    - agent -- writes messages to a log file for consumption by ratchet-agent_

    **default:** ``thread``
environment
    Environment name. Any string up to 255 chars is OK. For best results, use "production" for your production environment.
root
    Absolute path to the root of your application, not including the final ``/``. ``%(here)s`` is probably what you want.
branch
    Name of the checked-out branch.

    **default:** ``master``
agent.log_file
    If ``handler`` is ``agent``, the path to the log file. Filename must end in ``.ratchet``
allow_test
    When true, adds a hook to send a test error report (but not interrupt the request in any other way) whenever the query string contains ``pyramid_ratchet_test=true``.

    **default:** ``true``
endpoint
    URL items are posted to.
    
    **default:** ``https://submit.ratchet.io/api/1/item/``
web_base
    Base URL of the Ratchet.io web interface (used for links on the exception debug page)

    **default** ``https://ratchet.io``
patch_debugtoolbar
    If true, pyramid_debugtoolbar will be monkeypatched so that exception debug pages include a link to the item in Ratchet.io

    **default** ``true``


Contributing
------------

Contributions are welcome. The project is hosted on github at http://github.com/ratchetio/pyramid_ratchet


Additional Help
---------------
If you have any questions, feedback, etc., drop me a line at brian@ratchet.io


.. _Ratchet.io: http://ratchet.io/
.. _error reporting: http://ratchet.io/
.. _ratchet-agent: http://github.com/ratchetio/ratchet-agent
