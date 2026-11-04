# Proposal: Root installs source once in ProductionSourceGroups.cmake.
add_executable(reconstruction200_large02_w08 driver.cpp)
target_link_libraries(reconstruction200_large02_w08 PRIVATE presonus::cs18_components)
target_compile_options(reconstruction200_large02_w08 PRIVATE -O3 -DNDEBUG -fno-rtti)
target_link_options(reconstruction200_large02_w08 PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
add_test(NAME reconstruction200_large02_w08 COMMAND "${Python3_EXECUTABLE}"
 "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
 --binary "$<TARGET_FILE:reconstruction200_large02_w08>"
 --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
