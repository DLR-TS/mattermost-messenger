"""
Copyright (C) DLR-TS 2024

Unit tests for MattermostHandler
"""


import unittest
import logging
import contextlib
from io import StringIO
from mattermost_messenger import MattermostHandler, MattermostHandlerError


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] -- %(levelname)s: %(message)s'
)


webhookUrl = 'https://example.com/hooks/broken'
emojis = {
    logging.NOTSET: 'notset',
    logging.ERROR: 'error',
    logging.CRITICAL: 'critical'
}



class TestMattermostHandler(unittest.TestCase):
    """Tests for MattermostHandler class"""


    def setUp(self):
        """Create a MattermostHandler object for testing"""
        self.mattermostHandler = MattermostHandler(webhookUrl, level=logging.ERROR, emojis=emojis)
        formatter = logging.Formatter(fmt='%(asctime)s [%(name)s] -- %(levelname)s: %(message)s')
        self.mattermostHandler.setFormatter(formatter)


    def tearDown(self):
        """Close MattermostHandler object"""
        self.mattermostHandler.close()


    def makeRecord(self, msg, level=logging.ERROR):
        """Helper creating a logging.LogRecord object"""
        return logging.LogRecord(
            name='NoLogger',
            level=level,
            pathname=__file__,
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None
        )


    def emitMessage(self, msg, level=logging.ERROR):
        """Helper calling self.emit

        Wait until this and all other messages are processed. Return stderr output.
        """
        with contextlib.redirect_stderr(StringIO()) as outputBuf:
            record = self.makeRecord(msg, level)
            self.mattermostHandler.emit(record)
            self.waitSent()
        return outputBuf.getvalue()


    def assertErrorOutput(self, output, msg):
        """Helper checking if output is a typical MattermostHandler error message

        output has to contain msg.

        Works like other unittests assertions.
        """
        self.assertRegex(output,
                         "Error sending a message to Mattermost(.|\n)+"
                         "(Mattermost replied with http status|Sending a message raised an exception of type.+OSError)"
                         f"(.|\n)+{msg}"
                         )


    def waitSent(self):
        """Helper to wait until the send queue is empty

        ATTENTION: This will block if not all messages are properly processed
        """
        self.mattermostHandler._sender._sendQueue.join()


    def testErrorMsg(self):
        """Test error messages due to failed send"""
        output = self.emitMessage("Info message", level=logging.INFO)
        self.assertErrorOutput(output, "Info message")

        output = self.emitMessage("Error message", logging.ERROR)
        self.assertErrorOutput(output, "Error message")

        output = self.emitMessage("Critical message", logging.CRITICAL)
        self.assertErrorOutput(output, "Critical message")


    def testErrorLogger(self):
        """Test MattermostHandler.errorLogger"""
        errorLogger = logging.getLogger('errorLogger')
        errorLogger.propagate = False
        self.mattermostHandler.errorLogger = errorLogger

        with self.assertLogs(errorLogger) as logAssertion:
            record = self.makeRecord("Error message")
            self.mattermostHandler.emit(record)
            self.waitSent()
        self.assertErrorOutput(logAssertion.output[0], "Error message")

        self.mattermostHandler.errorLogger = None
        self.waitSent()
        output = self.emitMessage("Error message 2")
        self.assertErrorOutput(output, "Error message 2")


    def testIsSelfInLogger(self):
        """Test MattermostHandler._isSelfInLogger"""

        self.assertFalse(self.mattermostHandler._isSelfInLogger(None))

        errorLogger = logging.getLogger('parent.isSelfErrorLogger')
        self.assertFalse(self.mattermostHandler._isSelfInLogger(errorLogger))

        errorLogger.addHandler(self.mattermostHandler)
        self.assertTrue(self.mattermostHandler._isSelfInLogger(errorLogger))

        errorLogger.removeHandler(self.mattermostHandler)
        self.assertFalse(self.mattermostHandler._isSelfInLogger(errorLogger))

        # Add handler to parent logger
        logging.getLogger('parent').addHandler(self.mattermostHandler)
        self.assertTrue(self.mattermostHandler._isSelfInLogger(errorLogger))

        errorLogger.propagate = False
        self.assertFalse(self.mattermostHandler._isSelfInLogger(errorLogger))


    def testErrorLoggerProperty(self):
        """Test of MattermostHandler.errorLogger property methods"""

        errorLogger = logging.getLogger('propertyErrorLogger')
        self.mattermostHandler.errorLogger = errorLogger
        self.assertIs(self.mattermostHandler.errorLogger, errorLogger)

        del self.mattermostHandler.errorLogger
        self.assertIsNone(self.mattermostHandler.errorLogger)


    def testCyclicErrorLogger(self):
        """Test that MattermostHandler._error handles a cyclic error logger"""
        errorLogger = logging.getLogger('cyclicErrorLogger')
        errorLogger.propagate = False
        errorLogger.addHandler(self.mattermostHandler)
        with self.assertRaisesRegex(MattermostHandlerError, f"Attempted to set logger 'cyclicErrorLogger' as error logger for MattermostHandler .+, but that logger contains self as handler creating a cycle\\."):
            self.mattermostHandler.errorLogger = errorLogger
        errorLogger.removeHandler(self.mattermostHandler)

        # Make error logger cyclic after adding it
        self.mattermostHandler.errorLogger = errorLogger
        errorLogger.addHandler(self.mattermostHandler)
        self.assertIs(self.mattermostHandler.errorLogger, errorLogger)
        with self.assertRaisesRegex(MattermostHandlerError, f"Handler .+ called itself to handle an internal error\\. Removing error logger\\..+cyclic error"):
            record = self.makeRecord("cyclic error")
            self.mattermostHandler._error(record, "a problem")
        self.assertIsNone(self.mattermostHandler.errorLogger)


    def testError(self):
        """Test MattermostHandler._error"""
        with contextlib.redirect_stderr(StringIO()) as outputBuf:
            record = self.makeRecord("to stderr")
            self.mattermostHandler._error(record, "an error")
        self.assertRegex(outputBuf.getvalue(), r"an error.+to stderr")

        errorLogger = logging.getLogger('errorErrorLogger')
        self.mattermostHandler.errorLogger = errorLogger
        with self.assertLogs(errorLogger) as out:
            record = self.makeRecord("to error logger")
            self.mattermostHandler._error(record, "another error")
        self.assertRegex(out.output[0], r"another error.+to error logger")


    def testGetEmoji(self):
        """Test _getEmoji method"""
        def check(level, result):
            res = self.mattermostHandler._getEmoji(level)
            self.assertEqual(res, result)

        check(logging.NOTSET, 'notset')
        check(logging.NOTSET + 1, 'notset')
        check(logging.INFO, 'notset')
        check(logging.ERROR - 1, 'notset')
        check(logging.ERROR, 'error')
        check(logging.ERROR + 1, 'error')
        check(logging.CRITICAL - 1, 'error')
        check(logging.CRITICAL, 'critical')
        check(logging.CRITICAL + 1, 'critical')


