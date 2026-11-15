# Canonical production-linked replay tests.
if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(marker14_replay tests/recovery/compact20_surface_document_marker_14/Replay.cpp)
  target_compile_features(marker14_replay PRIVATE cxx_std_20)
  target_compile_options(marker14_replay PRIVATE -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -UNDEBUG -Ulinux)
  target_link_libraries(marker14_replay PRIVATE presonus::uc stdc++ m)
  add_test(NAME compact20_surface_document_marker_14_replay COMMAND "${Python3_EXECUTABLE}" "uc-library/tests/recovery/compact20_surface_document_marker_14/check.py" "replay" "$<TARGET_FILE:marker14_replay>" "uc-library/tests/recovery/compact20_surface_document_marker_14/fixtures.json")
  set_tests_properties(compact20_surface_document_marker_14_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
