import os
import sys
import unittest
import time

def run_qa_suite():
    print("=" * 60)
    print("AGRISENSE AUTOMATED VIRTUAL USER E2E QA TEST RUNNER")
    print("=" * 60)
    
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(start_dir=os.path.join(os.path.dirname(__file__), "tests", "e2e"), pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(test_suite)
    duration = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("AGRISENSE VIRTUAL USER QA REPORT")
    print("=" * 60)
    print(f"Overall Status : {'PASS [OK]' if result.wasSuccessful() else 'FAIL [X]'}")
    print(f"Total Tests    : {result.testsRun}")
    print(f"Passes         : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")
    print(f"Duration       : {duration:.2f} seconds")
    print("=" * 60)

    if not result.wasSuccessful():
        print("\nCRITICAL QA FAILURES DETECTED:")
        for failure in result.failures:
            print(f"\n[FAIL] {failure[0]}:\n{failure[1]}")
        for error in result.errors:
            print(f"\n[ERROR] {error[0]}:\n{error[1]}")
        sys.exit(1)
    else:
        print("\nALL VIRTUAL USER E2E ACCEPTANCE TESTS PASSED 100%!")
        sys.exit(0)

if __name__ == "__main__":
    run_qa_suite()
