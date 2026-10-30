cmake_minimum_required(VERSION 3.30)
project(PresonusCoreProvider VERSION 5.0.0 LANGUAGES C CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "This source provider candidate supports Linux only")
endif()
if(CMAKE_CONFIGURATION_TYPES OR NOT CMAKE_BUILD_TYPE STREQUAL "Release")
  message(FATAL_ERROR "Only single-configuration Release is validated; Debug needs upstream debug_malloc")
endif()
set(PRESONUS_CORE_SOURCE_DIR "" CACHE PATH "Pinned ccl-framework checkout")
find_package(Git REQUIRED)
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${PRESONUS_CORE_SOURCE_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE core_commit OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
if(NOT core_commit STREQUAL "e8cbdea4a4a20e15111f5a690798a259c0374b31")
  message(FATAL_ERROR "Core source must be pinned CCL 5.0.0 e8cbdea4...")
endif()
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${PRESONUS_CORE_SOURCE_DIR}" status --porcelain --untracked-files=all
  OUTPUT_VARIABLE core_changes COMMAND_ERROR_IS_FATAL ANY)
if(core_changes)
  message(FATAL_ERROR "Core checkout must be clean: ${core_changes}")
endif()
foreach(required core/cmake/CMakeLists.txt build/cmake ccl/cmake/repomacros.cmake license.md)
  if(NOT EXISTS "${PRESONUS_CORE_SOURCE_DIR}/${required}")
    message(FATAL_ERROR "Missing actual upstream ${required}; complete the Linux checkout explicitly")
  endif()
endforeach()
# Prefer CMake's system dependency finders over the vendor's bundled-source finders.
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_ROOT}/Modules" "${CMAKE_CURRENT_LIST_DIR}/../cmake"
  "${PRESONUS_CORE_SOURCE_DIR}/build/cmake/modules/shared")
find_package(PNG REQUIRED)
find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)
find_package(CoreDNSSD REQUIRED)
set(CMAKE_PREFIX_PATH "${PRESONUS_CORE_SOURCE_DIR}/core/cmake;${CMAKE_PREFIX_PATH}")
set(VENDOR_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/artifacts" CACHE PATH "" FORCE)
set(VENDOR_USE_CACHE_DIRECTORY OFF CACHE BOOL "" FORCE)
set(VENDOR_ENABLE_PARALLEL_BUILDS ON CACHE BOOL "" FORCE)
set(PROJECT_DEBUG_SUFFIX "" CACHE STRING "" FORCE)
set(corelib_BUILD_TESTAPP OFF CACHE BOOL "" FORCE)
set(CCL_SYSTEM_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory("${PRESONUS_CORE_SOURCE_DIR}/core/cmake" upstream)
# Keep source implementations untouched. Replace only the packaging interface:
# upstream's build-only paths and TARGET_FILE link option are not relocatable.
set_target_properties(corelib PROPERTIES EXPORT_NAME Archive
  INTERFACE_INCLUDE_DIRECTORIES "$<BUILD_INTERFACE:${PRESONUS_CORE_SOURCE_DIR}>;$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/presonus-core-5>"
  INTERFACE_LINK_LIBRARIES "PNG::PNG;ZLIB::ZLIB;OpenSSL::SSL;OpenSSL::Crypto;Threads::Threads;CoreDNSSD::CoreDNSSD;m;${CMAKE_DL_LIBS}"
  INTERFACE_LINK_OPTIONS ""
  INTERFACE_COMPILE_DEFINITIONS "CORE_USE_OPENSSL=1;NDEBUG=1"
  INTERFACE_COMPILE_OPTIONS "-pthread;$<$<COMPILE_LANGUAGE:CXX>:-Ulinux>"
  INTERFACE_COMPILE_FEATURES cxx_std_17)
target_link_libraries(corelib PRIVATE PNG::PNG ZLIB::ZLIB CoreDNSSD::CoreDNSSD)
add_library(presonus_core_allocator STATIC "${PRESONUS_CORE_SOURCE_DIR}/core/malloc/coremalloc.cpp")
set_target_properties(presonus_core_allocator PROPERTIES EXPORT_NAME Allocator POSITION_INDEPENDENT_CODE ON)
target_include_directories(presonus_core_allocator PRIVATE "${PRESONUS_CORE_SOURCE_DIR}")
# This upstream switch omits process-wide new/delete replacement, without editing source.
target_compile_definitions(presonus_core_allocator PRIVATE NDEBUG=1 CORE_DISABLE_NEW_OPERATOR=1)
target_compile_features(presonus_core_allocator PRIVATE cxx_std_17)
add_library(presonus_core_provider INTERFACE)
add_library(PresonusCore::Provider ALIAS presonus_core_provider)
set_target_properties(presonus_core_provider PROPERTIES EXPORT_NAME Provider)
target_link_libraries(presonus_core_provider INTERFACE corelib presonus_core_allocator)
target_compile_definitions(presonus_core_provider INTERFACE PRESONUS_HAS_UPSTREAM_CORE=1)
install(TARGETS corelib EXPORT PresonusCoreTargets ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
  FILE_SET HEADERS DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/presonus-core-5/core")
install(TARGETS presonus_core_allocator presonus_core_provider EXPORT PresonusCoreTargets
  ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(EXPORT PresonusCoreTargets NAMESPACE PresonusCore:: DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/PresonusCore")
install(DIRECTORY "${PRESONUS_CORE_SOURCE_DIR}/core/" DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/presonus-core-5/core"
  FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(FILES "${PRESONUS_CORE_SOURCE_DIR}/license.md" "${PRESONUS_CORE_SOURCE_DIR}/core/malloc/coremalloc.cpp"
  "${PRESONUS_CORE_SOURCE_DIR}/core/malloc/corenewoperator.cpp"
  DESTINATION "${CMAKE_INSTALL_DATADIR}/presonus-core-5/upstream")
install(FILES "${CMAKE_CURRENT_LIST_DIR}/../provenance.json" DESTINATION "${CMAKE_INSTALL_DATADIR}/presonus-core-5")
configure_package_config_file("${CMAKE_CURRENT_LIST_DIR}/../cmake/PresonusCoreConfig.cmake.in"
  "${CMAKE_CURRENT_BINARY_DIR}/PresonusCoreConfig.cmake" INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/PresonusCore")
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/PresonusCoreConfigVersion.cmake"
  VERSION 5.0.0 COMPATIBILITY ExactVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/PresonusCoreConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/PresonusCoreConfigVersion.cmake" "${CMAKE_CURRENT_LIST_DIR}/../cmake/FindCoreDNSSD.cmake"
  DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/PresonusCore")
