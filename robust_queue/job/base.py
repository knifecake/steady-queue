from .core import Core
from .enqueueing import Enqueueing
from .execution import Execution
from .queue_name import QueueName
from .queue_priority import QueuePriority


class Base(Core, QueueName, QueuePriority, Enqueueing, Execution):
    pass
