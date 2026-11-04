# Root adds the production CPP to exactly one common OBJECT partition.
add_executable(reconstruction_200_02_large02_w05 driver.cpp)
target_link_libraries(reconstruction_200_02_large02_w05 PRIVATE presonus_rm_components)
target_compile_options(reconstruction_200_02_large02_w05 PRIVATE -O3 -DNDEBUG)
target_link_options(reconstruction_200_02_large02_w05 PRIVATE
  -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz
  -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE)
add_test(NAME reconstruction_200_02_large02_w05
 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
 --executable $<TARGET_FILE:reconstruction_200_02_large02_w05>
 --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
