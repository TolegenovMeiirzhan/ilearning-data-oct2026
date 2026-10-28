import random
import unittest
from xor_linked_list import XorLinkedList


class ExtraTests(unittest.TestCase):
    def test_random_operations_against_builtin_list(self):
        rng=random.Random(2026)
        actual, expected=XorLinkedList(), []
        for _ in range(1000):
            choice=rng.randrange(3);value=rng.randrange(2**32)
            if choice==0:actual.append(value);expected.append(value)
            elif choice==1:actual.prepend(value);expected.insert(0,value)
            else:actual.reverse();expected.reverse()
            self.assertEqual(list(actual),expected)

    def test_xor_storage_is_real(self):
        linked=XorLinkedList()
        a,b,c=[linked.append(i) for i in range(3)]
        self.assertEqual(linked.buffer[b+1], a^c)
        self.assertEqual(linked.buffer[a+1],linked.NOT_FOUND^b)
        self.assertEqual(linked.buffer[c+1],b^linked.NOT_FOUND)

    def test_invalid_values_do_not_mutate(self):
        linked=XorLinkedList();linked.append(10)
        for value in (-1,2**32,1.5,'1',True):
            with self.assertRaises(ValueError):linked.append(value)
            self.assertEqual(list(linked),[10])

    def test_duplicate_search_follows_current_order(self):
        linked=XorLinkedList();a=linked.append(5);linked.append(2);b=linked.append(5)
        self.assertEqual(linked.address(5),a)
        self.assertEqual(linked.reverse().address(5),b)

    def test_insert_after_reverse(self):
        linked=XorLinkedList();a=linked.append(1);b=linked.append(3)
        linked.reverse();linked.insert_between(2,b,a)
        self.assertEqual(list(linked),[3,2,1])

    def test_negative_and_sentinel_reads_rejected(self):
        linked=XorLinkedList();linked.append(1)
        for address in (-2,1,2,1.5,True,linked.NOT_FOUND):
            with self.assertRaises(IndexError):linked[address]

if __name__=='__main__':unittest.main()
