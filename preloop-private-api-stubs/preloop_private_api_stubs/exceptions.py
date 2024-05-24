class PreloopError(Exception):
    def __init__(self, message="A preloop error occurred"):
        self.message = message
        super().__init__(self.message)
