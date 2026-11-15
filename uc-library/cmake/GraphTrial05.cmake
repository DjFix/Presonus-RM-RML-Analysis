# Actual CCL archive lacks RTTI. Keep each new production CPP compile-once.
set_source_files_properties(src/Presonus/MeterManagerBase.cpp src/Presonus/StormMixSceneComponent.cpp src/Presonus/PanControl.cpp src/Presonus/LinkControl.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti")
set_source_files_properties(src/Presonus/Surface/DawFxPageComponent.cpp PROPERTIES COMPILE_OPTIONS "-std=c++20")
include(cmake/tests/GraphTrial05.cmake)
