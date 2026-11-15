# Connected constructor foundations and bounded accessor; no ABI claim.
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/frontier-scale01/frontier_scale01_f01)
  add_subdirectory(tests/recovery/frontier-scale01/frontier_scale01_f02)
  add_subdirectory(tests/recovery/frontier-scale01/frontier_scale01_f03)
  add_subdirectory(tests/recovery/frontier-scale01/frontier_scale01_f04)
  foreach(target frontier_scale01_f01 frontier_scale01_f02_tests frontier_scale01_f03_driver frontier_scale01_f04_replay)
    target_compile_options(${target} PRIVATE -UNDEBUG -fno-lto -Ulinux)
  endforeach()
  add_test(NAME frontier_scale01_f01_native COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-scale01/frontier_scale01_f01/oracle.py")
  set_tests_properties(frontier_scale01_f01_native PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/..")
  add_test(NAME frontier_scale01_f02_native COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-scale01/frontier_scale01_f02/oracle.py")
  set_tests_properties(frontier_scale01_f02_native PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/..")
  add_test(NAME frontier_scale01_f03_native COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/recovery/frontier-scale01/frontier_scale01_f03/oracle.py")
  set_tests_properties(frontier_scale01_f03_native PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/..")
endif()
