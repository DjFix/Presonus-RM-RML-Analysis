# Root supplies the canonical application library target after integrating the
# disjoint proposal sources into ProductionSourceGroups.cmake exactly once.
if(NOT DEFINED LARGE02_W07_LIBRARY_TARGET OR NOT TARGET ${LARGE02_W07_LIBRARY_TARGET})
  message(FATAL_ERROR "Set LARGE02_W07_LIBRARY_TARGET to the integrated CS18 application library")
endif()
add_executable(recovery_large02_w07 driver.cpp)
target_link_libraries(recovery_large02_w07 PRIVATE ${LARGE02_W07_LIBRARY_TARGET})
target_compile_options(recovery_large02_w07 PRIVATE -O3)
target_compile_definitions(recovery_large02_w07 PRIVATE NDEBUG)
if(NOT DEFINED LARGE02_W07_ROOT)
  get_filename_component(LARGE02_W07_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../.." ABSOLUTE)
endif()
add_test(NAME recovery_large02_w07
  COMMAND "${LARGE02_W07_ROOT}/uc-library/.venv/bin/python"
    "${CMAKE_CURRENT_LIST_DIR}/replay.py"
    --executable $<TARGET_FILE:recovery_large02_w07>
    --fixtures "${CMAKE_CURRENT_LIST_DIR}/fixtures.json")
set_tests_properties(recovery_large02_w07 PROPERTIES
  WORKING_DIRECTORY "${LARGE02_W07_ROOT}" TIMEOUT 120)
