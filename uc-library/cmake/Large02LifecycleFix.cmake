# Continuation of the existing 177/200 batch; bodies compile once in CS18.
foreach(source IN ITEMS
    src/Presonus/Surface/SLMixerLifecycle.cpp
    src/Presonus/Color/MixerColorConverter.cpp
    src/Presonus/Color/ColorMappingName.cpp)
  set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/${source}" APPEND PROPERTY
    COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off)
endforeach()
if(BUILD_TESTING)
  add_subdirectory(tests/recovery/large02-lifecycle-fix01)
endif()
