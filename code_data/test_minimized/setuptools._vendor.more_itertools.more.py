def sort_together(iterables, key_list=(0,), key=None, reverse=False):
    """Return the input iterables sorted together, with *key_list* as the
    priority for sorting. All iterables are trimmed to the length of the
    shortest one.

    This can be used like the sorting function in a spreadsheet. If each
    iterable represents a column of data, the key list determines which
    columns are used for sorting.

    By default, all iterables are sorted using the ``0``-th iterable::

        >>> iterables = [(4, 3, 2, 1), ('a', 'b', 'c', 'd')]
        >>> sort_together(iterables)
        [(1, 2, 3, 4), ('d', 'c', 'b', 'a')]

    Set a different key list to sort according to another iterable.
    Specifying multiple keys dictates how ties are broken::

        >>> iterables = [(3, 1, 2), (0, 1, 0), ('c', 'b', 'a')]
        >>> sort_together(iterables, key_list=(1, 2))
        [(2, 3, 1), (0, 0, 1), ('a', 'c', 'b')]

    To sort by a function of the elements of the iterable, pass a *key*
    function. Its arguments are the elements of the iterables corresponding to
    the key list::

        >>> names = ('a', 'b', 'c')
        >>> lengths = (1, 2, 3)
        >>> widths = (5, 2, 1)
        >>> def area(length, width):
        ...     return length * width
        >>> sort_together([names, lengths, widths], key_list=(1, 2), key=area)
        [('c', 'b', 'a'), (3, 2, 1), (1, 2, 5)]

    Set *reverse* to ``True`` to sort in descending order.

        >>> sort_together([(1, 2, 3), ('c', 'b', 'a')], reverse=True)
        [(3, 2, 1), ('a', 'b', 'c')]

    """
    if key is None:
        # if there is no key function, the key argument to sorted is an
        # itemgetter
        key_argument = itemgetter(*key_list)
    else:
        # if there is a key function, call it with the items at the offsets
        # specified by the key function as arguments
        key_list = list(key_list)
        if len(key_list) == 1:
            # if key_list contains a single item, pass the item at that offset
            # as the only argument to the key function
            key_offset = key_list[0]
            key_argument = lambda zipped_items: key(zipped_items[key_offset])
        else:
            # if key_list contains multiple items, use itemgetter to return a
            # tuple of items, which we pass as *args to the key function
            get_key_items = itemgetter(*key_list)
            key_argument = lambda zipped_items: key(
                *get_key_items(zipped_items)
            )

    return list(
        zip(*sorted(zip(*iterables), key=key_argument, reverse=reverse))
    )


def unzip(iterable):
    """The inverse of :func:`zip`, this function disaggregates the elements
    of the zipped *iterable*.

    The ``i``-th iterable contains the ``i``-th element from each element
    of the zipped iterable. The first element is used to to determine the
    length of the remaining elements.

        >>> iterable = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
        >>> letters, numbers = unzip(iterable)
        >>> list(letters)
        ['a', 'b', 'c', 'd']
        >>> list(numbers)
        [1, 2, 3, 4]

    This is similar to using ``zip(*iterable)``, but it avoids reading
    *iterable* into memory. Note, however, that this function uses
    :func:`itertools.tee` and thus may require significant storage.

    """
    head, iterable = spy(iter(iterable))
    if not head:
        # empty iterable, e.g. zip([], [], [])
        return ()
    # spy returns a one-length iterable as head
    head = head[0]
    iterables = tee(iterable, len(head))

    def itemgetter(i):
        def getter(obj):
            try:
                return obj[i]
            except IndexError:
                # basically if we have an iterable like
                # iter([(1, 2, 3), (4, 5), (6,)])
                # the second unzipped iterable would fail at the third tuple
                # since it would try to access tup[1]
                # same with the third unzipped iterable and the second tuple
                # to support these "improperly zipped" iterables,
                # we create a custom itemgetter
                # which just stops the unzipped iterables
                # at first length mismatch
                raise StopIteration

        return getter

    return tuple(map(itemgetter(i), it) for i, it in enumerate(iterables))


