# Genuine original-scoped SLMixer app packet; no new Core production provider.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/SLMixerEncoder.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/SLMixerFootswitch.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/SLMixerDigitalParams.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto -fno-fast-math -ffp-contract=off)
include(cmake/tests/PanelSLMixer.cmake)
