add_executable(large02_lifecycle_fix01 driver.cpp)
target_link_libraries(large02_lifecycle_fix01 PRIVATE presonus_cs18_components)
target_compile_options(large02_lifecycle_fix01 PRIVATE -frtti -fno-lto -fno-fast-math -ffp-contract=off)
target_link_options(large02_lifecycle_fix01 PRIVATE
  -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
  -Wl,--wrap=_ZN8Presonus10DelayTimerD1Ev
  -Wl,--wrap=_ZN8Presonus7Surface15EQPageComponent14removeObserverEPNS1_9IObserverE
  -Wl,--wrap=_ZN8Presonus7Surface16GeqPageComponent14removeObserverEPNS1_9IObserverE
  -Wl,--wrap=_ZN8Presonus7Surface14SLMixerHandler16setDigitalParamsEPN4Core8Portable9ParameterES5_)
add_test(NAME large02_lifecycle_fix01
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/replay.py
    --executable $<TARGET_FILE:large02_lifecycle_fix01>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json)
