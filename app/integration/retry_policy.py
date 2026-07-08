from dataclasses import dataclass
@dataclass(slots=True)
class RetryPolicy:
    retries:int=3
    timeout:float=10.0
    backoff:float=0.5
