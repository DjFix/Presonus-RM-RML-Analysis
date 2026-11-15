# Replays link canonical role archives; production sources compile only once.
include(cmake/tests/ComponentReadonlyReplays.cmake)

include(cmake/tests/ComponentReadonlyReplays02.cmake)

# Preserve the independently checked binary32 expression staging in EQ curves.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/EQControl.cpp"
  APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off)
include(cmake/tests/ComponentReadonlyReplays03.cmake)

include(cmake/tests/ComponentReadonlyReplays04.cmake)
