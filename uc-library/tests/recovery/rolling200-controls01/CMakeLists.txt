add_executable(rolling200_controls01 driver.cpp)
target_link_libraries(rolling200_controls01 PRIVATE presonus_uc)
target_compile_options(rolling200_controls01 PRIVATE -UNDEBUG)
foreach(symbol IN ITEMS
  _ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE
  _ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
  _ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi
  _ZN4Core8Portable8ValueBar13setAttributesERKNS0_10AttributesE
  _ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_10AttributesEPKc)
  target_link_options(rolling200_controls01 PRIVATE "LINKER:--wrap=${symbol}")
endforeach()
add_test(NAME rolling200_controls01_native
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:rolling200_controls01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
add_test(NAME rolling200_controls01_attributes
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay_attributes.py
    --executable $<TARGET_FILE:rolling200_controls01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures_attributes.json)
add_test(NAME rolling200_controls01_provider_lifecycle
  COMMAND rolling200_controls01 --provider-lifecycle)
get_filename_component(controls_repository_root "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
set_tests_properties(rolling200_controls01_native rolling200_controls01_attributes
  rolling200_controls01_provider_lifecycle PROPERTIES WORKING_DIRECTORY "${controls_repository_root}")
