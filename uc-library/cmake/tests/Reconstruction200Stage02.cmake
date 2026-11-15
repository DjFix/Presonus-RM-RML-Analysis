# Test-only registration. Keep production source properties outside this directory.
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
