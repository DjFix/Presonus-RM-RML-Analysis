# Root adds this directory after putting the production CPP in exactly one
# ProductionSourceGroups OBJECT partition. Do not compile that CPP here.
add_executable(rank20c01_w01_replay_driver driver.cpp)
target_link_libraries(rank20c01_w01_replay_driver PRIVATE presonus_rm_components)
add_test(NAME rank20c01_w01_native
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/oracle.py)
set_tests_properties(rank20c01_w01_native PROPERTIES
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/..)
add_test(NAME rank20c01_w01_replay
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
  --executable $<TARGET_FILE:rank20c01_w01_replay_driver>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
