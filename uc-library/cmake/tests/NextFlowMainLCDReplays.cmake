# Native constructor and prior MainLCD behavior replays.
file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/remaining14")
foreach(variant IN ITEMS c1 c2)
  set(task "rolling10_next100_mainlcd_${variant}")
  add_executable(${task}_replay "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/${task}/Replay.cpp")
  target_link_libraries(${task}_replay PRIVATE stdc++ presonus::cs18_components)
  target_compile_options(${task}_replay PRIVATE -fno-rtti -UNDEBUG)
  add_test(NAME ${task}_replay COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/${task}/check.py"
    --exe "$<TARGET_FILE:${task}_replay>"
    --object "${CMAKE_BINARY_DIR}/CMakeFiles/presonus_cs18_objects.dir/src/Presonus/MainLCDComponent.cpp.o"
    --compat-text-exe "$<TARGET_FILE:graph_trial08_mainlcd_tests>"
    --compat-stack-exe "$<TARGET_FILE:ranked09_lcd_tests>"
    --integration local
    --current-source-transition "${PRESONUS_REPOSITORY_ROOT}/evidence/recovery/2026-11-21/reconstruction10x10/next884-historical-guard-repairs/MAINLCD_CURRENT_SOURCE_TRANSITION.json"
    --current-source-transition-sha256 "c333fc6580522ec9d410429aad7d51054179b8fc64ff8c40fa9d9f140feaa50c"
    --out "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/remaining14/${task}.json")
  set_tests_properties(${task}_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}" TIMEOUT 120)
endforeach()
