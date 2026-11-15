# Canonical production-linked replay tests.
if(BUILD_TESTING AND PRESONUS_ENABLE_UPSTREAM_CORE)
  add_executable(SurfaceRoutingMembersReplay tests/recovery/compact20_surface_network_02/Replay.cpp)
  target_compile_features(SurfaceRoutingMembersReplay PRIVATE cxx_std_20)
  target_compile_options(SurfaceRoutingMembersReplay PRIVATE -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -UNDEBUG -Ulinux -pthread)
  target_link_libraries(SurfaceRoutingMembersReplay PRIVATE presonus::uc stdc++ m)
  add_test(NAME compact20_surface_network_02_replay COMMAND "${Python3_EXECUTABLE}" "uc-library/tests/recovery/compact20_surface_network_02/check.py" "replay" "--executable" "$<TARGET_FILE:SurfaceRoutingMembersReplay>" "--fixtures" "uc-library/tests/recovery/compact20_surface_network_02/fixtures.json" "--elf" "rootfs/CS18_v13840/home/root/surface")
  set_tests_properties(compact20_surface_network_02_replay PROPERTIES WORKING_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}")
endif()
