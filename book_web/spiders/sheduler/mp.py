# from multiprocessing import Pool
# import os, time, random, threading

# def long_time_task(name):
#     print('Run task %s (%s)...' % (name, os.getpid()))
#     time.sleep(1)

# def do_process():

#     print('Parent process %s.' % os.getpid())
#     p = Pool(4)
#     for i in range(100):
#         p.apply_async(long_time_task, args=(i, ))
#     print('Waiting for all subprocesses done...')
#     p.close()
#     p.join()
#     print('All subprocesses done.')

# def ss(n):
#     for i in range(n):
#         long_time_task(i)

# def do_thread():
#     print('thread %s is running...' % threading.current_thread().name)
#     t = threading.Thread(target=ss, args=(100, ))
#     t.start()
#     t.join()
#     print('thread %s ended.' % threading.current_thread().name)

# if __name__ == '__main__':
#     s = time.time()
#     do_process()
#     # do_thread()
#     print('All done. total time: {}'.format(time.time() - s))

try:
    # print('123' / 5)
    print(5 / 0)
    # (1, ).add(2)
except TypeError as e:
    print('te:', e)
except ZeroDivisionError as e:
    print('zde', e)
except Exception as e:
    print(11, e)