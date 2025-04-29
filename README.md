# Mattermost Messenger

This package provides the Python module `mattermost_messenger` containing code to easily send messages to a Mattermost channel.

[Mattermost](https://mattermost.com/) is a persistent chat tool. It manages chats in different teams and channels. The chat messages are usually kept for an indefinite time. So you may create a channel to receive notifications from automatic processes to monitor what is going on.

The package provides several interfaces. Besides a command line executable it contains classes to send Mattermost messages either directly or in its own thread (to avoid blocking the caller due to network issues). Furthermore, there is a Python logging handler sending log messages to Mattermost.

See also `CHANGELOG.md` for current features.



## License

See `LICENSE.md`



## Installation

Install package with Pip from PyPI:

```bash
pip install mattermost-messenger
```


### Required Python version

The Mattermost Messenger requires at least Python 3.10 or the version noted as dependency in `pyproject.toml`.



## Documentation

Every class and method contains a doc string with its documentation.

With Sphinx you can generate a nicely formatted HTML page hierarchy to easily browse the doc strings.

In order to build the documentation you need to install the Python package manager [Poetry](https://python-poetry.org/) if you haven't done that yet:

```bash
pip install poetry
```

Next, you need to apply Poetry to create a virtual environment with the required Sphinx tools. This is done with a single Poetry call:

```bash
poetry install --with=docs
```

Finally, change to the `docs` folder and apply its `Makefile` within the Poetry virtual environment:

```bash
cd docs
poetry run make html
```

Now, the folder `docs/_build/html/` contains the doc pages. Open `index.html` with a web browser to see the documentation.

With `make help` instead of `make html` a list of available other formats besides `html` are shown.



## Usage

### Mattermost webhook

To send messages to Mattermost you first need to create a webhook URL in Mattermost as destination.

To create a webhook you need to be an admin of the Mattermost team. (Each bubble on the left bar of the Mattermost user interface is a team in Mattermost's terminology.) Once the webhook is created, everyone can use it as long as it is active.

The user who created a team is its admin by default. Any admin could make other team members an admin as well by opening the team's menu *Manage Members*. The menu is only visible for admins, if you cannot find it you are probably not yet an admin.

To create a webhook go to the team with the destination channel. Then open the menu on Mattermost's top left (with the nine dots icon) and select *Integrations* (only available for team admins), then *Incoming Webhooks*, and then *Add Incoming Webhook*. Now, you can configure a new webhook. Note that you need to uncheck *Lock to this channel* if you plan to use the channel argument of the interfaces. When done, you can copy its URL, which is a required parameter for all interfaces.

[This documentation](https://developers.mattermost.com/integrate/webhooks/incoming/) explains more on Mattermost webhooks. The part about using a webhook is coverd by this package. 


### Proxy

In case you run the Mattermost Messenger behind a proxy such that Mattermost can only be accessed through the proxy there are two options to pass the proxy setup:

* Every interface of Mattermost Messenger has an optional `proxy` parameter
* If no `proxy` argument is given the environment variables `HTTPS_PROXY`, `HTTP_PROXY`, and `NO_PROXY` are considered


### Emojis

All interfaces have an optional parameter to set an emoji. The emoji will be shown to the left of the message. The `emoji` parameter should be given as the name of an emoji known to the Mattermost instance. You can find out an emoji name by hovering over an emoji in the emoji selection dialog in the Mattermost app or web frontend.


### Command line tool

After installation the command `sendToMattermost` is available or you can alternatively execute the package with `python -m mattermost_messenger`.

You have to pass at least a webhook with option `--webhook` or `-w` for short and the message with option `--message` or `-m`. Further options allow to set an emoji, select a channel (if enabled, see [section on webhooks](#mattermost-webhook)), set a timeout, or set a [proxy](#proxy).

Call the command with option `--help` to get a list of all parameters and their descriptions.


### Classes

This package provides several classes to send messages to a Mattermost webhook. Each of the following classes can be used directly.

To use the classes import the package with

```python
import mattermost_messenger
```

or specific classes, for example:

```python
from mattermost_messenger import MattermostSender, MattermostError
```

For details on the usage see the API documentation or the doc strings in the code.


#### `MattermostSender`

Basic class to establish a connection to a Mattermost webhook and send messages to it.

It provides a `connect` and a `disconnect` method besides a `send` method. In case of an error it raises a `MattermostSend` exception. In case of Mattermost access problems it may take up to the given timeout until the `send` method returns or an exception is raised.

The class can be used as context manager, which takes care to call `connect` on entry and `disconnect` on leaving the `with` statement.


#### `MattermostSenderThreaded`

Variant of `MattermostSender` that applies an independent thread to send messages to Mattermost. Hence, calls to its `send` method never block on access problems with Mattermost.

The `send` method is similar to `MattermostSender.send` but instead of sending the message right away it stores it in a send queue. The background thread takes care to actually send the messages by passing them to `MattermostSender.send`.

On `__init__` this class creates and starts the send thread. The thread runs until `shutdown` is called, after which it cannot be used any more. `shutdown` **must be called** to send the remaining messages in the send queue and terminate the thread, which would otherwise block the program from exiting.

On error the class calls an error callback function that has to be passed to `__init__`. To know which message eventually triggered an error callback call you may pass an arbitrary object to `send`, which will be passed to the related error callback call in case of an error. 


#### `MattermostHandler`

A Python `logging.Handler` specialization applying `MattermostSenderThreaded` to send log messages to Mattermost through the logging system. An instance of this class can be added as handler to a `logging.Logger` instance.

**Make sure** to call `logging.shutdown()` at th end of the program to ensure that `MattermostHandler.close` will be called, which in turn calls `MattermostSenderThreaded.shutdown`.

In case of an error it will be logged to a special `errorLogger` instance of `logging.Logger` or -- if not present -- printed to `stderr`. An error logger can be passed to `__init__` or set later by assigning it to `MattermostHandler.errorLogger`.

The user must ensure that the error logger does not directly or indirectly send the message back to the `MattermostHandler` instance that created it. Such cycles are detected and lead to a `MattermostHandlerError` exception. Detection takes place on adding an error handler and before a message is sent to it. The latter happens within the sending thread so it terminates the thread breaking `MattermostHandler`.

Emojis are given as a dictionary passed to `MattermostHandler.__init__`. The dictionary maps log levels on emoji names. The emoji assigned to the highest log level less than or equal to the log message's level will be used, so you don't have to define an emoji for all possible log levels. This allows, for example, to have a more eye-catching emoji for critical messages than for regular error messages.


#### Exception classes

* `MattermostError`
  * Raised by `MattermostSender` on any error.
* `MattermostHandlerError`
  * Derived from `MattermostError`
  * Raised by `MattermostHandler` if it cannot handle an error with its error logger.



## Contributing

See `CONTRIBUTING.md`

