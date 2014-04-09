# encoding: utf-8
import os
from construct import Subconstruct, Construct
import time


def time_it(f):
    def wrapper(*args, **kwargs):
        t1 = time.time()
        ret = f(*args, **kwargs)
        t2 = time.time()

        print '"%s" time elapsed: %0.2f' % (f.__name__, (t2 - t1))

        return ret

    return wrapper

class HardPointer(Subconstruct):

    __slots__ = ['offsetfunc']

    def __init__(self, offsetfunc, subcon):
        Subconstruct.__init__(self, subcon)
        self.offsetfunc = offsetfunc

    def _parse(self, stream, context):
        pos = self.offsetfunc(context)
        stream.seek(pos, 2 if pos < 0 else 0)

        return self.subcon._parse(stream, context)

    def _sizeof(self, context):
        return 0


class Jump(Construct):

    __slots__ = ['offset_func']

    def __init__(self, offset_func):
        Construct.__init__(self, None)
        self.offset_func = offset_func

    def _parse(self, stream, context):
        pos = self.offset_func(context)
        stream.seek(pos, 2 if pos < 0 else 0)


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
