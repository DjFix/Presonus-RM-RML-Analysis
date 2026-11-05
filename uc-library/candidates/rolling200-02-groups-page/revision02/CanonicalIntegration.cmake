# Root-owned integration proposal. This file only defines a test executable.
# Neither production CPP is added here: both stay in their existing OBJECT
# partitions and reach this test through the existing CS18 role archive.
add_executable(rolling200_02_groups_page_canonical
  "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200-02-groups-page/revision02/canonical_replay.cpp")
target_compile_features(rolling200_02_groups_page_canonical PRIVATE cxx_std_17)
target_compile_options(rolling200_02_groups_page_canonical PRIVATE
  -fno-rtti -fno-instrument-functions -fno-fast-math -ffp-contract=off)
target_link_libraries(rolling200_02_groups_page_canonical PRIVATE presonus_cs18_components)
add_test(NAME rolling200_02_groups_page_canonical
  COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/bin/python"
    "${CMAKE_CURRENT_SOURCE_DIR}/candidates/rolling200-02-groups-page/revision02/canonical_verify.py"
    --executable "$<TARGET_FILE:rolling200_02_groups_page_canonical>"
    --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-11-05/rolling200-02/groups-page/native.json"
    --fixture-sha256 34c6a21c0ea0337829b94a7e14e54a97b3ff7e353f6f2da4f605604fa9ade952
    --inputs "${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-11-05/rolling200-02/groups-page/inputs.txt"
    --inputs-sha256 10e55ee045dd56ea83c708f1ba27cd1905954caeab31b1980f47976c536d9da4)
set_tests_properties(rolling200_02_groups_page_canonical PROPERTIES
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/.." TIMEOUT 120)
