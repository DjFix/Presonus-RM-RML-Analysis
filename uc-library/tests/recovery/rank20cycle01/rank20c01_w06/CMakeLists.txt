# Proposed local integration; Root adds production CPP once to common partition.
add_executable(rank20cycle01_w06_tests driver.cpp)
target_link_libraries(rank20cycle01_w06_tests PRIVATE presonus::uc)
add_test(NAME rank20cycle01_w06_differential
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:rank20cycle01_w06_tests>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json
    --sha256 cc4d3b7feb9d72b7f1c6f49393a3380e9c31e355a283e94fe81d7f38a474871b)
