from pylint.reporters import BaseReporter


class CollectingReporter(BaseReporter):
    def __init__(self):
        super().__init__()
        self.messages = []

    def handle_message(self, msg):
        """Collect each message."""
        self.messages.append(msg)

    def display_reports(self, layout):
        """Skip displaying reports."""

    def _display(self, layout):
        """Override to prevent printing to stdout."""