def divide(n, iterable):
    """Divide the elements from *iterable* into *n* parts, maintaining
    order.

        >>> group_1, group_2 = divide(2, [1, 2, 3, 4, 5, 6])
        >>> list(group_1)
        [1, 2, 3]
        >>> list(group_2)
        [4, 5, 6]

    If the length of *iterable* is not evenly divisible by *n*, then the
    length of the returned iterables will not be identical:

        >>> children = divide(3, [1, 2, 3, 4, 5, 6, 7])
        >>> [list(c) for c in children]
        [[1, 2, 3], [4, 5], [6, 7]]

    If the length of the iterable is smaller than n, then the last returned
    iterables will be empty:

        >>> children = divide(5, [1, 2, 3])
        >>> [list(c) for c in children]
        [[1], [2], [3], [], []]

    This function will exhaust the iterable before returning and may require
    significant storage. If order is not important, see :func:`distribute`,
    which does not first pull the iterable into memory.

    """
    if n < 1:
        raise ValueError('n must be at least 1')

    try:
        iterable[:0]
    except TypeError:
        seq = tuple(iterable)
    else:
        seq = iterable

    q, r = divmod(len(seq), n)

    ret = []
    stop = 0
    for i in range(1, n + 1):
        start = stop
        stop += q + 1 if i <= r else q
        ret.append(iter(seq[start:stop]))

    return ret


def always_iterable(obj, base_type=(str, bytes)):
    """If *obj* is iterable, return an iterator over its items::

        >>> obj = (1, 2, 3)
        >>> list(always_iterable(obj))
        [1, 2, 3]

    If *obj* is not iterable, return a one-item iterable containing *obj*::

        >>> obj = 1
        >>> list(always_iterable(obj))
        [1]

    If *obj* is ``None``, return an empty iterable:

        >>> obj = None
        >>> list(always_iterable(None))
        []

    By default, binary and text strings are not considered iterable::

        >>> obj = 'foo'
        >>> list(always_iterable(obj))
        ['foo']

    If *base_type* is set, objects for which ``isinstance(obj, base_type)``
    returns ``True`` won't be considered iterable.

        >>> obj = {'a': 1}
        >>> list(always_iterable(obj))  # Iterate over the dict's keys
        ['a']
        >>> list(always_iterable(obj, base_type=dict))  # Treat dicts as a unit
        [{'a': 1}]

    Set *base_type* to ``None`` to avoid any special handling and treat objects
    Python considers iterable as iterable:

        >>> obj = 'foo'
        >>> list(always_iterable(obj, base_type=None))
        ['f', 'o', 'o']
    """
    if obj is None:
        return iter(())

    if (base_type is not None) and isinstance(obj, base_type):
        return iter((obj,))

    try:
        return iter(obj)
    except TypeError:
        return iter((obj,))


def adjacent(predicate, iterable, distance=1):
    """Return an iterable over `(bool, item)` tuples where the `item` is
    drawn from *iterable* and the `bool` indicates whether
    that item satisfies the *predicate* or is adjacent to an item that does.

    For example, to find whether items are adjacent to a ``3``::

        >>> list(adjacent(lambda x: x == 3, range(6)))
        [(False, 0), (False, 1), (True, 2), (True, 3), (True, 4), (False, 5)]

    Set *distance* to change what counts as adjacent. For example, to find
    whether items are two places away from a ``3``:

        >>> list(adjacent(lambda x: x == 3, range(6), distance=2))
        [(False, 0), (True, 1), (True, 2), (True, 3), (True, 4), (True, 5)]

    This is useful for contextualizing the results of a search function.
    For example, a code comparison tool might want to identify lines that
    have changed, but also surrounding lines to give the viewer of the diff
    context.

    The predicate function will only be called once for each item in the
    iterable.

    See also :func:`groupby_transform`, which can be used with this function
    to group ranges of items with the same `bool` value.

    """
    # Allow distance=0 mainly for testing that it reproduces results with map()
    if distance < 0:
        raise ValueError('distance must be at least 0')

    i1, i2 = tee(iterable)
    padding = [False] * distance
    selected = chain(padding, map(predicate, i1), padding)
    adjacent_to_selected = map(any, windowed(selected, 2 * distance + 1))
    return zip(adjacent_to_selected, i2)


