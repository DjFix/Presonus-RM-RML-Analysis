add_executable(reconstruction200_large02_w06 driver.cpp)
target_link_libraries(reconstruction200_large02_w06 PRIVATE presonus_rm_components)
target_compile_options(reconstruction200_large02_w06 PRIVATE -O3 -DNDEBUG -fno-rtti -fno-fast-math -ffp-contract=off)
add_test(NAME reconstruction200_large02_w06
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
    --binary "$<TARGET_FILE:reconstruction200_large02_w06>"
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json"
    --work "${CMAKE_SOURCE_DIR}/../temp/test-work/reconstruction-200-02/large02_w06")
