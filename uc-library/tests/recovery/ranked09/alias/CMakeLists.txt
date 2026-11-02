# Root integrates this directory after adding AliasComponent.cpp to exactly one
# production OBJECT partition. presonus_uc carries the actual pinned provider.
add_executable(ranked09_alias_replay driver.cpp)
target_link_libraries(ranked09_alias_replay PRIVATE presonus_uc)
add_test(NAME ranked09_alias_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/replay.py"
    --executable "$<TARGET_FILE:ranked09_alias_replay>"
    --fixtures "${CMAKE_CURRENT_LIST_DIR}/fixtures.json")