def groupby_transform(iterable, keyfunc=None, valuefunc=None, reducefunc=None):
    """An extension of :func:`itertools.groupby` that can apply transformations
    to the grouped data.

    * *keyfunc* is a function computing a key value for each item in *iterable*
    * *valuefunc* is a function that transforms the individual items from
      *iterable* after grouping
    * *reducefunc* is a function that transforms each group of items

    >>> iterable = 'aAAbBBcCC'
    >>> keyfunc = lambda k: k.upper()
    >>> valuefunc = lambda v: v.lower()
    >>> reducefunc = lambda g: ''.join(g)
    >>> list(groupby_transform(iterable, keyfunc, valuefunc, reducefunc))
    [('A', 'aaa'), ('B', 'bbb'), ('C', 'ccc')]

    Each optional argument defaults to an identity function if not specified.

    :func:`groupby_transform` is useful when grouping elements of an iterable
    using a separate iterable as the key. To do this, :func:`zip` the iterables
    and pass a *keyfunc* that extracts the first element and a *valuefunc*
    that extracts the second element::

        >>> from operator import itemgetter
        >>> keys = [0, 0, 1, 1, 1, 2, 2, 2, 3]
        >>> values = 'abcdefghi'
        >>> iterable = zip(keys, values)
        >>> grouper = groupby_transform(iterable, itemgetter(0), itemgetter(1))
        >>> [(k, ''.join(g)) for k, g in grouper]
        [(0, 'ab'), (1, 'cde'), (2, 'fgh'), (3, 'i')]

    Note that the order of items in the iterable is significant.
    Only adjacent items are grouped together, so if you don't want any
    duplicate groups, you should sort the iterable by the key function.

    """
    ret = groupby(iterable, keyfunc)
    if valuefunc:
        ret = ((k, map(valuefunc, g)) for k, g in ret)
    if reducefunc:
        ret = ((k, reducefunc(g)) for k, g in ret)

    return ret


class numeric_range(abc.Sequence, abc.Hashable):
    """An extension of the built-in ``range()`` function whose arguments can
    be any orderable numeric type.

    With only *stop* specified, *start* defaults to ``0`` and *step*
    defaults to ``1``. The output items will match the type of *stop*:

        >>> list(numeric_range(3.5))
        [0.0, 1.0, 2.0, 3.0]

    With only *start* and *stop* specified, *step* defaults to ``1``. The
    output items will match the type of *start*:

        >>> from decimal import Decimal
        >>> start = Decimal('2.1')
        >>> stop = Decimal('5.1')
        >>> list(numeric_range(start, stop))
        [Decimal('2.1'), Decimal('3.1'), Decimal('4.1')]

    With *start*, *stop*, and *step*  specified the output items will match
    the type of ``start + step``:

        >>> from fractions import Fraction
        >>> start = Fraction(1, 2)  # Start at 1/2
        >>> stop = Fraction(5, 2)  # End at 5/2
        >>> step = Fraction(1, 2)  # Count by 1/2
        >>> list(numeric_range(start, stop, step))
        [Fraction(1, 2), Fraction(1, 1), Fraction(3, 2), Fraction(2, 1)]

    If *step* is zero, ``ValueError`` is raised. Negative steps are supported:

        >>> list(numeric_range(3, -1, -1.0))
        [3.0, 2.0, 1.0, 0.0]

    Be aware of the limitations of floating point numbers; the representation
    of the yielded numbers may be surprising.

    ``datetime.datetime`` objects can be used for *start* and *stop*, if *step*
    is a ``datetime.timedelta`` object:

        >>> import datetime
        >>> start = datetime.datetime(2019, 1, 1)
        >>> stop = datetime.datetime(2019, 1, 3)
        >>> step = datetime.timedelta(days=1)
        >>> items = iter(numeric_range(start, stop, step))
        >>> next(items)
        datetime.datetime(2019, 1, 1, 0, 0)
        >>> next(items)
        datetime.datetime(2019, 1, 2, 0, 0)

    """

    _EMPTY_HASH = hash(range(0, 0))

    def __init__(self, *args):
        argc = len(args)
        if argc == 1:
            (self._stop,) = args
            self._start = type(self._stop)(0)
            self._step = type(self._stop - self._start)(1)
        elif argc == 2:
            self._start, self._stop = args
            self._step = type(self._stop - self._start)(1)
        elif argc == 3:
            self._start, self._stop, self._step = args
        elif argc == 0:
            raise TypeError(
                'numeric_range expected at least '
                '1 argument, got {}'.format(argc)
            )
        else:
            raise TypeError(
                'numeric_range expected at most '
                '3 arguments, got {}'.format(argc)
            )

        self._zero = type(self._step)(0)
        if self._step == self._zero:
            raise ValueError('numeric_range() arg 3 must not be zero')
        self._growing = self._step > self._zero
        self._init_len()

    def __bool__(self):
        if self._growing:
            return self._start < self._stop
        else:
            return self._start > self._stop

    def __contains__(self, elem):
        if self._growing:
            if self._start <= elem < self._stop:
                return (elem - self._start) % self._step == self._zero
        else:
            if self._start >= elem > self._stop:
                return (self._start - elem) % (-self._step) == self._zero

        return False

    def __eq__(self, other):
        if isinstance(other, numeric_range):
            empty_self = not bool(self)
            empty_other = not bool(other)
            if empty_self or empty_other:
                return empty_self and empty_other  # True if both empty
            else:
                return (
                    self._start == other._start
                    and self._step == other._step
                    and self._get_by_index(-1) == other._get_by_index(-1)
                )
        else:
            return False

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._get_by_index(key)
        elif isinstance(key, slice):
            step = self._step if key.step is None else key.step * self._step

            if key.start is None or key.start <= -self._len:
                start = self._start
            elif key.start >= self._len:
                start = self._stop
            else:  # -self._len < key.start < self._len
                start = self._get_by_index(key.start)

            if key.stop is None or key.stop >= self._len:
                stop = self._stop
            elif key.stop <= -self._len:
                stop = self._start
            else:  # -self._len < key.stop < self._len
                stop = self._get_by_index(key.stop)

            return numeric_range(start, stop, step)
        else:
            raise TypeError(
                'numeric range indices must be '
                'integers or slices, not {}'.format(type(key).__name__)
            )

    def __hash__(self):
        if self:
            return hash((self._start, self._get_by_index(-1), self._step))
        else:
            return self._EMPTY_HASH

    def __iter__(self):
        values = (self._start + (n * self._step) for n in count())
        if self._growing:
            return takewhile(partial(gt, self._stop), values)
        else:
            return takewhile(partial(lt, self._stop), values)

    def __len__(self):
        return self._len

    def _init_len(self):
        if self._growing:
            start = self._start
            stop = self._stop
            step = self._step
        else:
            start = self._stop
            stop = self._start
            step = -self._step
        distance = stop - start
        if distance <= self._zero:
            self._len = 0
        else:  # distance > 0 and step > 0: regular euclidean division
            q, r = divmod(distance, step)
            self._len = int(q) + int(r != self._zero)

    def __reduce__(self):
        return numeric_range, (self._start, self._stop, self._step)

    def __repr__(self):
        if self._step == 1:
            return "numeric_range({}, {})".format(
                repr(self._start), repr(self._stop)
            )
        else:
            return "numeric_range({}, {}, {})".format(
                repr(self._start), repr(self._stop), repr(self._step)
            )

    def __reversed__(self):
        return iter(
            numeric_range(
                self._get_by_index(-1), self._start - self._step, -self._step
            )
        )

    def count(self, value):
        return int(value in self)

    def index(self, value):
        if self._growing:
            if self._start <= value < self._stop:
                q, r = divmod(value - self._start, self._step)
                if r == self._zero:
                    return int(q)
        else:
            if self._start >= value > self._stop:
                q, r = divmod(self._start - value, -self._step)
                if r == self._zero:
                    return int(q)

        raise ValueError("{} is not in numeric range".format(value))

    def _get_by_index(self, i):
        if i < 0:
            i += self._len
        if i < 0 or i >= self._len:
            raise IndexError("numeric range object index out of range")
        return self._start + i * self._step


