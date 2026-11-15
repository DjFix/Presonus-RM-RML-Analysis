# Canonical production-linked replay tests.
if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(compact20_mixer_preset_permissions_02_replay tests/recovery/compact20_mixer_preset_permissions_02/Replay.cpp)
  target_compile_features(compact20_mixer_preset_permissions_02_replay PRIVATE cxx_std_20)
  target_compile_options(compact20_mixer_preset_permissions_02_replay PRIVATE -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -UNDEBUG -Ulinux)
  target_link_libraries(compact20_mixer_preset_permissions_02_replay PRIVATE presonus::uc stdc++ m)
  add_test(NAME compact20_mixer_preset_permissions_02_replay COMMAND "${Python3_EXECUTABLE}" "uc-library/tests/recovery/compact20_mixer_preset_permissions_02/check.py" "replay" "--executable" "$<TARGET_FILE:compact20_mixer_preset_permissions_02_replay>" "--fixtures" "uc-library/tests/recovery/compact20_mixer_preset_permissions_02/fixtures.json")
  set_tests_properties(compact20_mixer_preset_permissions_02_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
