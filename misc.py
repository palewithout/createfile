# encoding: utf-8
import os
from construct import Construct
import time

MAGIC_END_SECTION = b'\x55\xaa'

STATE_DOS_ENTRY = 0b01
STATE_LFN_ENTRY = 0b10
STATE_START = 0b11


def clear_cur_obj(obj):
    obj['name'] = ''
    obj['checksum'] = 0


def time_it(f):
    def wrapper(*args, **kwargs):
        t1 = time.time()
        ret = f(*args, **kwargs)
        t2 = time.time()

        print('"%s" time elapsed: %0.2f' % (f.__name__, (t2 - t1)))

        return ret

    return wrapper


class SimpleCounter:

    __slots__ = ['counter']

    def __init__(self, initial=0):
        self.counter = initial

    def inc(self, n=1):
        self.counter += n

    def dec(self, n=1):
        self.counter -= n

    def __str__(self):
        return str(self.counter)

    def __repr__(self):
        return repr(self.counter)

    def __lt__(self, other):
        if isinstance(other, self):
            other = other.counter
        return self.counter < other

    def __eq__(self, other):
        return self.counter == other.counter

    def __hash__(self):
        return hash(self.counter)

    def __int__(self):
        return self.counter


class Skip(Construct):

    __slots__ = ['length', 'length_func', 'cons']

    def __init__(self, length=None, length_func=None, cons=None):
        Construct.__init__(self, None)
        self.length_func = length_func
        self.length = length
        self.cons = cons

    def _parse(self, stream, context):
        func_mode = self.length_func and self.length_func(context)
        cons_mode = self.cons and sum(map(lambda con:
                                              con(None)._sizeof(object()),
                                          self.cons))

        length = self.length or func_mode or cons_mode

        if not length:
            raise ValueError('invalid Skip construct')
        if length < 0:
            raise ValueError('skipping negative number of bytes')

        stream.seek(length, os.SEEK_CUR)


class StateManager:
    def __init__(self, init_state):
        self._state = init_state

    def transit_to(self, state):
        self._state = state

    def is_(self, state):
        return self._state == state