def count_cycle(iterable, n=None):
    """Cycle through the items from *iterable* up to *n* times, yielding
    the number of completed cycles along with each item. If *n* is omitted the
    process repeats indefinitely.

    >>> list(count_cycle('AB', 3))
    [(0, 'A'), (0, 'B'), (1, 'A'), (1, 'B'), (2, 'A'), (2, 'B')]

    """
    iterable = tuple(iterable)
    if not iterable:
        return iter(())
    counter = count() if n is None else range(n)
    return ((i, item) for i in counter for item in iterable)


def mark_ends(iterable):
    """Yield 3-tuples of the form ``(is_first, is_last, item)``.

    >>> list(mark_ends('ABC'))
    [(True, False, 'A'), (False, False, 'B'), (False, True, 'C')]

    Use this when looping over an iterable to take special action on its first
    and/or last items:

    >>> iterable = ['Header', 100, 200, 'Footer']
    >>> total = 0
    >>> for is_first, is_last, item in mark_ends(iterable):
    ...     if is_first:
    ...         continue  # Skip the header
    ...     if is_last:
    ...         continue  # Skip the footer
    ...     total += item
    >>> print(total)
    300
    """
    it = iter(iterable)

    try:
        b = next(it)
    except StopIteration:
        return

    try:
        for i in count():
            a = b
            b = next(it)
            yield i == 0, False, a

    except StopIteration:
        yield i == 0, True, a


