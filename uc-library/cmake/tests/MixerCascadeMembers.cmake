# Canonical production-linked replay tests.
if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(presonus_compact20_mixer_cascade_01_replay tests/recovery/compact20_mixer_cascade_01/Replay.cpp)
  target_compile_features(presonus_compact20_mixer_cascade_01_replay PRIVATE cxx_std_20)
  target_compile_options(presonus_compact20_mixer_cascade_01_replay PRIVATE -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -UNDEBUG -Ulinux -pthread)
  target_link_libraries(presonus_compact20_mixer_cascade_01_replay PRIVATE presonus::uc stdc++ m)
  add_test(NAME compact20_mixer_cascade_01_replay COMMAND "${Python3_EXECUTABLE}" "uc-library/tests/recovery/compact20_mixer_cascade_01/check.py" "--mode" "replay" "--executable" "$<TARGET_FILE:presonus_compact20_mixer_cascade_01_replay>" "--object" "$<TARGET_FILE:presonus_rm_components>" "--fixtures" "uc-library/tests/recovery/compact20_mixer_cascade_01/fixtures.json" "--elf" "/home/rs/projects/opencs/ai-line-analysis/rootfs/RML16AI_Rack_13731/home/root/mixer")
  set_tests_properties(compact20_mixer_cascade_01_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
