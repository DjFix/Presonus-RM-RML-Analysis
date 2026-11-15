# Test registration boundary

Add recovery test targets, fixture checks, replay commands and `add_test()`
registrations in this directory, normally in the existing module for the
subsystem. Keep `BUILD_TESTING` guards and the existing include order. The
main registration module is `RecoveryTests.cmake`; the top-level CMake file
includes later subsystem modules at their historical execution points.

These files are included, not added as CMake subdirectories:
`CMAKE_CURRENT_SOURCE_DIR` and `CMAKE_CURRENT_BINARY_DIR` retain their existing
library-directory meaning. Do not replace those paths with
`CMAKE_CURRENT_LIST_DIR`, which identifies this directory.

Keep production sources, source properties, target definitions, public headers,
install rules and production link/compile settings outside this directory.
Test helper targets may carry their own private options and dependencies.
When a new module needs an include, add it to the appropriate existing test
registration module so ordinary test additions do not edit production CMake.

Dependency-index refresh may treat this directory as test registration only
after CMake reconfiguration confirms that production compile commands remain
unchanged. The directory name alone is not evidence that production inputs are
unaffected. Run the normal full Linux integration and role audits for admission.
