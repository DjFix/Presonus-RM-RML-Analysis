# Canonical production-linked replay tests.
if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(mixer_lcd_alt_key_param_replay tests/recovery/compact20_lcd_controls_01/Replay.cpp)
  target_compile_features(mixer_lcd_alt_key_param_replay PRIVATE cxx_std_20)
  target_compile_options(mixer_lcd_alt_key_param_replay PRIVATE -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -UNDEBUG -Ulinux -DCORE_PLATFORM_LINUX=1)
  target_link_libraries(mixer_lcd_alt_key_param_replay PRIVATE presonus::uc stdc++ m)
  add_test(NAME compact20_lcd_controls_01_replay COMMAND "${Python3_EXECUTABLE}" "uc-library/tests/recovery/compact20_lcd_controls_01/check.py" "replay" "--out" "temp/test-work/mixer-lcd-alt-key-param" "--executable" "$<TARGET_FILE:mixer_lcd_alt_key_param_replay>" "--fixture" "uc-library/tests/recovery/compact20_lcd_controls_01/fixtures.json")
  set_tests_properties(compact20_lcd_controls_01_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
