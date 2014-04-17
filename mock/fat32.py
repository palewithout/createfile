# encoding: utf-8
import pickle
import time


def memory_dump(f):
    def wrapper(*args, **kwargs):
        _ = next(f(*args, **kwargs))
        pickle.dump(_,
                    open('../dumps/dump0', 'wb'),
                    protocol=-1)
    return wrapper


class MockFAT32(object):
    def __init__(self):
        print('mocking fat32')

        print('loading pickle')
        t1 = time.time()
        self._fat32 = pickle.load(open('../dumps/dump0', 'rb'))
        t2 = time.time()
        print('loaded pickle in %0.2f' % (t2 - t1))



if __name__ == '__main__':
    mock = MockFAT32()
    mock._fat32.get_fdt()
