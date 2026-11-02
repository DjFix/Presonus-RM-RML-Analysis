# Root may include after adding MixerBaseLinks.cpp and OutputComponent.cpp exactly once to the RM partition.
add_executable(ranked09_mixer_replay driver.cpp)
target_link_libraries(ranked09_mixer_replay PRIVATE presonus_rm_components)
add_test(NAME ranked09_mixer_native_fixture
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
          "$<TARGET_FILE:ranked09_mixer_replay>" "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
