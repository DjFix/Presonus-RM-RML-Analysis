# Root integration proposal; source CPP belongs once to the CS18 OBJECT partition.
add_executable(large02_w10_driver driver.cpp)
target_link_libraries(large02_w10_driver PRIVATE presonus_cs18_components)
# CCL is built without C++ RTTI; this test subclasses its real NumericParam.
target_compile_options(large02_w10_driver PRIVATE -O3 -DNDEBUG -fno-rtti)
target_link_options(large02_w10_driver PRIVATE
  -Wl,--wrap=_ZN8Presonus7Surface14PanelRegistrar22invokeFaderCalibrationEb
  -Wl,--wrap=_ZN8Presonus5Panel9OutputPinC1Ei
  -Wl,--wrap=_ZN8Presonus5Panel9OutputPin3setEi
  -Wl,--wrap=_ZN8Presonus5Panel9OutputPinD1Ev
  -Wl,--wrap=_ZN8Presonus7Surface14PanelRegistrar14bumpFaderSpeedEi
  -Wl,--wrap=_ZN8Presonus7Surface14PanelRegistrar25bumpFaderTouchSensitivityEi
  -Wl,--wrap=fopen -Wl,--wrap=fprintf -Wl,--wrap=__fprintf_chk
  -Wl,--wrap=fclose -Wl,--wrap=fwrite -Wl,--wrap=setvbuf -Wl,--wrap=fputc)
add_test(NAME large02_w10_replay COMMAND
  "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/replay.py"
  --driver "$<TARGET_FILE:large02_w10_driver>"
  --fixtures "${CMAKE_CURRENT_SOURCE_DIR}/fixtures.json")
