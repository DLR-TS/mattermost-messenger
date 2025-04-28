"""
Copyright (C) DLR-TS 2024

Mattermost Messenger package
"""


from .sender import MattermostSender, MattermostError
from .threaded import MattermostSenderThreaded
from .handler import MattermostHandler, MattermostHandlerError

__all__ = (
    'MattermostSender',
    'MattermostError',
    'MattermostSenderThreaded',
    'MattermostHandler',
    'MattermostHandlerError'
)


# Don't export the modules themselfes (and ignore mypy errors)
del sender      # type: ignore
del threaded    # type: ignore
del handler     # type: ignore



