import sys
import random
import numpy as np  # type: ignore


def print_info(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def setup_random_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)