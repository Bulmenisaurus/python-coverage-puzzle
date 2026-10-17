# line 416:

'''
415 PyObject *
416 _PyList_GetItemRef(PyListObject *list, Py_ssize_t i)
417 {
418    return list_get_item_ref(list, i);
419 }
'''

# added in commit https://github.com/python/cpython//commit/e2713409cff5b71b1176b0e3fa63dae447548672
# seems to be a specific subscript operator for specialization?

arr = [0]

for i in range(100):
    arr[0]