def locate(iterable, pred=bool, window_size=None):
    """Yield the index of each item in *iterable* for which *pred* returns
    ``True``.

    *pred* defaults to :func:`bool`, which will select truthy items:

        >>> list(locate([0, 1, 1, 0, 1, 0, 0]))
        [1, 2, 4]

    Set *pred* to a custom function to, e.g., find the indexes for a particular
    item.

        >>> list(locate(['a', 'b', 'c', 'b'], lambda x: x == 'b'))
        [1, 3]

    If *window_size* is given, then the *pred* function will be called with
    that many items. This enables searching for sub-sequences:

        >>> iterable = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
        >>> pred = lambda *args: args == (1, 2, 3)
        >>> list(locate(iterable, pred=pred, window_size=3))
        [1, 5, 9]

    Use with :func:`seekable` to find indexes and then retrieve the associated
    items:

        >>> from itertools import count
        >>> from more_itertools import seekable
        >>> source = (3 * n + 1 if (n % 2) else n // 2 for n in count())
        >>> it = seekable(source)
        >>> pred = lambda x: x > 100
        >>> indexes = locate(it, pred=pred)
        >>> i = next(indexes)
        >>> it.seek(i)
        >>> next(it)
        106

    """
    if window_size is None:
        return compress(count(), map(pred, iterable))

    if window_size < 1:
        raise ValueError('window size must be at least 1')

    it = windowed(iterable, window_size, fillvalue=_marker)
    return compress(count(), starmap(pred, it))


def lstrip(iterable, pred):
    """Yield the items from *iterable*, but strip any from the beginning
    for which *pred* returns ``True``.

    For example, to remove a set of items from the start of an iterable:

        >>> iterable = (None, False, None, 1, 2, None, 3, False, None)
        >>> pred = lambda x: x in {None, False, ''}
        >>> list(lstrip(iterable, pred))
        [1, 2, None, 3, False, None]

    This function is analogous to to :func:`str.lstrip`, and is essentially
    an wrapper for :func:`itertools.dropwhile`.

    """
    return dropwhile(pred, iterable)


def rstrip(iterable, pred):
    """Yield the items from *iterable*, but strip any from the end
    for which *pred* returns ``True``.

    For example, to remove a set of items from the end of an iterable:

        >>> iterable = (None, False, None, 1, 2, None, 3, False, None)
        >>> pred = lambda x: x in {None, False, ''}
        >>> list(rstrip(iterable, pred))
        [None, False, None, 1, 2, None, 3]

    This function is analogous to :func:`str.rstrip`.

    """
    cache = []
    cache_append = cache.append
    cache_clear = cache.clear
    for x in iterable:
        if pred(x):
            cache_append(x)
        else:
            yield from cache
            cache_clear()
            yield x


def strip(iterable, pred):
    """Yield the items from *iterable*, but strip any from the
    beginning and end for which *pred* returns ``True``.

    For example, to remove a set of items from both ends of an iterable:

        >>> iterable = (None, False, None, 1, 2, None, 3, False, None)
        >>> pred = lambda x: x in {None, False, ''}
        >>> list(strip(iterable, pred))
        [1, 2, None, 3]

    This function is analogous to :func:`str.strip`.

    """
    return rstrip(lstrip(iterable, pred), pred)


class islice_extended:
    """An extension of :func:`itertools.islice` that supports negative values
    for *stop*, *start*, and *step*.

        >>> iterable = iter('abcdefgh')
        >>> list(islice_extended(iterable, -4, -1))
        ['e', 'f', 'g']

    Slices with negative values require some caching of *iterable*, but this
    function takes care to minimize the amount of memory required.

    For example, you can use a negative step with an infinite iterator:

        >>> from itertools import count
        >>> list(islice_extended(count(), 110, 99, -2))
        [110, 108, 106, 104, 102, 100]

    You can also use slice notation directly:

        >>> iterable = map(str, count())
        >>> it = islice_extended(iterable)[10:20:2]
        >>> list(it)
        ['10', '12', '14', '16', '18']

    """

    def __init__(self, iterable, *args):
        it = iter(iterable)
        if args:
            self._iterable = _islice_helper(it, slice(*args))
        else:
            self._iterable = it

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iterable)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return islice_extended(_islice_helper(self._iterable, key))

        raise TypeError('islice_extended.__getitem__ argument must be a slice')


