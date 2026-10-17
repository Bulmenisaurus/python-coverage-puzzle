# Line 416: _PyList_GetItemRef
# Callers:
# - _PyBytes_FromList, line 2886
#  - PyBytes_FromObject, line 3031

from test.support import import_helper
bytes([1])

# Line 726, in PyList_GetSlice

_testlimitedcapi = import_helper.import_module('_testlimitedcapi')

getslice = _testlimitedcapi.list_getslice
lst = [1, 2, 3]

getslice(lst, 4, 2)  # trigger ilow > Py_SIZE(a) and ihigh < ilow

# list_concat_lock_held
[] + []

# list_concat
try:
    [] + {}
except TypeError:
    pass

# list_ass_slice 998
# called by PyList_SetSlice
setslice = _testlimitedcapi.list_setslice
a = [1, 2, 3]
setslice(a, 0, 2, a)


# merge_at (ai generated!)
def ascending_runs(lengths):
    out = []
    for n in lengths:
        out.extend(range(n))
    return out


data = ascending_runs([144, 32, 32, 48])
data.sort()

# unsafe_object_compare


class A(list):
    def __eq__(self, other):
        return "oops"


print(A() == [])
