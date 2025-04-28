#!/usr/bin/env python3


"""
Copyright (C) DLR-TS 2024

Python executable to send a single message to Mattermost

To find out the command line parameters call it with option --help.
"""


import sys
import argparse
from mattermost_messenger import MattermostSender, MattermostError



def _parseCommandLine() -> argparse.Namespace:
    """Parse command line"""
    parser = argparse.ArgumentParser(description="Send a message to Mattermost channel")
    parser.add_argument('--webhook', '-w',
                        required=True,
                        help="(required) Mattermost webhook to send the message to.")
    parser.add_argument('--message', '-m',
                        required=True,
                        help="(required) Message to send.")
    parser.add_argument('--channel', '-c',
                        help="(optional) Mattermost channel to send the message to. REQUIRES that the webhook has access to the channel. Default is the channel configured with the webhook.")
    parser.add_argument('--emoji', '-e',
                        help="(optional) Name of an emoji to tag the message with. You can find the name by hovering over an emoji in the selector in Mattermost.")
    parser.add_argument('--timeout', '-t',
                        type=float,
                        help="(optional) Timeout in seconds (float) to wait until sending is considered as failed.")
    parser.add_argument('--proxy', '-p',
                        help="(optional) Address (including port) of a proxy server for http(s) requests.")
    return parser.parse_args()



def _send(args: argparse.Namespace) -> int:
    """Apply MattermostSender to send message"""
    try:
        with MattermostSender(url=args.webhook, timeout=args.timeout, channel=args.channel, proxy=args.proxy) as sender:
            sender.send(msg=args.message, emoji=args.emoji)
        return 0
    except MattermostError as ex:
        print(f"Failed to send message to Mattermost: {ex}", file=sys.stderr)
        return 1



def main():
    """Execute as script"""
    args = _parseCommandLine()
    result = _send(args)
    sys.exit(result)


if __name__ == '__main__':
    main()