def _islice_helper(it, s):
    start = s.start
    stop = s.stop
    if s.step == 0:
        raise ValueError('step argument must be a non-zero integer or None.')
    step = s.step or 1

    if step > 0:
        start = 0 if (start is None) else start

        if start < 0:
            # Consume all but the last -start items
            cache = deque(enumerate(it, 1), maxlen=-start)
            len_iter = cache[-1][0] if cache else 0

            # Adjust start to be positive
            i = max(len_iter + start, 0)

            # Adjust stop to be positive
            if stop is None:
                j = len_iter
            elif stop >= 0:
                j = min(stop, len_iter)
            else:
                j = max(len_iter + stop, 0)

            # Slice the cache
            n = j - i
            if n <= 0:
                return

            for index, item in islice(cache, 0, n, step):
                yield item
        elif (stop is not None) and (stop < 0):
            # Advance to the start position
            next(islice(it, start, start), None)

            # When stop is negative, we have to carry -stop items while
            # iterating
            cache = deque(islice(it, -stop), maxlen=-stop)

            for index, item in enumerate(it):
                cached_item = cache.popleft()
                if index % step == 0:
                    yield cached_item
                cache.append(item)
        else:
            # When both start and stop are positive we have the normal case
            yield from islice(it, start, stop, step)
    else:
        start = -1 if (start is None) else start

        if (stop is not None) and (stop < 0):
            # Consume all but the last items
            n = -stop - 1
            cache = deque(enumerate(it, 1), maxlen=n)
            len_iter = cache[-1][0] if cache else 0

            # If start and stop are both negative they are comparable and
            # we can just slice. Otherwise we can adjust start to be negative
            # and then slice.
            if start < 0:
                i, j = start, stop
            else:
                i, j = min(start - len_iter, -1), None

            for index, item in list(cache)[i:j:step]:
                yield item
        else:
            # Advance to the stop position
            if stop is not None:
                m = stop + 1
                next(islice(it, m, m), None)

            # stop is positive, so if start is negative they are not comparable
            # and we need the rest of the items.
            if start < 0:
                i = start
                n = None
            # stop is None and start is positive, so we just need items up to
            # the start index.
            elif stop is None:
                i = None
                n = start + 1
            # Both stop and start are positive, so they are comparable.
            else:
                i = None
                n = start - stop
                if n <= 0:
                    return

            cache = list(islice(it, n))

            yield from cache[i::step]


def always_reversible(iterable):
    """An extension of :func:`reversed` that supports all iterables, not
    just those which implement the ``Reversible`` or ``Sequence`` protocols.

        >>> print(*always_reversible(x for x in range(3)))
        2 1 0

    If the iterable is already reversible, this function returns the
    result of :func:`reversed()`. If the iterable is not reversible,
    this function will cache the remaining items in the iterable and
    yield them in reverse order, which may require significant storage.
    """
    try:
        return reversed(iterable)
    except TypeError:
        return reversed(list(iterable))


def consecutive_groups(iterable, ordering=lambda x: x):
    """Yield groups of consecutive items using :func:`itertools.groupby`.
    The *ordering* function determines whether two items are adjacent by
    returning their position.

    By default, the ordering function is the identity function. This is
    suitable for finding runs of numbers:

        >>> iterable = [1, 10, 11, 12, 20, 30, 31, 32, 33, 40]
        >>> for group in consecutive_groups(iterable):
        ...     print(list(group))
        [1]
        [10, 11, 12]
        [20]
        [30, 31, 32, 33]
        [40]

    For finding runs of adjacent letters, try using the :meth:`index` method
    of a string of letters:

        >>> from string import ascii_lowercase
        >>> iterable = 'abcdfgilmnop'
        >>> ordering = ascii_lowercase.index
        >>> for group in consecutive_groups(iterable, ordering):
        ...     print(list(group))
        ['a', 'b', 'c', 'd']
        ['f', 'g']
        ['i']
        ['l', 'm', 'n', 'o', 'p']

    Each group of consecutive items is an iterator that shares it source with
    *iterable*. When an an output group is advanced, the previous group is
    no longer available unless its elements are copied (e.g., into a ``list``).

        >>> iterable = [1, 2, 11, 12, 21, 22]
        >>> saved_groups = []
        >>> for group in consecutive_groups(iterable):
        ...     saved_groups.append(list(group))  # Copy group elements
        >>> saved_groups
        [[1, 2], [11, 12], [21, 22]]

    """
    for k, g in groupby(
        enumerate(iterable), key=lambda x: x[0] - ordering(x[1])
    ):
        yield map(itemgetter(1), g)


