def test_list_resize_overflow(self):
    # gh-97616: test new_allocated * sizeof(PyObject*) overflow
    # check in list_resize()
    lst = [0] * 65
    del lst[1:]
    self.assertEqual(len(lst), 1)
    size = ((2 ** (tuple.__itemsize__ * 8) - 1) // 2)
    with self.assertRaises((MemoryError, OverflowError)):
        lst * size
    with self.assertRaises((MemoryError, OverflowError)):
        lst *= size
