





import ast
from pathlib import Path
import time
import unittest

class Portable(ast.NodeTransformer):
    def visit_Import(self,node):
        return None if any(a.name=='timeout_decorator' for a in node.names) else node
    def visit_ImportFrom(self,node):
        return None if node.module=='forbiddenfruit' else node
    def visit_Expr(self,node):
        if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='curse':return None
        return self.generic_visit(node)
    def visit_FunctionDef(self,node):
        node.decorator_list=[]
        return self.generic_visit(node)
    def visit_Call(self,node):
        node=self.generic_visit(node)
        if isinstance(node.func,ast.Attribute) and node.func.attr=='times':
            return ast.copy_location(ast.Call(func=ast.Name(id='times',ctx=ast.Load()),args=[node.func.value,*node.args],keywords=node.keywords),node)
        return node

source=Path(__file__).with_name('teacher_tests.py').read_text(encoding='utf-8-sig')
tree=ast.fix_missing_locations(Portable().visit(ast.parse(source)))
namespace={'__name__':'teacher_portable'}
exec(compile(tree,'teacher_tests.py','exec'),namespace)
case=namespace['TestXorLinkedList']
suite=unittest.defaultTestLoader.loadTestsFromTestCase(case)
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('\nOriginal 10 ms timing targets (Windows wall time, median of 5):')
timing_pass=True
for name in sorted(x for x in dir(case) if x.endswith('_IsFast')):
    durations=[]
    for _ in range(5):
        start=time.perf_counter();getattr(case(name),name)();durations.append(time.perf_counter()-start)
    elapsed=sorted(durations)[2];passed=elapsed<=0.01;timing_pass &= passed
    print(f'{name}: {elapsed*1000:.3f} ms — {"PASS" if passed else "OVER 10 ms"}')
print('POSIX timeout-decorator execution: NOT RUN on Windows.')
raise SystemExit(0 if result.wasSuccessful() and timing_pass else 1)