def difference(iterable, func=sub, *, initial=None):
    """This function is the inverse of :func:`itertools.accumulate`. By default
    it will compute the first difference of *iterable* using
    :func:`operator.sub`:

        >>> from itertools import accumulate
        >>> iterable = accumulate([0, 1, 2, 3, 4])  # produces 0, 1, 3, 6, 10
        >>> list(difference(iterable))
        [0, 1, 2, 3, 4]

    *func* defaults to :func:`operator.sub`, but other functions can be
    specified. They will be applied as follows::

        A, B, C, D, ... --> A, func(B, A), func(C, B), func(D, C), ...

    For example, to do progressive division:

        >>> iterable = [1, 2, 6, 24, 120]
        >>> func = lambda x, y: x // y
        >>> list(difference(iterable, func))
        [1, 2, 3, 4, 5]

    If the *initial* keyword is set, the first element will be skipped when
    computing successive differences.

        >>> it = [10, 11, 13, 16]  # from accumulate([1, 2, 3], initial=10)
        >>> list(difference(it, initial=10))
        [1, 2, 3]

    """
    a, b = tee(iterable)
    try:
        first = [next(b)]
    except StopIteration:
        return iter([])

    if initial is not None:
        first = []

    return chain(first, starmap(func, zip(b, a)))


class SequenceView(Sequence):
    """Return a read-only view of the sequence object *target*.

    :class:`SequenceView` objects are analogous to Python's built-in
    "dictionary view" types. They provide a dynamic view of a sequence's items,
    meaning that when the sequence updates, so does the view.

        >>> seq = ['0', '1', '2']
        >>> view = SequenceView(seq)
        >>> view
        SequenceView(['0', '1', '2'])
        >>> seq.append('3')
        >>> view
        SequenceView(['0', '1', '2', '3'])

    Sequence views support indexing, slicing, and length queries. They act
    like the underlying sequence, except they don't allow assignment:

        >>> view[1]
        '1'
        >>> view[1:-1]
        ['1', '2']
        >>> len(view)
        4

    Sequence views are useful as an alternative to copying, as they don't
    require (much) extra storage.

    """

    def __init__(self, target):
        if not isinstance(target, Sequence):
            raise TypeError
        self._target = target

    def __getitem__(self, index):
        return self._target[index]

    def __len__(self):
        return len(self._target)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self._target))


class seekable:
    """Wrap an iterator to allow for seeking backward and forward. This
    progressively caches the items in the source iterable so they can be
    re-visited.

    Call :meth:`seek` with an index to seek to that position in the source
    iterable.

    To "reset" an iterator, seek to ``0``:

        >>> from itertools import count
        >>> it = seekable((str(n) for n in count()))
        >>> next(it), next(it), next(it)
        ('0', '1', '2')
        >>> it.seek(0)
        >>> next(it), next(it), next(it)
        ('0', '1', '2')
        >>> next(it)
        '3'

    You can also seek forward:

        >>> it = seekable((str(n) for n in range(20)))
        >>> it.seek(10)
        >>> next(it)
        '10'
        >>> it.seek(20)  # Seeking past the end of the source isn't a problem
        >>> list(it)
        []
        >>> it.seek(0)  # Resetting works even after hitting the end
        >>> next(it), next(it), next(it)
        ('0', '1', '2')

    Call :meth:`peek` to look ahead one item without advancing the iterator:

        >>> it = seekable('1234')
        >>> it.peek()
        '1'
        >>> list(it)
        ['1', '2', '3', '4']
        >>> it.peek(default='empty')
        'empty'

    Before the iterator is at its end, calling :func:`bool` on it will return
    ``True``. After it will return ``False``:

        >>> it = seekable('5678')
        >>> bool(it)
        True
        >>> list(it)
        ['5', '6', '7', '8']
        >>> bool(it)
        False

    You may view the contents of the cache with the :meth:`elements` method.
    That returns a :class:`SequenceView`, a view that updates automatically:

        >>> it = seekable((str(n) for n in range(10)))
        >>> next(it), next(it), next(it)
        ('0', '1', '2')
        >>> elements = it.elements()
        >>> elements
        SequenceView(['0', '1', '2'])
        >>> next(it)
        '3'
        >>> elements
        SequenceView(['0', '1', '2', '3'])

    By default, the cache grows as the source iterable progresses, so beware of
    wrapping very large or infinite iterables. Supply *maxlen* to limit the
    size of the cache (this of course limits how far back you can seek).

        >>> from itertools import count
        >>> it = seekable((str(n) for n in count()), maxlen=2)
        >>> next(it), next(it), next(it), next(it)
        ('0', '1', '2', '3')
        >>> list(it.elements())
        ['2', '3']
        >>> it.seek(0)
        >>> next(it), next(it), next(it), next(it)
        ('2', '3', '4', '5')
        >>> next(it)
        '6'

    """

    def __init__(self, iterable, maxlen=None):
        self._source = iter(iterable)
        if maxlen is None:
            self._cache = []
        else:
            self._cache = deque([], maxlen)
        self._index = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._index is not None:
            try:
                item = self._cache[self._index]
            except IndexError:
                self._index = None
            else:
                self._index += 1
                return item

        item = next(self._source)
        self._cache.append(item)
        return item

    def __bool__(self):
        try:
            self.peek()
        except StopIteration:
            return False
        return True

    def peek(self, default=_marker):
        try:
            peeked = next(self)
        except StopIteration:
            if default is _marker:
                raise
            return default
        if self._index is None:
            self._index = len(self._cache)
        self._index -= 1
        return peeked

    def elements(self):
        return SequenceView(self._cache)

    def seek(self, index):
        self._index = index
        remainder = index - len(self._cache)
        if remainder > 0:
            consume(self, remainder)


