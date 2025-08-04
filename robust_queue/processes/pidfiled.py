class Pidfiled:
    def boot(self):
        self.setup_pidfile()
        super().boot()

    def shutdown(self):
        super().shutdown()
        self.remove_pidfile()

    def setup_pidfile(self):
        pass

    def remove_pidfile(self):
        pass
