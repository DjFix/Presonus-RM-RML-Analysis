# Candidate module. The coordinating root owns any active integration.
include_guard(GLOBAL)
function(presonus_build_common_objects)
  if(TARGET presonus_uc)
    message(FATAL_ERROR "Common objects must replace initial presonus_uc construction")
  endif()
  foreach(group IN ITEMS common cs18 rm)
    if(NOT PRESONUS_${group}_SOURCES)
      message(FATAL_ERROR "Actual nonempty ${group} production source partition required")
    endif()
    add_library(presonus_${group}_objects OBJECT)
    foreach(source IN LISTS PRESONUS_${group}_SOURCES)
      target_sources(presonus_${group}_objects PRIVATE "${PRESONUS_LIBRARY_SOURCE}/${source}")
    endforeach()
    target_compile_features(presonus_${group}_objects PRIVATE cxx_std_17)
    set_target_properties(presonus_${group}_objects PROPERTIES CXX_EXTENSIONS OFF)
    target_include_directories(presonus_${group}_objects PRIVATE "${PRESONUS_LIBRARY_SOURCE}/include")
    target_compile_options(presonus_${group}_objects PRIVATE -Wall -Wextra -Wpedantic)
    target_link_libraries(presonus_${group}_objects PRIVATE PresonusCore::Provider)
  endforeach()
  set(float_options -fno-fast-math -ffp-contract=off)
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    list(APPEND float_options -ffp-model=strict)
  endif()
  set_source_files_properties(
    "${PRESONUS_LIBRARY_SOURCE}/src/mixer_dsp/Dsp.cpp"
    "${PRESONUS_LIBRARY_SOURCE}/src/mixer_dsp/FilterControllers.cpp"
    PROPERTIES COMPILE_OPTIONS "${float_options}")
  set_source_files_properties(
    "${PRESONUS_LIBRARY_SOURCE}/src/surface_panel/DbTable.cpp"
    "${PRESONUS_LIBRARY_SOURCE}/src/surface_panel/MeterControl.cpp"
    PROPERTIES COMPILE_OPTIONS "${float_options};-fno-builtin-powf")
  set_source_files_properties("${PRESONUS_LIBRARY_SOURCE}/src/Presonus/DICE/Dice3Programmer.cpp"
    PROPERTIES COMPILE_OPTIONS "-fno-fast-math")

  add_library(presonus_uc STATIC $<TARGET_OBJECTS:presonus_common_objects>
    $<TARGET_OBJECTS:presonus_cs18_objects> $<TARGET_OBJECTS:presonus_rm_objects>)
  add_library(presonus_cs18_components STATIC $<TARGET_OBJECTS:presonus_common_objects>
    $<TARGET_OBJECTS:presonus_cs18_objects>)
  add_library(presonus_rm_components STATIC $<TARGET_OBJECTS:presonus_common_objects>
    $<TARGET_OBJECTS:presonus_rm_objects>)
  add_library(presonus::uc ALIAS presonus_uc)
  add_library(presonus::cs18_components ALIAS presonus_cs18_components)
  add_library(presonus::rm_components ALIAS presonus_rm_components)
  set_target_properties(presonus_uc PROPERTIES EXPORT_NAME uc)
  set_target_properties(presonus_cs18_components PROPERTIES EXPORT_NAME cs18_components)
  set_target_properties(presonus_rm_components PROPERTIES EXPORT_NAME rm_components)
  foreach(target IN ITEMS presonus_uc presonus_cs18_components presonus_rm_components)
    target_compile_features(${target} PUBLIC cxx_std_17)
    target_include_directories(${target} PUBLIC
      $<BUILD_INTERFACE:${PRESONUS_LIBRARY_SOURCE}/include> $<INSTALL_INTERFACE:include>)
    target_link_libraries(${target} PUBLIC PresonusCore::Provider)
  endforeach()
endfunction()
