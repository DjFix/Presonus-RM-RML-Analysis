# Included by the coordinator after adding the production CPP to its one role partition.
# The caller supplies the canonical production target through this variable.
if(NOT DEFINED LARGE01_W06_PRODUCTION_TARGET)
  message(FATAL_ERROR "Set LARGE01_W06_PRODUCTION_TARGET to the canonical client library")
endif()
add_executable(reconstruction200_large01_w06 driver.cpp)
target_link_libraries(reconstruction200_large01_w06 PRIVATE ${LARGE01_W06_PRODUCTION_TARGET})
target_compile_features(reconstruction200_large01_w06 PRIVATE cxx_std_17)
target_compile_options(reconstruction200_large01_w06 PRIVATE -ffp-contract=off -fno-fast-math)
add_test(NAME reconstruction200_large01_w06_native_replay
  COMMAND ${PROJECT_SOURCE_DIR}/.venv/bin/python
    ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:reconstruction200_large01_w06>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