class run_length:
    """
    :func:`run_length.encode` compresses an iterable with run-length encoding.
    It yields groups of repeated items with the count of how many times they
    were repeated:

        >>> uncompressed = 'abbcccdddd'
        >>> list(run_length.encode(uncompressed))
        [('a', 1), ('b', 2), ('c', 3), ('d', 4)]

    :func:`run_length.decode` decompresses an iterable that was previously
    compressed with run-length encoding. It yields the items of the
    decompressed iterable:

        >>> compressed = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
        >>> list(run_length.decode(compressed))
        ['a', 'b', 'b', 'c', 'c', 'c', 'd', 'd', 'd', 'd']

    """

    @staticmethod
    def encode(iterable):
        return ((k, ilen(g)) for k, g in groupby(iterable))

    @staticmethod
    def decode(iterable):
        return chain.from_iterable(repeat(k, n) for k, n in iterable)


def exactly_n(iterable, n, predicate=bool):
    """Return ``True`` if exactly ``n`` items in the iterable are ``True``
    according to the *predicate* function.

        >>> exactly_n([True, True, False], 2)
        True
        >>> exactly_n([True, True, False], 1)
        False
        >>> exactly_n([0, 1, 2, 3, 4, 5], 3, lambda x: x < 3)
        True

    The iterable will be advanced until ``n + 1`` truthy items are encountered,
    so avoid calling it on infinite iterables.

    """
    return len(take(n + 1, filter(predicate, iterable))) == n


def circular_shifts(iterable):
    """Return a list of circular shifts of *iterable*.

    >>> circular_shifts(range(4))
    [(0, 1, 2, 3), (1, 2, 3, 0), (2, 3, 0, 1), (3, 0, 1, 2)]
    """
    lst = list(iterable)
    return take(len(lst), windowed(cycle(lst), len(lst)))


def make_decorator(wrapping_func, result_index=0):
    """Return a decorator version of *wrapping_func*, which is a function that
    modifies an iterable. *result_index* is the position in that function's
    signature where the iterable goes.

    This lets you use itertools on the "production end," i.e. at function
    definition. This can augment what the function returns without changing the
    function's code.

    For example, to produce a decorator version of :func:`chunked`:

        >>> from more_itertools import chunked
        >>> chunker = make_decorator(chunked, result_index=0)
        >>> @chunker(3)
        ... def iter_range(n):
        ...     return iter(range(n))
        ...
        >>> list(iter_range(9))
        [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

    To only allow truthy items to be returned:

        >>> truth_serum = make_decorator(filter, result_index=1)
        >>> @truth_serum(bool)
        ... def boolean_test():
        ...     return [0, 1, '', ' ', False, True]
        ...
        >>> list(boolean_test())
        [1, ' ', True]

    The :func:`peekable` and :func:`seekable` wrappers make for practical
    decorators:

        >>> from more_itertools import peekable
        >>> peekable_function = make_decorator(peekable)
        >>> @peekable_function()
        ... def str_range(*args):
        ...     return (str(x) for x in range(*args))
        ...
        >>> it = str_range(1, 20, 2)
        >>> next(it), next(it), next(it)
        ('1', '3', '5')
        >>> it.peek()
        '7'
        >>> next(it)
        '7'

    """