# Scratch successor. Include inside BUILD_TESTING; no production sources here.

add_executable(sqlite_meter_peak_param_changed tests/recovery/sqlite_meter_peak_param_changed/Replay.cpp)
target_compile_features(sqlite_meter_peak_param_changed PRIVATE cxx_std_17)
target_link_libraries(sqlite_meter_peak_param_changed PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite_meter_peak_param_changed PRIVATE -O2 -Ulinux -fno-rtti -fno-sized-deallocation)
add_test(NAME sqlite_meter_peak_param_changed COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite_meter_peak_param_changed/check.py" "--replay" "--executable" "$<TARGET_FILE:sqlite_meter_peak_param_changed>")
set_tests_properties(sqlite_meter_peak_param_changed PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite_meter_peak_transmit tests/recovery/sqlite_meter_peak_transmit/Replay.cpp)
target_compile_features(sqlite_meter_peak_transmit PRIVATE cxx_std_17)
target_link_libraries(sqlite_meter_peak_transmit PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite_meter_peak_transmit PRIVATE -O2 -Ulinux -fno-rtti -fno-sized-deallocation)
add_test(NAME sqlite_meter_peak_transmit COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite_meter_peak_transmit/check.py" "--replay" "--executable" "$<TARGET_FILE:sqlite_meter_peak_transmit>")
set_tests_properties(sqlite_meter_peak_transmit PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite_meter_peak_broadcast_value tests/recovery/sqlite_meter_peak_broadcast_value/Replay.cpp)
target_compile_features(sqlite_meter_peak_broadcast_value PRIVATE cxx_std_17)
target_link_libraries(sqlite_meter_peak_broadcast_value PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite_meter_peak_broadcast_value PRIVATE -O2 -Ulinux -fno-rtti -fno-sized-deallocation)
add_test(NAME sqlite_meter_peak_broadcast_value COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite_meter_peak_broadcast_value/check.py" "--replay" "--executable" "$<TARGET_FILE:sqlite_meter_peak_broadcast_value>")
set_tests_properties(sqlite_meter_peak_broadcast_value PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite07_daw_channel_group_production_initReplay tests/recovery/sqlite07_daw_channel_group_production_init/Replay.cpp)
target_compile_features(sqlite07_daw_channel_group_production_initReplay PRIVATE cxx_std_17)
target_link_libraries(sqlite07_daw_channel_group_production_initReplay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite07_daw_channel_group_production_initReplay PRIVATE -O2 -Ulinux)
add_test(NAME sqlite07_daw_channel_group_production_initReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite07_daw_channel_group_production_init/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite07_daw_channel_group_production_initReplay>")
set_tests_properties(sqlite07_daw_channel_group_production_initReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite13_daw_channel_get_typeReplay tests/recovery/sqlite13_daw_channel_get_type/Replay.cpp)
target_compile_features(sqlite13_daw_channel_get_typeReplay PRIVATE cxx_std_17)
target_link_libraries(sqlite13_daw_channel_get_typeReplay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite13_daw_channel_get_typeReplay PRIVATE -O2 -Ulinux)
add_test(NAME sqlite13_daw_channel_get_typeReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite13_daw_channel_get_type/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite13_daw_channel_get_typeReplay>")
set_tests_properties(sqlite13_daw_channel_get_typeReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite13_daw_channel_group_idleReplay tests/recovery/sqlite13_daw_channel_group_idle/Replay.cpp)
target_compile_features(sqlite13_daw_channel_group_idleReplay PRIVATE cxx_std_17)
target_link_libraries(sqlite13_daw_channel_group_idleReplay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite13_daw_channel_group_idleReplay PRIVATE -O2 -Ulinux)
target_link_options(sqlite13_daw_channel_group_idleReplay PRIVATE -Wl,--wrap=_ZN4Core8Portable9Component6onIdleEv)
add_test(NAME sqlite13_daw_channel_group_idleReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite13_daw_channel_group_idle/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite13_daw_channel_group_idleReplay>")
set_tests_properties(sqlite13_daw_channel_group_idleReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(recovery_meter_level_whole_sol61 tests/recovery/sqlite14_meter_level_1f7e4d866f/Replay.cpp)
target_compile_features(recovery_meter_level_whole_sol61 PRIVATE cxx_std_17)
target_link_libraries(recovery_meter_level_whole_sol61 PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(recovery_meter_level_whole_sol61 PRIVATE -Ulinux -fno-fast-math -ffp-contract=off)
add_test(NAME recovery_meter_level_whole_sol61 COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/sqlite14_meter_level_1f7e4d866f/check.py" "replay" "--exe" "$<TARGET_FILE:recovery_meter_level_whole_sol61>" "--fixtures" "uc-library/tests/recovery/sqlite14_meter_level_1f7e4d866f/fixtures.json")
set_tests_properties(recovery_meter_level_whole_sol61 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(control_suspender_replay tests/recovery/ControlSuspenderReplay.cpp)
target_compile_features(control_suspender_replay PRIVATE cxx_std_17)
target_link_libraries(control_suspender_replay PRIVATE presonus::rm_components PresonusCore::Provider)
add_test(NAME control_suspender_replay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/control_suspender/replay.py" "replay" "--executable" "$<TARGET_FILE:control_suspender_replay>" "--fixtures" "uc-library/tests/recovery/control_suspender/native_observations.json" "--fixture-sha256" "3d175f93ca0e4335aefae76acb8c0ee6e38d2c57eb4cbe3a852cc6a9bc81082f")
set_tests_properties(control_suspender_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite14_formatter_6d4f86c7ad tests/recovery/sqlite14_formatter_6d4f86c7ad/Replay.cpp)
target_compile_features(sqlite14_formatter_6d4f86c7ad PRIVATE cxx_std_17)
target_link_libraries(sqlite14_formatter_6d4f86c7ad PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite14_formatter_6d4f86c7ad PRIVATE -fno-rtti -fno-sized-deallocation -O2 -Ulinux)
target_compile_definitions(sqlite14_formatter_6d4f86c7ad PRIVATE FORMATTER_OPTIMIZED=1)
target_link_options(sqlite14_formatter_6d4f86c7ad PRIVATE -Wl,--wrap=_ZdlPv)
add_test(NAME sqlite14_formatter_6d4f86c7ad COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite14_formatter_6d4f86c7ad/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite14_formatter_6d4f86c7ad>" "--fixtures" "uc-library/tests/recovery/sqlite14_formatter_6d4f86c7ad/fixtures.json" "--optimized")
set_tests_properties(sqlite14_formatter_6d4f86c7ad PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite14_formatter_6eaa514467 tests/recovery/sqlite14_formatter_6eaa514467/Replay.cpp)
target_compile_features(sqlite14_formatter_6eaa514467 PRIVATE cxx_std_17)
target_link_libraries(sqlite14_formatter_6eaa514467 PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite14_formatter_6eaa514467 PRIVATE -fno-rtti -fno-sized-deallocation -O2 -Ulinux)
target_compile_definitions(sqlite14_formatter_6eaa514467 PRIVATE FORMATTER_OPTIMIZED=1)
target_link_options(sqlite14_formatter_6eaa514467 PRIVATE -Wl,--wrap=_ZdlPv)
add_test(NAME sqlite14_formatter_6eaa514467 COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite14_formatter_6eaa514467/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite14_formatter_6eaa514467>" "--fixtures" "uc-library/tests/recovery/sqlite14_formatter_6eaa514467/fixtures.json" "--optimized")
set_tests_properties(sqlite14_formatter_6eaa514467 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite14_formatter_887e7eddca tests/recovery/sqlite14_formatter_887e7eddca/Replay.cpp)
target_compile_features(sqlite14_formatter_887e7eddca PRIVATE cxx_std_17)
target_link_libraries(sqlite14_formatter_887e7eddca PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite14_formatter_887e7eddca PRIVATE -fno-rtti -fno-sized-deallocation -O2 -Ulinux)
target_compile_definitions(sqlite14_formatter_887e7eddca PRIVATE FORMATTER_OPTIMIZED=1)
target_link_options(sqlite14_formatter_887e7eddca PRIVATE -Wl,--wrap=_ZdlPv)
add_test(NAME sqlite14_formatter_887e7eddca COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite14_formatter_887e7eddca/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite14_formatter_887e7eddca>" "--fixtures" "uc-library/tests/recovery/sqlite14_formatter_887e7eddca/fixtures.json" "--optimized")
set_tests_properties(sqlite14_formatter_887e7eddca PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite14_formatter_b9be1bac94 tests/recovery/sqlite14_formatter_b9be1bac94/Replay.cpp)
target_compile_features(sqlite14_formatter_b9be1bac94 PRIVATE cxx_std_17)
target_link_libraries(sqlite14_formatter_b9be1bac94 PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite14_formatter_b9be1bac94 PRIVATE -fno-rtti -fno-sized-deallocation -O2 -Ulinux)
target_compile_definitions(sqlite14_formatter_b9be1bac94 PRIVATE FORMATTER_OPTIMIZED=1)
target_link_options(sqlite14_formatter_b9be1bac94 PRIVATE -Wl,--wrap=_ZdlPv)
add_test(NAME sqlite14_formatter_b9be1bac94 COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/sqlite14_formatter_b9be1bac94/check.py" "replay" "--exe" "$<TARGET_FILE:sqlite14_formatter_b9be1bac94>" "--fixtures" "uc-library/tests/recovery/sqlite14_formatter_b9be1bac94/fixtures.json" "--optimized")
set_tests_properties(sqlite14_formatter_b9be1bac94 PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite15_formatter_init_276e76d19d tests/recovery/formatter_initializer_whole/Replay.cpp)
target_compile_features(sqlite15_formatter_init_276e76d19d PRIVATE cxx_std_17)
target_link_libraries(sqlite15_formatter_init_276e76d19d PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite15_formatter_init_276e76d19d PRIVATE -O2 -Ulinux -fno-rtti -fno-sized-deallocation)
target_compile_definitions(sqlite15_formatter_init_276e76d19d PRIVATE FORMATTER_INIT_CLASS=1)
target_link_options(sqlite15_formatter_init_276e76d19d PRIVATE -Wl,--wrap=__cxa_guard_acquire -Wl,--wrap=__cxa_guard_release -Wl,--wrap=__cxa_atexit -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZN4Core17FormatterRegistry3addEPNS_9FormatterE)
add_test(NAME sqlite15_formatter_init_276e76d19d COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/formatter_initializer_whole/check.py" "replay" "--task" "sqlite15_formatter_init_276e76d19d" "--exe" "$<TARGET_FILE:sqlite15_formatter_init_276e76d19d>" "--fixtures" "uc-library/tests/recovery/formatter_initializer_whole/fixtures.json")
set_tests_properties(sqlite15_formatter_init_276e76d19d PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(sqlite15_formatter_init_6c3820bbef tests/recovery/formatter_initializer_whole/Replay.cpp)
target_compile_features(sqlite15_formatter_init_6c3820bbef PRIVATE cxx_std_17)
target_link_libraries(sqlite15_formatter_init_6c3820bbef PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(sqlite15_formatter_init_6c3820bbef PRIVATE -O2 -Ulinux -fno-rtti -fno-sized-deallocation)
target_compile_definitions(sqlite15_formatter_init_6c3820bbef PRIVATE FORMATTER_INIT_CLASS=0)
target_link_options(sqlite15_formatter_init_6c3820bbef PRIVATE -Wl,--wrap=__cxa_guard_acquire -Wl,--wrap=__cxa_guard_release -Wl,--wrap=__cxa_atexit -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZN4Core17FormatterRegistry3addEPNS_9FormatterE)
add_test(NAME sqlite15_formatter_init_6c3820bbef COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "-B" "uc-library/tests/recovery/formatter_initializer_whole/check.py" "replay" "--task" "sqlite15_formatter_init_6c3820bbef" "--exe" "$<TARGET_FILE:sqlite15_formatter_init_6c3820bbef>" "--fixtures" "uc-library/tests/recovery/formatter_initializer_whole/fixtures.json")
set_tests_properties(sqlite15_formatter_init_6c3820bbef PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(UCDataElementReplay tests/recovery/uc_data_element/Replay.cpp)
target_compile_features(UCDataElementReplay PRIVATE cxx_std_17)
target_link_libraries(UCDataElementReplay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(UCDataElementReplay PRIVATE -fno-sized-deallocation -O2 -Ulinux)
target_link_options(UCDataElementReplay PRIVATE -Wl,--wrap=free -Wl,--wrap=_ZdlPv)
add_test(NAME UCDataElementReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/uc_data_element/check.py" "replay" "--exe" "$<TARGET_FILE:UCDataElementReplay>")
set_tests_properties(UCDataElementReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(UCTemplateComponentElementReplay tests/recovery/uc_template_component_elements/Replay.cpp)
target_compile_features(UCTemplateComponentElementReplay PRIVATE cxx_std_17)
target_link_libraries(UCTemplateComponentElementReplay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(UCTemplateComponentElementReplay PRIVATE -O0)
target_link_options(UCTemplateComponentElementReplay PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
add_test(NAME UCTemplateComponentElementReplay COMMAND "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python" "uc-library/tests/recovery/uc_template_component_elements/check.py" "replay" "$<TARGET_FILE:UCTemplateComponentElementReplay>")
set_tests_properties(UCTemplateComponentElementReplay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

add_executable(UCDataElementDirectD1Replay tests/recovery/uc_data_element/DirectD1.cpp)
target_compile_features(UCDataElementDirectD1Replay PRIVATE cxx_std_17)
target_link_libraries(UCDataElementDirectD1Replay PRIVATE presonus::uc PresonusCore::Provider)
target_compile_options(UCDataElementDirectD1Replay PRIVATE -fno-sized-deallocation)
target_link_options(UCDataElementDirectD1Replay PRIVATE -Wl,--wrap=free -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZN8Presonus2UC7ElementD2Ev)
add_test(NAME UCDataElementDirectD1Replay COMMAND "$<TARGET_FILE:UCDataElementDirectD1Replay>")
set_tests_properties(UCDataElementDirectD1Replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")

# Execute accepted replay assertions even in the Release integration build.
foreach(replay_target IN ITEMS
  sqlite_meter_peak_param_changed
  sqlite_meter_peak_transmit
  sqlite_meter_peak_broadcast_value
  sqlite07_daw_channel_group_production_initReplay
  sqlite13_daw_channel_get_typeReplay
  sqlite13_daw_channel_group_idleReplay
  recovery_meter_level_whole_sol61
  control_suspender_replay
  sqlite14_formatter_6d4f86c7ad
  sqlite14_formatter_6eaa514467
  sqlite14_formatter_887e7eddca
  sqlite14_formatter_b9be1bac94
  sqlite15_formatter_init_276e76d19d
  sqlite15_formatter_init_6c3820bbef
  UCDataElementReplay
  UCTemplateComponentElementReplay
  UCDataElementDirectD1Replay
)
  target_compile_options(${replay_target} PRIVATE -UNDEBUG)
endforeach()
