# Root adds production CPP exactly once to the RM OBJECT partition.
add_executable(frontier01_w01_replay_driver driver.cpp)
target_link_libraries(frontier01_w01_replay_driver PRIVATE presonus_rm_components)
target_link_options(frontier01_w01_replay_driver PRIVATE
  -Wl,--wrap=_ZNK8Presonus5Panel15PresetComponent8getCacheEv
  -Wl,--wrap=_ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb
  -Wl,--wrap=_ZN8Presonus5Panel15PresetNameCache7rebuildEv
  -Wl,--wrap=_ZN8Presonus5Panel23FXPresetRecallComponent12updateFxNameEv
  -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev
  -Wl,--wrap=_ZN8Presonus2UC18FileRequestHandlerD2Ev)
add_test(NAME frontier01_w01_native COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/oracle.py)
add_test(NAME frontier01_w01_replay COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
  --executable $<TARGET_FILE:frontier01_w01_replay_driver>
  --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json
  --work-dir ${CMAKE_SOURCE_DIR}/../temp/test-work/frontier-small01/frontier01_w01)
set_tests_properties(frontier01_w01_native frontier01_w01_replay PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/..)
