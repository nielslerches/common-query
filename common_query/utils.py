from itertools import islice, tee


def nwise(xs, n=2):
    return zip(*(islice(xs, idx, None) for idx, xs in enumerate(tee(xs, n))))
