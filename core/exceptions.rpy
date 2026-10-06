# exceptions.rpy
init -10 python in v1FNaSR:
    class FNaSRException(Exception):

        PREFIX = "FNaSR"

        def __init__(self, message=None):
            if message is None:
                message = ":("
            super(FNaSRException, self).__init__("{} | {}".format(self.PREFIX, message))

    class FNaSRRuntimeError(FNaSRException, RuntimeError):
        pass

    class FNaSRNotImplementedError(FNaSRException, NotImplementedError):
        pass

    class FNaSRTypeError(FNaSRException, TypeError):
        pass

    class FNaSRValueError(FNaSRException, ValueError):
        pass

    class FNaSRAttributeError(FNaSRException, AttributeError):
        pass

    class FNaSRKeyError(FNaSRException, KeyError):
        pass

    class FNaSRTimeoutError(FNaSRException):
        pass

    class FNaSRNotFound(FNaSRRuntimeError):
        pass

    class FNaSRRegisterError(FNaSRRuntimeError):
        pass
