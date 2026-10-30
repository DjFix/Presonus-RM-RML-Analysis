# Candidate integration draft only. No root project is modified by this file.
# The managed provider is regenerated and compiled on every build; mutable
# library working-copy headers are never compiler inputs.
function(presonus_add_private_glibc29 target)
  cmake_parse_arguments(ARG "" "REPOSITORY;ARCHIVE;SIGNATURE;MANIFEST;GUARD;PYTHON;OUTPUT" "" ${ARGN})
  foreach(required REPOSITORY ARCHIVE SIGNATURE MANIFEST GUARD PYTHON OUTPUT)
    if(NOT ARG_${required})
      message(FATAL_ERROR "Private GNU math requires ${required}")
    endif()
  endforeach()
  find_program(_presonus_math_cc NAMES cc REQUIRED)
  find_program(_presonus_math_ar NAMES ar REQUIRED)
  find_program(_presonus_math_nm NAMES nm REQUIRED)
  set(_archive "${ARG_OUTPUT}/libpresonus_private_glibc29.a")
  add_custom_target(${target}_regenerate ALL
    COMMAND "${ARG_PYTHON}" "${ARG_GUARD}" "${ARG_REPOSITORY}"
      --archive "${ARG_ARCHIVE}" --signature "${ARG_SIGNATURE}"
      --manifest "${ARG_MANIFEST}" --output "${ARG_OUTPUT}"
      --cc "${_presonus_math_cc}" --ar "${_presonus_math_ar}"
      --nm "${_presonus_math_nm}"
    BYPRODUCTS "${_archive}" "${ARG_OUTPUT}/provider-validation.json"
    VERBATIM
    COMMENT "Regenerating hash-verified private GNU 2.9 math provider")
  add_library(${target} STATIC IMPORTED GLOBAL)
  set_target_properties(${target} PROPERTIES IMPORTED_LOCATION "${_archive}")
  add_dependencies(${target} ${target}_regenerate)
  target_link_libraries(${target} INTERFACE m)
endfunction()
