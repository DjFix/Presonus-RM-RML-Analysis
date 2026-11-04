# Root adds this directory only after integrating the sealed source proposal.
add_executable(reconstruction200_large02_w04 driver.cpp)
target_link_libraries(reconstruction200_large02_w04 PRIVATE presonus_rm_components)
target_compile_options(reconstruction200_large02_w04 PRIVATE -O3 -DNDEBUG -fno-rtti -fno-fast-math -ffp-contract=off)
target_link_options(reconstruction200_large02_w04 PRIVATE
  -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
  -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz
  -Wl,--wrap=_ZN8Presonus2UC17MessageAttributesC1EPKc
  -Wl,--wrap=_ZN8Presonus2UC17MessageAttributes6setURLEPKc
  -Wl,--wrap=_ZN4Core8Portable10Attributes11lookupOrAddEPKc
  -Wl,--wrap=_ZN4Core8Portable14AttributeValue3setEx
  -Wl,--wrap=_ZN4Core8Portable14AttributeValue3setEPKcb
  -Wl,--wrap=_ZN8Presonus2UC19MutableMessageEventC1ERKNS0_17MessageAttributesEii
  -Wl,--wrap=_ZN4Core2IO6BufferD1Ev
  -Wl,--wrap=_ZN8Presonus2UC17MessageAttributesD1Ev
  -Wl,--wrap=_ZNK8Presonus2UC11NetworkItem12getComponentEv
  -Wl,--wrap=_ZNK4Core8Portable9Component17getParameterByTagEi
  -Wl,--wrap=_ZN8Presonus2UC20ClientImplementation9sendEventERNS0_5EventE
)
add_test(NAME reconstruction200_large02_w04_native_replay
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --driver "$<TARGET_FILE:reconstruction200_large02_w04>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")

target_compile_features(reconstruction200_large02_w04 PRIVATE cxx_std_20)
