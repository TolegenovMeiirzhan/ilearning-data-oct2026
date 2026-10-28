import unittest
from forbiddenfruit import curse
import timeout_decorator

from xor_linked_list import *

def times(self, f):
    for i in range(self): f(i)

curse(int, "times", times)

class TestXorLinkedList(unittest.TestCase):
    def test_Count_EmptyList_ReturnsZero(self):

        self.assertEqual(len(XorLinkedList()), 0)

    def test_First_EmptyList_ReturnsNotFound(self):

        self.assertEqual(XorLinkedList().first, XorLinkedList.NOT_FOUND);

    def test_Last_EmptyList_ReturnsNotFound(self):

        self.assertEqual(XorLinkedList().last, XorLinkedList.NOT_FOUND);

    def test_Empty_EmptyList_ReturnsTrue(self):

        self.assertTrue(not XorLinkedList());
        self.assertTrue(XorLinkedList().empty);

    def test_Last_ReturnsLastElementAddress(self):

        xorll = XorLinkedList()
        xorll.append(0)
        xorll.append(1)
        xorll.append(2)
        self.assertEqual(xorll.last, XorLinkedList.ELEMENT_SIZE * 2)

    def test_First_ReturnsFirstElementAddress(self):

        xorll = XorLinkedList()
        xorll.prepend(0)
        xorll.prepend(1)
        xorll.prepend(2)
        self.assertEqual(xorll.first, XorLinkedList.ELEMENT_SIZE * 2)


    def test_EnsureCapacity_ListDoesNotGrowIfUnnecessary(self):

        xorll = XorLinkedList()
        self.assertEqual(xorll.size, 0)
        self.assertEqual(xorll.capacity, XorLinkedList.INITIAL_CAPACITY)
        XorLinkedList.INITIAL_CAPACITY.times(lambda _:
            xorll.allocate(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND))
        self.assertEqual(xorll.size, XorLinkedList.INITIAL_CAPACITY)
        self.assertEqual(xorll.capacity, XorLinkedList.INITIAL_CAPACITY)


    def test_EnsureCapacity_DoublesCapacity(self):

        xorll = XorLinkedList()
        (XorLinkedList.INITIAL_CAPACITY + 1).times(lambda _:
            xorll.allocate(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND))
        self.assertNotEqual(xorll.capacity, XorLinkedList.INITIAL_CAPACITY)
        self.assertEqual(xorll.capacity // XorLinkedList.INITIAL_CAPACITY, 2)
        (XorLinkedList.INITIAL_CAPACITY + 1).times(lambda _:
            xorll.allocate(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND))
        self.assertEqual(xorll.capacity // XorLinkedList.INITIAL_CAPACITY, 4)

    def test_Buffer_HasProperSize(self):

        xorll = XorLinkedList()
        multiplier = xorll.buffer.itemsize * XorLinkedList.ELEMENT_SIZE
        self.assertEqual(xorll.buffer.nbytes, XorLinkedList.INITIAL_CAPACITY * multiplier)
        XorLinkedList.INITIAL_CAPACITY.times(lambda _:
            xorll.allocate(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND))
        self.assertEqual(xorll.buffer.nbytes, xorll.capacity * multiplier)

    def test_Allocate_IncreasesListSize(self):

        xorll = XorLinkedList()
        xorll.allocate(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND);
        self.assertEqual(xorll.size, 1);
        xorll.allocate(1, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND);
        self.assertEqual(xorll.size, 2);  

    def test_Allocate_StoresValue(self):

        xorll = XorLinkedList()
        self.assertNotIn(42, xorll.buffer)
        xorll.allocate(42, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND);
        self.assertIn(42, xorll.buffer)

    def test_Empty_NonEmptyList_ReturnsFalse(self):

        xorll = XorLinkedList()
        xorll.append(42)
        self.assertFalse(xorll.empty)

    def test_Append_IncreasesSize(self):

        xorll = XorLinkedList()
        xorll.append(0)
        self.assertEqual(xorll.size, 1)
        xorll.append(1)
        self.assertEqual(xorll.size, 2)

    def test_Append_StoresValue(self):

        xorll = XorLinkedList()
        self.assertEqual(list(xorll), []);
        xorll.append(42);
        self.assertEqual(list(xorll), [42]);
    

    def test_Append_AcceptsUintValues(self):

        xorll = XorLinkedList()
        xorll.append(0xFFFF_FFFF)
        self.assertEqual(list(xorll), [0xFFFF_FFFF]);
        xorll.append(0);
        self.assertEqual(list(xorll), [0xFFFF_FFFF, 0]);
        xorll.append(1);
        self.assertEqual(list(xorll), [0xFFFF_FFFF, 0, 1]);
        xorll.append(-1 & 0xFFFF_FFFF)
        self.assertEqual(list(xorll), [0xFFFF_FFFF, 0, 1, 0xFFFF_FFFF]);


    def test_Append_PreservesOrder(self):

        xorll = XorLinkedList()
        xorll.append(0)
        xorll.append(1)
        xorll.append(2)
        self.assertEqual(list(xorll),  [0, 1, 2])

    def test_Append_StoresMultipleCopies(self):

        xorll = XorLinkedList()
        xorll.append(0)
        xorll.append(1)
        xorll.append(0)
        xorll.append(0)
        self.assertEqual(list(xorll), [0, 1, 0, 0])

    def test_Append_ReturnsDifferentReferences(self):

        xorll = XorLinkedList()
        r1 = xorll.append(0)
        r2 = xorll.append(0)
        self.assertNotEqual(r1, r2)
        self.assertNotEqual(r1, XorLinkedList.NOT_FOUND)
        self.assertNotEqual(r2, XorLinkedList.NOT_FOUND)

    def test_Append_CanOverflow(self):

        xorll = XorLinkedList()
        XorLinkedList.MAX_CAPACITY.times(lambda _: xorll.append(0))
        self.assertEqual(len(xorll), XorLinkedList.MAX_CAPACITY)
        with self.assertRaises(RuntimeError):
            xorll.append(0)

    def test_Prepend_StoresValue(self):

        xorll = XorLinkedList()
        self.assertEqual(list(xorll), [])
        xorll.prepend(42)
        self.assertEqual(list(xorll), [42])

    def test_Prepend_ReversesOrder(self):

        xorll = XorLinkedList()
        xorll.prepend(2)
        xorll.prepend(1)
        xorll.prepend(0)
        self.assertEqual(list(xorll), [0, 1, 2])

    def test_Prepend_StoresMultipleCopies(self):

        xorll = XorLinkedList()
        xorll.prepend(0)
        xorll.prepend(1)
        xorll.prepend(0)
        xorll.prepend(0)
        self.assertEqual(list(xorll), [0, 0, 1, 0])

    def test_AppendAndPrepend_EmptyList_GetsSameResults(self):

        xorll1, xorll2 = XorLinkedList(), XorLinkedList()
        xorll1.prepend(42)
        xorll2.append(42)
        self.assertEqual(list(xorll1), list(xorll2))

    def test_AppendAndPrepend_WorkProperly(self):

        xorll = XorLinkedList()
        xorll.prepend(1)
        xorll.append(2)
        xorll.prepend(0)
        xorll.append(3)
        self.assertEqual(list(xorll), [0, 1, 2, 3])

    def test_Prepend_ReturnsDifferentReferences(self):

        xorll = XorLinkedList()
        r1 = xorll.prepend(0)
        r2 = xorll.prepend(0)
        self.assertNotEqual(r1, r2)
        self.assertNotEqual(r1, XorLinkedList.NOT_FOUND)
        self.assertNotEqual(r2, XorLinkedList.NOT_FOUND)

    def test_AppendAndPrepend_ReturnsDifferentReferences(self):

        xorll = XorLinkedList()
        r1 = xorll.append(0)
        r2 = xorll.prepend(0)
        self.assertNotEqual(r1, r2)
        self.assertNotEqual(r1, XorLinkedList.NOT_FOUND)
        self.assertNotEqual(r2, XorLinkedList.NOT_FOUND)

    def test_Prepend_CanOverflow(self):

        xorll = XorLinkedList()
        XorLinkedList.MAX_CAPACITY.times(lambda _: xorll.prepend(0))
        self.assertEqual(len(xorll), XorLinkedList.MAX_CAPACITY)
        with self.assertRaises(RuntimeError):
            xorll.prepend(0)

    def test_CheckAddress_AcceptsNotFound(self):

        XorLinkedList().check_address(XorLinkedList.NOT_FOUND)
     

    def test_CheckAddress_EmptyList_ThrowsFor0(self):

        with self.assertRaises(IndexError):
            XorLinkedList().check_address(0)
    
    def test_CheckAddress_OneElementList_DoesNotThrowFor0(self):

        xorll = XorLinkedList()
        xorll.append(0)
        xorll.check_address(0)

    def test_CheckAddress_OneElementList_ThrowsFor2(self):

        xorll = XorLinkedList()
        xorll.append(0)
        with self.assertRaises(IndexError):
            xorll.check_address(XorLinkedList.ELEMENT_SIZE)

    def test_CheckAddress_OneElementList_ThrowsForInvalidAddress(self):

        xorll = XorLinkedList()
        xorll.append(0)
        with self.assertRaises(IndexError):
            xorll.check_address(1)
        with self.assertRaises(IndexError):
            xorll.check_address(42)

    def test_Append_ReturnsProperAddresses(self):

        xorll = XorLinkedList()
        ref0 = xorll.append(37)
        ref1 = xorll.append(42)
        self.assertEqual(ref0, 0)
        self.assertEqual(ref1, XorLinkedList.ELEMENT_SIZE)

    def test_Prepend_ReturnsProperAddresses(self):

        xorll = XorLinkedList()
        ref0 = xorll.prepend(37)
        ref1 = xorll.prepend(42)
        self.assertEqual(ref0, 0)
        self.assertEqual(ref1, XorLinkedList.ELEMENT_SIZE)

    def test_Get_ReturnsValues(self):

        xorll = XorLinkedList()
        self.assertEqual(xorll[xorll.prepend(37)], 37)
        self.assertEqual(xorll[xorll.append(42)], 42)

    def test_InsertBetween_EmptyList_Works(self):

        xorll = XorLinkedList()
        xorll.insert_between(0, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND)
        self.assertEqual(list(xorll), [0])

    def test_InsertBetween_NonEmptyList_Prepends(self):

        xorll = XorLinkedList()
        r = xorll.insert_between(0, XorLinkedList.NOT_FOUND, xorll.prepend(1))
        self.assertEqual(list(xorll), [0, 1])
        self.assertEqual(r, XorLinkedList.ELEMENT_SIZE)

    def test_InsertBetween_NonEmptyList_Appends(self):

        xorll = XorLinkedList()
        r = xorll.insert_between(1, xorll.append(0), XorLinkedList.NOT_FOUND)
        self.assertEqual(list(xorll), [0, 1])
        self.assertEqual(r, XorLinkedList.ELEMENT_SIZE)

    def test_InsertBetween_DirectOrder_InsertsInProperPlace(self):

        xorll = XorLinkedList()
        a = xorll.append(0)
        b = xorll.append(2)
        r = xorll.insert_between(1, a, b)
        self.assertEqual(list(xorll), [0, 1, 2])

    def test_InsertBetween_ReverseOrder_InsertsInProperPlace(self):

        xorll = XorLinkedList()
        a = xorll.append(2)
        b = xorll.prepend(0)
        r = xorll.insert_between(1, b, a)
        self.assertEqual(list(xorll), [0, 1, 2])

    def test_InsertBetween_CanBeChained(self):

        xorll = XorLinkedList()
        xorll.insert_between(0, XorLinkedList.NOT_FOUND, xorll.insert_between(2, xorll.insert_between(1, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND), XorLinkedList.NOT_FOUND))
        self.assertEqual(list(xorll), [0, 1, 2])

    def test_InsertBetween_WorksInComplexScenarios(self):

        xorll = XorLinkedList()
        r2 = xorll.insert_between(2, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND)
        self.assertEqual(list(xorll), [2])
        r0 = xorll.insert_between(0, XorLinkedList.NOT_FOUND, r2)
        self.assertEqual(list(xorll), [0, 2])
        r4 = xorll.insert_between(4, r2, XorLinkedList.NOT_FOUND)
        self.assertEqual(list(xorll), [0, 2, 4])
        r1 = xorll.insert_between(1, r0, r2)
        self.assertEqual(list(xorll), [0, 1, 2, 4])
        r3 = xorll.insert_between(3, r2, r4)
        self.assertEqual(list(xorll), [0, 1, 2, 3, 4])

    def test_InsertBetween_TakesOrderIntoAccount(self):

        xorll1, xorll2 = XorLinkedList(), XorLinkedList()
        xorll1.insert_between(1, xorll1.append(0), xorll1.append(2))
        xorll2.insert_between(1, xorll2.append(2), xorll2.append(0))
        self.assertEqual(list(xorll1), [0, 1, 2])
        self.assertNotEqual(list(xorll2), [0, 1, 2])

    def test_InsertBetweenAndAppendAndPrepend_WorkTogether(self):

        xorll = XorLinkedList()
        r2 = xorll.insert_between(2, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND)
        r0 = xorll.prepend(0)
        r4 = xorll.append(4)
        r1 = xorll.insert_between(1, r0, r2)
        r3 = xorll.insert_between(3, r2, r4)
        self.assertEqual(list(xorll), [0, 1, 2, 3, 4])

    def test_InsertBetween_WorksInComplexScenario(self):

        xorll = XorLinkedList()
        (10).times(lambda i: xorll.prepend(1000 - i))
        a = xorll.last
        b = xorll.append(90000)
        (10).times(lambda i: xorll.append(100000 + i))
        def add_pair(i):
            nonlocal a, b
            a = xorll.insert_between(i + 10000, a, b)
            b = xorll.insert_between(50000 - i, a, b)
        (20).times(add_pair)
        self.assertEqual(len(xorll), 10 + 10 + 1 + 20 * 2)
        result = list(xorll)
        (len(result) - 1).times(lambda i: self.assertTrue(result[i] < result[i + 1]))

    def test_AddressOf_EmptyList_ReturnsNotFound(self):

        xorll = XorLinkedList()
        self.assertEqual(xorll.address(0), XorLinkedList.NOT_FOUND)

    def test_AddressOf_FindsFirstElement(self):

        xorll = XorLinkedList()
        xorll.append(0); xorll.append(1); xorll.append(2); xorll.append(3)
        self.assertEqual(xorll.address(0), 0)

    def test_AddressOf_FindsLastElement(self):

        xorll = XorLinkedList()
        xorll.append(0); xorll.append(1);
        self.assertEqual(xorll.address(1), XorLinkedList.ELEMENT_SIZE);

    def test_AddressOf_FindsAllElements(self):

        xorll = XorLinkedList()
        (10).times(lambda i: xorll.append(i))
        (10).times(lambda i: self.assertEqual(xorll.address(i), i * XorLinkedList.ELEMENT_SIZE))

    def test_AddressOf_DoesNotFindAbsentElement(self):

        xorll = XorLinkedList()
        (10).times(lambda i: xorll.append(i) if i != 5 else None)
        self.assertEqual(xorll.address(5), XorLinkedList.NOT_FOUND)

    def test_Reverse_EmptyList_Works(self):

        self.assertEqual(list(XorLinkedList().reverse()), [])
    
    def test_Reverse_CancelsItself(self):

        xorll = XorLinkedList()
        xorll.append(1)
        xorll.prepend(0)
        xorll.append(2)
        self.assertEqual(list(xorll.reverse().reverse()), list(xorll))

    def test_Reverse_ShortList_Works(self):

        xorll1 = XorLinkedList()
        xorll1.append(0)
        xorll1.reverse()
        self.assertEqual(list(xorll1), [0])
        xorll2 = XorLinkedList()
        xorll2.prepend(1)
        xorll2.prepend(0)
        xorll2.reverse()
        self.assertEqual(list(xorll2), [1, 0])

    def test_AppendAndPrepend_CanBeExchangedFollowedByReverse(self):

        xorll1, xorll2 = XorLinkedList(), XorLinkedList()
        (10).times(lambda i:            
            (xorll1.append(i), xorll2.prepend(i)) if i % 2 == 0 else (xorll2.append(i), xorll1.prepend(i))
        )
        self.assertEqual(list(xorll1), list(xorll2.reverse()))

    def test_Reverse_WorksInComplexScenarios(self):

        xorll = XorLinkedList()   
        r2 = xorll.insert_between(2, XorLinkedList.NOT_FOUND, XorLinkedList.NOT_FOUND)
        r0 = xorll.prepend(0)
        r4 = xorll.append(4)
        r1 = xorll.insert_between(1, r0, r2)
        r3 = xorll.insert_between(3, r2, r4)
        self.assertEqual(list(xorll.reverse()), [4, 3, 2, 1, 0])

    @timeout_decorator.timeout(0.01)
    def test_Reverse_IsFast(self):

        xorll = XorLinkedList() 
        (1000).times(lambda i: xorll.append(i))      
        (5000).times(lambda _: xorll.reverse().reverse())

    @timeout_decorator.timeout(0.01)
    def test_Prepend_IsFast(self):

        xorll = XorLinkedList() 
        (5000).times(lambda i: xorll.prepend(i))

    @timeout_decorator.timeout(0.01)
    def test_Append_IsFast(self):

        xorll = XorLinkedList() 
        (5000).times(lambda i: xorll.append(i))

    @timeout_decorator.timeout(0.01)
    def test_InsertBetween_IsFast(self):

        xorll = XorLinkedList()
        (1000).times(lambda i: xorll.prepend(1000 - i))
        a = xorll.last
        b = xorll.append(90000)
        (1000).times(lambda i: xorll.append(100000 + i))
        def add_pair(i):
            nonlocal a, b
            a = xorll.insert_between(i + 10000, a, b)
            b = xorll.insert_between(50000 - i, a, b)
        (2500).times(add_pair)
        self.assertEqual(len(xorll), 1000 + 1000 + 1 + 2500 * 2)

    def test_InternalBufferSizeIsLimited(self):

        xorll = XorLinkedList()
        self.assertTrue(XorLinkedList.INITIAL_CAPACITY <= 15)
        self.assertEqual(XorLinkedList.ELEMENT_SIZE, 2)
        def test(i):
            xorll.append(i)
            limit = 2 * XorLinkedList.ELEMENT_SIZE * xorll.buffer.itemsize * (i + 1)
            if (i > XorLinkedList.INITIAL_CAPACITY):
                self.assertTrue(xorll.buffer.nbytes <= limit)
        (10000).times(test)
    
if __name__ == '__main__':
    unittest.main()