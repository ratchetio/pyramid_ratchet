pyramid_ratchet
===============

pyramid_ratchet is a simple middleware for reporting errors from Pyramid apps to Ratchet.io_.


Requirements
------------
pyramid_ratchet requires:

- Python 2.6 or 2.7
- Pyramid 1.2+
- requests 0.12+
- a Ratchet.io_ account


Installation
------------
Install using pip::
    
    pip install pyramid_ratchet


Configuration
-------------
Add pyramid_ratchet to the beginning of your ``pyramid.includes``::
    
    [app:main]
    pyramid.includes =
        pyramid_ratchet
        pyramid_debugtoolbar

Add the bare minimum configuration variables::

    [app:main]
    ratchet.access_token = 32charactertoken

Most users will want a few extra settings to take advantage of more features::

    [app:main]
    ratchet.access_token = 32charactertoken
    ratchet.environment = production
    ratchet.branch = master
    ratchet.root = %(here)s
    ratchet.github.account = youraccount
    ratchet.github.repo = yourrepo

Here's the full list of configuration variables:

access_token
    Access token from your Ratchet.io project
endpoint
    URL items are posted to.
    
    **default:** ``http://submit.ratchet.io/api/item/``
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
github.account
    Github account name for your github repo. Required for Github integration.
github.repo
    Github repo name. Required for Github integration.
branch
    Name of the checked-out branch. Required for Github integration.
agent.log_file
    If ``handler`` is ``agent``, the path to the log file. Filename must end in ``.ratchet``


Contributing
------------

Contributions are welcome. The project is hosted on github at http://github.com/brianr/pyramid_ratchet


Additional Help
---------------
If you have any questions, feedback, etc., drop me a line at brian@ratchet.io


.. _Ratchet.io: http://ratchet.io/
.. _`download the zip`: https://github.com/brianr/pyramid_ratchet/zipball/master
.. _ratchet-agent: http://github.com/brianr/ratchet-agent
