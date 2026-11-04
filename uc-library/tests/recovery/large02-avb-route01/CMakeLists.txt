# Root integrates MixerRouteInputsToNet.cpp into exactly one production partition.
add_executable(large02_avb_route01 driver.cpp)
target_link_libraries(large02_avb_route01 PRIVATE presonus_rm_components)
add_test(NAME large02_avb_route01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
  --executable $<TARGET_FILE:large02_avb_route01>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
