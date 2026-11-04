# Root integration: production bodies belong exactly once to role OBJECT partitions.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w01.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w02.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w03.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -std=c++20)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w04.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w05.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w06.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w07.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w08.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w09.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/reconstruction200/large02_w10.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/Controller.cpp" APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/GroupsPageRecovery.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off)
if(BUILD_TESTING)
  # Preserve legacy caller-only native boundary fixtures. The new stage02
  # replay separately executes the actual helper/provider implementations.
  target_link_options(graph_trial05_groups_tests PRIVATE
    -Wl,--wrap=_ZN8Presonus7Surface19GroupsPageComponent11refreshListEv
    -Wl,--wrap=_ZN8Presonus7Surface19GroupsPageComponent8doselectEv
    -Wl,--wrap=_ZN8Presonus7Surface19GroupsPageComponent12observeGroupEPN4Core8Portable9ComponentE)
  target_link_options(graph_trial06_groupsedit_tests PRIVATE
    -Wl,--wrap=_ZN8Presonus7Surface19GroupsPageComponent8doselectEv)
  set(LARGE02_W07_LIBRARY_TARGET presonus_cs18_components)
  set(LARGE02_W07_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w01)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w02)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w03)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w04)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w05)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w06)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w07)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w08)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w09)
  add_subdirectory(tests/recovery/reconstruction-200-02/large02_w10)
endif()
