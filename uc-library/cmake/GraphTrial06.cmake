# Ten sealed scopes; each production CPP belongs to exactly one role OBJECT partition.
set_source_files_properties(src/Presonus/Surface/WifiSetupComponent.cpp src/Presonus/Surface/CapturePageComponent.cpp src/Presonus/Panel/GeqUIComponent.cpp src/Presonus/Panel/PresetComponent.cpp src/Presonus/Mixer/NetworkSelectComponent.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti")
set_property(SOURCE src/Presonus/Panel/GeqUIComponent.cpp APPEND PROPERTY COMPILE_OPTIONS -UNDEBUG)
set_source_files_properties(src/Presonus/Surface/WifiSetupComponent.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti;-std=c++20")
include(cmake/tests/GraphTrial06.cmake)
