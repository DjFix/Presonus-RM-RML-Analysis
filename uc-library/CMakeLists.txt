cmake_minimum_required(VERSION 3.16)
project(presonus_uc_recovered VERSION 0.1.0 LANGUAGES CXX)
set(_core_default OFF)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  set(_core_default ON)
endif()
option(PRESONUS_ENABLE_UPSTREAM_CORE "Build actual pinned CCL source" ${_core_default})
get_filename_component(_repo_default "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
if(NOT EXISTS "${_repo_default}/third_party/ccl-framework")
  get_filename_component(_repo_default "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
endif()
set(PRESONUS_REPOSITORY_ROOT "${_repo_default}" CACHE PATH "Repository root")
set(PRESONUS_CORE_SOURCE_DIR "${PRESONUS_REPOSITORY_ROOT}/third_party/ccl-framework"
    CACHE PATH "Pinned CCL source checkout")
if(PRESONUS_ENABLE_UPSTREAM_CORE AND CMAKE_VERSION VERSION_LESS 3.30)
  message(FATAL_ERROR "Enabled actual CCL provider requires CMake >= 3.30")
endif()
include(cmake/providerRoot/cmake/PresonusCoreProvider.cmake)
# Same source tree; each production CPP belongs to exactly one object partition.
if(NOT PRESONUS_ENABLE_UPSTREAM_CORE)
  message(FATAL_ERROR "The current source-backed shared role libraries require enabled CCL")
endif()
set(PRESONUS_LIBRARY_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}")
include(cmake/ProductionSourceGroups.cmake)
include(cmake/PrivateGlibc29.cmake)
set(PRESONUS_PRIVATE_GLIBC29_OUTPUT "${CMAKE_BINARY_DIR}/private-glibc29-provider")
presonus_add_private_glibc29(presonus_private_glibc29
  REPOSITORY "${PRESONUS_REPOSITORY_ROOT}"
  ARCHIVE "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/glibc-2.9.tar.bz2"
  SIGNATURE "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/glibc-2.9.tar.bz2.sig"
  MANIFEST "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/BUILD-MEMBERS.json"
  GUARD "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_private_glibc29.py"
  PYTHON "${PRESONUS_REPOSITORY_ROOT}/uc-library/.venv/bin/python"
  OUTPUT "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/SinglePole.cpp"
  APPEND PROPERTY COMPILE_DEFINITIONS PRESONUS_DSP_GLIBC29_PRIVATE)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/SinglePole.cpp"
  APPEND PROPERTY COMPILE_OPTIONS
    -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin-expf)
include(cmake/CommonObjects.cmake)
presonus_build_common_objects()
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerTransport.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerLifecycle.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/MillisecondsFormatterSingleton.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/MidiConnection.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterMixerInputRoutes.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/EventQueueLifetime.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/EqSourceProviders.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/GateParameterList.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/GateSourceProviders.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/EqSourceProviders.cpp" APPEND PROPERTY INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/GEQParameterList.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/GEQSourceProviders.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterGeqInputRoutes.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/Format/OnOff.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/CompressorParameterList.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/CompressorSourceProviders.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterBusRoutes.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardUCNetHandlerIO.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardHandlerProperties.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/FaderInterpolator.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardReceive.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardStart.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
# ClientStateTracking retains RTTI for explicit partial IEventHandler interface checks.

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/FilterParameterLists.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
# NetworkActivityManager retains native RTTI for its genuine measured hierarchy.

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/EQControlBiquad.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardDiagnostics.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRate.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE src/Presonus/UC/MessageQueue.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/Eq8LimiterParameterLists.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardCommands.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE src/Presonus/UC/MutableMessageEvent.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardResources.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardStatus.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
# Scope missing provider RTTI to the new app unit only; retain the old unit flag.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/MessageAttributesEvent.cpp"
  APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/EqParameterLists.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/EqSourceProviders.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardSetup.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardState.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/EqSourceProviders.cpp" APPEND PROPERTY INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/BeastSetupProperty.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/GambitSetupProperty.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/RogueSetupProperty.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/StormSetupProperty.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/WolverineSetupProperty.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterOpen.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
# Actual CCL Attributes provider omits RTTI; scope this to the new derived CPP.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/MessageAttributes.cpp"
  APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/ParamDescriptorList.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterLookups.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/BeastRouterSlots.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/GambitRouterSlots.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/RogueRouterSlots.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/StormRouterSlots.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/WolverineRouterSlots.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/GateMeterInterpolators.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/PacketQueueOperations.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/FaderCurveInterpolator.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterCommands.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/DicePacketQueueLifetime.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/noaa/RouterLookupImage.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Dsp/FaderCurveInterpolator.cpp" APPEND PROPERTY INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3ManagerLifecycle.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/UDPDiscoveryLifecycle.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/CclManagerOwnedRuntime.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/ManagerWorkerGuard.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/OwnedUartServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/MulticastSocketServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3SubsystemLifecycle.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3ManagerControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3SubsystemControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/CclSubsystemRuntime.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/AdditionalFormatters.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/utilities/StringUtils.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Formatters.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Power.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/UDPDiscoveryServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/AdapterServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3ManagerFirmware.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/ManagerProgrammerServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Interpolators.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Logarithm.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3ProgrammerUpdate.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-fast-math -ffp-contract=off -frounding-math -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DICE/Dice3ProgrammerErase.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/EQTypeConversions.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_source_files_properties(src/Presonus/DICE/Dice3ManagerServices.cpp src/portable/dice/CclManagerServices.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti;-fno-lto")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/BiquadMethods.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/BiquadIncremental.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/BiquadSine.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)

foreach(_math_role presonus_uc presonus_cs18_components presonus_rm_components)
  target_link_libraries(${_math_role} PUBLIC
    $<BUILD_INTERFACE:presonus_private_glibc29>
    $<INSTALL_INTERFACE:presonus::private_glibc29>)
endforeach()

set(PRESONUS_DSP_FLOAT_OPTIONS -fno-fast-math -ffp-contract=off)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  # Preserve ordered comparisons for signaling NaNs under optimization.
  list(APPEND PRESONUS_DSP_FLOAT_OPTIONS -ffp-model=strict)
endif()
set_source_files_properties(src/mixer_dsp/Dsp.cpp src/mixer_dsp/FilterControllers.cpp PROPERTIES
  COMPILE_OPTIONS "${PRESONUS_DSP_FLOAT_OPTIONS}")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Dsp.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_source_files_properties(src/surface_panel/DbTable.cpp src/surface_panel/MeterControl.cpp PROPERTIES
  COMPILE_OPTIONS "${PRESONUS_DSP_FLOAT_OPTIONS};-fno-builtin-powf")
set_source_files_properties(src/Presonus/DICE/Dice3Programmer.cpp PROPERTIES
  COMPILE_OPTIONS "-fno-fast-math")
set_source_files_properties(src/Presonus/DelayTimer.cpp PROPERTIES
  COMPILE_OPTIONS "${PRESONUS_DSP_FLOAT_OPTIONS}")

set_target_properties(presonus_uc PROPERTIES EXPORT_NAME uc)
target_compile_features(presonus_uc PUBLIC cxx_std_17)
target_include_directories(presonus_uc PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>)
target_compile_options(presonus_uc PRIVATE -Wall -Wextra -Wpedantic)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterInitialization.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterScript.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterLifecycle.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/SysexReceiver.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardRouterCommands.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardSPIService.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/input_pin_lifetime.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/portable/dice/CclResponseServices.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/FeedbackFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/tests/noaa_router_lifecycle_core_scope.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sanitize=vptr)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerSerial.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerReceive.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerInformation.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardProgrammerProtocol.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/ScaledTimeFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/FilterQFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/GeqGainFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/EventFactoryLifetime.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/EventItem.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/NetworkManagerDiscoveryCallbacks.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/NetworkManagerMulticastCallback.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/ReportFunctions.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/SocketConnectionIdentity.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/connection.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/external_connection.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/UC/EventQueueLifetime.cpp" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)
include(CTest)
if(BUILD_TESTING)
  if(PRESONUS_ENABLE_UPSTREAM_CORE)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(panel_control_tests tests/panel_control_tests.cpp
      tests/panel_control_virtual_entry.cpp)
    target_link_libraries(panel_control_tests PRIVATE presonus::uc)
    target_compile_options(panel_control_tests PRIVATE -fno-rtti -fno-lto)
    target_link_options(panel_control_tests PRIVATE -fno-lto
      -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
      -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm
      -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
      -Wl,--wrap=_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE
      -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE)
    add_test(NAME panel_control_tests COMMAND panel_control_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-control-base/original/arm-vectors.bin
      --normal)
    add_executable(uc_file_services_bridge tests/uc_file_services_bridge.cpp)
    target_link_libraries(uc_file_services_bridge PRIVATE presonus::uc)
    target_link_options(uc_file_services_bridge PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
    add_test(NAME uc_file_services COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/uc_file_services/replay_fixture.py
      --repo ${PRESONUS_REPOSITORY_ROOT}
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-services/fixtures.jsonl
      --bridge $<TARGET_FILE:uc_file_services_bridge>
      --out ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/uc-file-services-ctest --unique)
    add_executable(noaa_spi_packet_constructor tests/noaa_spi_packet_constructor.cpp)
    target_link_libraries(noaa_spi_packet_constructor PRIVATE presonus::rm_components)
    add_test(NAME noaa_spi_packet_constructor COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:noaa_spi_packet_constructor>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/constructor-stdin.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/constructor-expected.txt)
    add_executable(noaa_spi_packet_clock_provider tests/noaa_spi_packet_clock_provider.cpp)
    target_link_libraries(noaa_spi_packet_clock_provider PRIVATE presonus::rm_components)
    add_test(NAME noaa_spi_packet_clock_provider COMMAND noaa_spi_packet_clock_provider)
    add_executable(noaa_spi_registration tests/noaa_spi_registration.cpp)
    target_link_libraries(noaa_spi_registration PRIVATE presonus::rm_components)
    add_test(NAME noaa_spi_registration COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:noaa_spi_registration>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/registration-stdin.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/registration-expected.txt)
    add_test(NAME noaa_spi_registration_source_provider COMMAND noaa_spi_registration --provider)
    add_executable(noaa_spi_assembly tests/noaa_spi_assembly.cpp)
    target_link_libraries(noaa_spi_assembly PRIVATE presonus::rm_components)
    target_link_options(noaa_spi_assembly PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz
      -Wl,--wrap=_ZNK8Presonus4NOAA11SysexPacket3logEv)
    add_test(NAME noaa_spi_assembly COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:noaa_spi_assembly>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/assembly-stdin.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-packets/assembly-expected.txt)
    add_executable(noaa_spi_assembly_source_provider tests/noaa_spi_assembly_source_provider.cpp)
    target_link_libraries(noaa_spi_assembly_source_provider PRIVATE presonus::rm_components)
    add_test(NAME noaa_spi_assembly_source_provider COMMAND noaa_spi_assembly_source_provider)
    add_executable(panel_param_edit_handler_tests tests/panel_param_edit_handler_tests.cpp)
    target_link_libraries(panel_param_edit_handler_tests PRIVATE presonus::uc)
    target_compile_options(panel_param_edit_handler_tests PRIVATE -fno-rtti -fno-lto)
    target_link_options(panel_param_edit_handler_tests PRIVATE -fno-lto
      -Wl,--wrap=_Znam -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm
      -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv)
    add_test(NAME panel_param_edit_handler_tests COMMAND panel_param_edit_handler_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-param-edit-handler/original/arm-vectors.bin
      --normal)
    add_executable(application_identity_bridge tests/application_identity_bridge.cpp)
    target_link_libraries(application_identity_bridge PRIVATE presonus::cs18_components)
    target_link_options(application_identity_bridge PRIVATE
      -Wl,--wrap=__isoc99_sscanf -Wl,--wrap=__isoc23_sscanf
      -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_test(NAME application_surface_identity COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/application_identity/replay_fixture.py
      --repository ${PRESONUS_REPOSITORY_ROOT}
      --bridge $<TARGET_FILE:application_identity_bridge>
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-identity/fixtures.json
      --work ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/application-identity-fixtures)
    add_executable(application_firmware_stream_bridge tests/application_firmware_stream_bridge.cpp)
    target_link_libraries(application_firmware_stream_bridge PRIVATE presonus::uc)
    target_link_options(application_firmware_stream_bridge PRIVATE
      -Wl,--wrap=inflateInit2_ -Wl,--wrap=inflate -Wl,--wrap=inflateEnd)
    add_test(NAME application_firmware_streams COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/application_firmware_stream/replay_fixture.py
      --repository ${PRESONUS_REPOSITORY_ROOT}
      --bridge $<TARGET_FILE:application_firmware_stream_bridge>
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-firmware-stream/fixtures.json
      --work ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/firmware-stream-fixtures)
    add_executable(dice_uart_lifetime_tests tests/dice_uart_lifetime_tests.cpp
      tests/dice_uart_lifetime_virtual_entries.cpp)
    target_link_libraries(dice_uart_lifetime_tests PRIVATE presonus::cs18_components)
    target_compile_options(dice_uart_lifetime_tests PRIVATE -fno-lto
      -fno-devirtualize -fno-devirtualize-speculatively)
    target_link_options(dice_uart_lifetime_tests PRIVATE -fno-lto
      -Wl,--wrap=_ZN4Core8Platform9PosixLockC1Ev
      -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLockD1Ev
      -Wl,--wrap=core_free -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
      -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=open -Wl,--wrap=close)
    add_test(NAME dice_uart_lifetime_tests COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:dice_uart_lifetime_tests>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-lifetime/fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-lifetime/arm-output.txt)
    add_executable(dice_uart_lifetime_source_provider tests/dice_uart_lifetime_source_provider.cpp)
    target_link_libraries(dice_uart_lifetime_source_provider PRIVATE presonus::cs18_components)
    target_link_options(dice_uart_lifetime_source_provider PRIVATE -Wl,--wrap=open -Wl,--wrap=close)
    add_test(NAME dice_uart_lifetime_source_provider COMMAND dice_uart_lifetime_source_provider)
    add_executable(panel_uart_message_handler_tests tests/panel_uart_message_handler_tests.cpp
      tests/panel_uart_handler_virtual_entry.cpp)
    target_link_libraries(panel_uart_message_handler_tests PRIVATE presonus::uc)
    target_compile_options(panel_uart_message_handler_tests PRIVATE -fno-lto)
    target_link_options(panel_uart_message_handler_tests PRIVATE -fno-lto)
    add_test(NAME panel_uart_message_handler_tests COMMAND panel_uart_message_handler_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-uart-message-handler/original/arm-vectors.bin)
    add_executable(application_resource_bridge tests/application_resource_bridge.cpp)
    target_link_libraries(application_resource_bridge PRIVATE presonus::uc)
    target_link_options(application_resource_bridge PRIVATE
      -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm)
    add_test(NAME application_resource_registration COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/application_resource/replay_fixture.py
      --repository ${PRESONUS_REPOSITORY_ROOT}
      --bridge $<TARGET_FILE:application_resource_bridge>
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-resource/fixtures.json
      --work ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/resource-fixtures)
    add_executable(panel_delay_timer_tests tests/panel_delay_timer_tests.cpp)
    target_link_libraries(panel_delay_timer_tests PRIVATE presonus::uc)
    target_compile_options(panel_delay_timer_tests PRIVATE -fno-lto -ffp-contract=off)
    target_link_options(panel_delay_timer_tests PRIVATE -fno-lto
      -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv)
    add_test(NAME panel_delay_timer_tests COMMAND panel_delay_timer_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-delay-timer/original/arm-vectors.bin)
    add_executable(dice_uart_transport_tests tests/dice_uart_transport_tests.cpp)
    target_link_libraries(dice_uart_transport_tests PRIVATE presonus::cs18_components)
    target_compile_options(dice_uart_transport_tests PRIVATE
      -fno-devirtualize -fno-devirtualize-speculatively)
    target_link_options(dice_uart_transport_tests PRIVATE
      -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
      -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_test(NAME dice_uart_transport_tests COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:dice_uart_transport_tests>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-transport/fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-transport/arm-output.txt)
    add_executable(dice_uart_transport_bounds tests/dice_uart_transport_bounds.cpp)
    target_link_libraries(dice_uart_transport_bounds PRIVATE presonus::cs18_components)
    target_link_options(dice_uart_transport_bounds PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_test(NAME dice_uart_transport_bounds COMMAND dice_uart_transport_bounds)
    add_executable(application_serial_bridge tests/application_serial_bridge.cpp)
    target_link_libraries(application_serial_bridge PRIVATE presonus::cs18_components)
    target_link_options(application_serial_bridge PRIVATE
      -Wl,--wrap=fopen -Wl,--wrap=fclose -Wl,--wrap=__isoc99_sscanf)
    add_test(NAME application_serial_lifecycle COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/application_serial/replay_fixture.py
      --repository ${PRESONUS_REPOSITORY_ROOT}
      --bridge $<TARGET_FILE:application_serial_bridge>
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-serial/fixtures.json
      --work ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/application-serial-fixtures)
    add_executable(panel_simulate_comm_tests tests/panel_simulate_comm_tests.cpp
      tests/panel_simulate_virtual_entry.cpp)
    target_link_libraries(panel_simulate_comm_tests PRIVATE presonus::uc)
    target_compile_options(panel_simulate_comm_tests PRIVATE -fno-lto)
    target_link_options(panel_simulate_comm_tests PRIVATE -fno-lto
      -Wl,--wrap=_ZN4Core8Platform9PosixLockC1Ev
      -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLockD1Ev)
    add_test(NAME panel_simulate_comm_tests COMMAND panel_simulate_comm_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-simulate-comm/original/arm-vectors.bin)
    add_executable(application_file_cleanup_bridge tests/application_file_cleanup_bridge.cpp)
    target_link_libraries(application_file_cleanup_bridge PRIVATE presonus::uc)
    target_link_options(application_file_cleanup_bridge PRIVATE
      -Wl,--wrap=remove -Wl,--wrap=rmdir -Wl,--wrap=fopen -Wl,--wrap=opendir
      -Wl,--wrap=_Znam -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm)
    add_executable(application_file_cleanup_smoke tests/application_file_cleanup_smoke.cpp)
    target_link_libraries(application_file_cleanup_smoke PRIVATE presonus::uc)
    add_test(NAME application_file_cleanup_lifecycle COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/file_cleanup/replay_fixture.py
      --repository ${PRESONUS_REPOSITORY_ROOT}
      --bridge $<TARGET_FILE:application_file_cleanup_bridge>
      --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-file-cleanup/fixtures.json
      --work ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/file-cleanup-tests)
    add_executable(panel_uart_codec_tests tests/panel_uart_codec_tests.cpp)
    target_link_libraries(panel_uart_codec_tests PRIVATE presonus::uc)
    target_link_options(panel_uart_codec_tests PRIVATE -Wl,--wrap=__assert_fail)
    add_test(NAME panel_uart_codec_tests COMMAND panel_uart_codec_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-protocol-comm/codecs/arm-vectors.bin)
    add_executable(panel_protocol_comm_tests tests/panel_protocol_comm_tests.cpp
      tests/panel_protocol_virtual_entry.cpp)
    target_link_libraries(panel_protocol_comm_tests PRIVATE presonus::uc)
    target_compile_options(panel_protocol_comm_tests PRIVATE -fno-lto)
    target_link_options(panel_protocol_comm_tests PRIVATE -fno-lto
      -Wl,--wrap=_ZN4Core8Platform9PosixLockC1Ev
      -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
      -Wl,--wrap=_ZN4Core8Platform9PosixLockD1Ev)
    add_test(NAME panel_protocol_comm_tests COMMAND panel_protocol_comm_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-protocol-comm/protocol/arm-vectors.bin)
    add_executable(panel_uart_comm_tests tests/panel_uart_comm_tests.cpp)
    target_link_libraries(panel_uart_comm_tests PRIVATE presonus::uc)
    target_compile_options(panel_uart_comm_tests PRIVATE
      -fno-devirtualize -fno-devirtualize-speculatively)
    target_link_options(panel_uart_comm_tests PRIVATE
      -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz
      -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
    foreach(role IN ITEMS client server)
      add_test(NAME panel_uart_comm_${role} COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
        --executable $<TARGET_FILE:panel_uart_comm_tests>
        --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-uart-comm/fixtures.txt
        --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-uart-comm/${role}-arm-output.txt)
    endforeach()
    add_executable(panel_alert_manager_tests tests/panel_alert_manager_tests.cpp
      tests/panel_alert_dispatch_entry.cpp)
    target_link_libraries(panel_alert_manager_tests PRIVATE presonus::uc)
    target_compile_options(panel_alert_manager_tests PRIVATE -fno-lto)
    target_link_options(panel_alert_manager_tests PRIVATE -fno-lto)
    add_test(NAME panel_alert_manager_tests COMMAND panel_alert_manager_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-alert-manager/arm-vectors.bin)
    add_executable(application_reader_tests tests/application_reader_tests.cpp)
    target_link_libraries(application_reader_tests PRIVATE presonus::uc)
    target_link_options(application_reader_tests PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    foreach(role IN ITEMS client server)
      add_test(NAME application_reader_${role} COMMAND application_reader_tests
        ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-reader/${role}-vectors.txt
        ${role} ${PRESONUS_REPOSITORY_ROOT}/temp/application-reader/files)
    endforeach()
    add_executable(application_reader_binding_smoke tests/application_reader_binding_smoke.cpp)
    target_link_libraries(application_reader_binding_smoke PRIVATE presonus::uc)
    add_test(NAME application_reader_binding_smoke COMMAND application_reader_binding_smoke
      ${CMAKE_CURRENT_BINARY_DIR}/application-reader-binding-device.txt)
    add_executable(application_manager_tests tests/application_manager_tests.cpp)
    target_link_libraries(application_manager_tests PRIVATE presonus::uc)
    foreach(role IN ITEMS client server)
      add_test(NAME application_manager_${role} COMMAND application_manager_tests
        ${CMAKE_CURRENT_SOURCE_DIR}/validation/application-managers/${role}-vectors.txt ${role})
    endforeach()
    add_executable(uc_data_codecs_tests tests/uc_data_codecs_tests.cpp)
    target_link_libraries(uc_data_codecs_tests PRIVATE presonus::uc)
    target_link_options(uc_data_codecs_tests PRIVATE
      -Wl,--wrap=core_realloc
      -Wl,--wrap=_ZN4Core2IO6Buffer6resizeEj
      -Wl,--wrap=_ZN4Core2IO6Buffer8copyFromEPKvj)
    add_test(NAME uc_data_codecs_tests COMMAND uc_data_codecs_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-data-codecs/arm-vectors.bin)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(packet_logging_capture tests/dice_packet_logging_tests.cpp)
    target_compile_definitions(packet_logging_capture PRIVATE PRESONUS_CAPTURE_LOGGING=1)
    target_link_libraries(packet_logging_capture PRIVATE presonus::uc)
    target_link_options(packet_logging_capture PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_executable(packet_logging_provider tests/dice_packet_logging_tests.cpp)
    target_link_libraries(packet_logging_provider PRIVATE presonus::uc)
    foreach(role IN ITEMS client server)
      add_test(NAME packet_logging_${role} COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/packet_logging_replay.py
        --executable $<TARGET_FILE:packet_logging_capture>
        --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-packet-log --role ${role})
      add_test(NAME packet_logging_provider_${role} COMMAND packet_logging_provider ${role})
    endforeach()
    add_test(NAME packet_logging_noaa_commands COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/packet_logging_replay.py
      --executable $<TARGET_FILE:packet_logging_capture>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-packet-log --role server --commands)
    add_executable(packet_logging_uart_sink tests/dice_packet_log_source_provider.cpp)
    target_link_libraries(packet_logging_uart_sink PRIVATE presonus::cs18_components)
    add_test(NAME packet_logging_uart_sink COMMAND packet_logging_uart_sink)
    add_executable(dice_uart_registration_tests tests/dice_uart_registration_tests.cpp)
    target_link_libraries(dice_uart_registration_tests PRIVATE presonus::cs18_components)
    add_test(NAME dice_uart_registration_replay COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:dice_uart_registration_tests>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-registration/registration-fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-registration/registration-arm-output.txt)
    target_sources(dice_uart_registration_tests PRIVATE tests/dice_uart_seeded_diagnostics.cpp)
    target_link_options(dice_uart_registration_tests PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_executable(dice_uart_registration_source_provider tests/dice_uart_registration_tests.cpp)
    target_link_libraries(dice_uart_registration_source_provider PRIVATE presonus::cs18_components)
    add_test(NAME dice_uart_registration_smoke COMMAND dice_uart_registration_source_provider --smoke)
    add_executable(dice_uart_assembly_replay tests/dice_uart_assembly_replay.cpp)
    target_link_libraries(dice_uart_assembly_replay PRIVATE presonus::cs18_components)
    target_sources(dice_uart_assembly_replay PRIVATE tests/dice_uart_seeded_diagnostics.cpp)
    target_link_options(dice_uart_assembly_replay PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
    add_test(NAME dice_uart_assembly_replay COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:dice_uart_assembly_replay>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-assembly/fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-uart-assembly/arm-output.txt)
    add_executable(dice_uart_assembly_source_provider tests/dice_uart_assembly_source_provider.cpp)
    target_link_libraries(dice_uart_assembly_source_provider PRIVATE presonus::cs18_components)
    add_test(NAME dice_uart_assembly_source_provider COMMAND dice_uart_assembly_source_provider)
    add_executable(uc_dispatcher_registration_tests tests/uc_dispatcher_registration_tests.cpp)
    target_link_libraries(uc_dispatcher_registration_tests PRIVATE presonus::uc)
    add_test(NAME uc_dispatcher_registration_tests COMMAND uc_dispatcher_registration_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-dispatcher-registration/arm-vectors.bin)
    add_executable(panel_digital_pot_tests tests/panel_digital_pot_tests.cpp)
    target_link_libraries(panel_digital_pot_tests PRIVATE presonus::uc)
    foreach(role IN ITEMS client server)
      add_test(NAME panel_digital_pot_${role} COMMAND panel_digital_pot_tests
        ${CMAKE_CURRENT_SOURCE_DIR}/candidates/panel-digital-pot/validation/${role}-vectors.txt)
    endforeach()
    add_executable(uc_event_dispatcher_tests tests/uc_event_dispatcher_tests.cpp)
    target_link_libraries(uc_event_dispatcher_tests PRIVATE presonus::uc)
    add_test(NAME uc_event_dispatcher_tests COMMAND uc_event_dispatcher_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-event-dispatcher/arm-vectors.bin)
    add_executable(panel_control_group_tests tests/panel_control_group_tests.cpp)
    target_link_libraries(panel_control_group_tests PRIVATE presonus::uc)
    add_test(NAME panel_control_group_tests COMMAND panel_control_group_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/candidates/panel-control-group/validation/arm-vectors.txt)
    find_package(ZLIB REQUIRED)
    # The fixture supplies packetClockRawTicks; the archive gateway stays unselected.
    add_executable(dice_packet_tests tests/dice_packet_tests.cpp)
    target_compile_features(dice_packet_tests PRIVATE cxx_std_17)
    target_link_libraries(dice_packet_tests PRIVATE presonus::cs18_components)
    foreach(mode IN ITEMS constructor commands receivers)
      if(mode STREQUAL "constructor")
        set(packet_fixture constructors)
      else()
        set(packet_fixture ${mode})
      endif()
      add_test(NAME dice_packet_${mode} COMMAND dice_packet_tests ${mode}
        ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-packet-candidate/runs/20261026T220418.737889Z/${packet_fixture}.txt)
    endforeach()
    add_executable(dice_response_tests tests/dice_response_tests.cpp)
    target_link_libraries(dice_response_tests PRIVATE presonus::uc ZLIB::ZLIB)
    foreach(role IN ITEMS client server)
      add_test(NAME dice_response_${role} COMMAND dice_response_tests
        ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-response-candidate/runs/20261027T023858.579945Z/${role}-response-vectors.txt.gz ${role})
    endforeach()
    add_executable(dice_response_ccl_smoke tests/dice_response_ccl_smoke.cpp)
    target_link_libraries(dice_response_ccl_smoke PRIVATE presonus::uc)
    add_test(NAME dice_response_ccl_smoke COMMAND dice_response_ccl_smoke)
    add_executable(dice_packet_clock_tests tests/dice_packet_clock_tests.cpp)
    target_link_libraries(dice_packet_clock_tests PRIVATE presonus::uc)
    add_test(NAME dice_packet_clock_tests COMMAND dice_packet_clock_tests)
    add_executable(avb_lookup_tests validation/avb-lookup-candidate/tests/lookup_tests.cpp)
    target_link_libraries(avb_lookup_tests PRIVATE presonus::uc)
    foreach(role IN ITEMS client server)
      add_test(NAME avb_lookup_${role} COMMAND avb_lookup_tests
        ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-lookup-candidate/runs/20261027T020329.112061Z/${role}-lookup-vectors.txt)
    endforeach()
    add_executable(uc_factory_ccl_tests tests/uc_factory_ccl_tests.cpp)
    target_link_libraries(uc_factory_ccl_tests PRIVATE presonus::uc)
    add_test(NAME uc_factory_ccl_tests COMMAND uc_factory_ccl_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-factory/arm-vectors.bin)
    add_executable(uc_connection_receive_ccl_tests tests/uc_connection_receive_ccl_tests.cpp)
    target_link_libraries(uc_connection_receive_ccl_tests PRIVATE presonus::uc)
    add_test(NAME uc_connection_receive_ccl_tests COMMAND uc_connection_receive_ccl_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/candidates/uc-connection-transport/validation/arm-vectors.bin)
    add_executable(uc_ccl_provider_tests tests/uc_ccl_provider_tests.cpp)
    target_link_libraries(uc_ccl_provider_tests PRIVATE presonus::uc)
    add_test(NAME uc_ccl_provider_tests COMMAND uc_ccl_provider_tests)
  endif()
  find_package(Threads REQUIRED)
  add_executable(uc_tests tests/uc_tests.cpp)
  target_link_libraries(uc_tests PRIVATE presonus::uc Threads::Threads)
  add_test(NAME uc_tests COMMAND uc_tests ${CMAKE_CURRENT_SOURCE_DIR}/tests/vectors/capture-vectors.txt)
  add_executable(dice_tests tests/dice_tests.cpp)
  target_link_libraries(dice_tests PRIVATE presonus::uc)
  add_test(NAME dice_tests COMMAND dice_tests ${CMAKE_CURRENT_SOURCE_DIR}/tests/vectors/dice-arm-vectors.txt)
  add_executable(dice_subsystem_tests tests/dice_subsystem_tests.cpp)
  target_link_libraries(dice_subsystem_tests PRIVATE presonus::uc)
  add_test(NAME dice_subsystem_tests COMMAND dice_subsystem_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-subsystem/arm-vectors.txt)
  add_executable(dice_codec_tests tests/dice_codec_tests.cpp)
  target_link_libraries(dice_codec_tests PRIVATE presonus::uc)
  add_test(NAME dice_codec_client COMMAND dice_codec_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-codec/runs/20261026T203738.123385Z/client/arm-vectors.txt)
  add_test(NAME dice_codec_server COMMAND dice_codec_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-codec/runs/20261026T203738.123385Z/server/arm-vectors.txt)
  add_executable(dice_routing_tests tests/dice_routing_tests.cpp)
  target_link_libraries(dice_routing_tests PRIVATE presonus::uc)
  add_test(NAME dice_routing_tests COMMAND dice_routing_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-routing/runs/20261026T204946.521989Z/arm-vectors.txt)
  add_executable(surface_panel_tests tests/surface_panel_tests.cpp)
  target_link_libraries(surface_panel_tests PRIVATE presonus::uc)
  add_test(NAME surface_panel_tests COMMAND surface_panel_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/surface-panel/arm-vectors.txt)
  add_executable(mixer_dsp_tests tests/mixer_dsp_tests.cpp)
  target_link_libraries(mixer_dsp_tests PRIVATE presonus::uc)
  target_compile_options(mixer_dsp_tests PRIVATE ${PRESONUS_DSP_FLOAT_OPTIONS})
  add_test(NAME mixer_dsp_server COMMAND mixer_dsp_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/mixer-dsp/arm-vectors.txt)
  add_test(NAME mixer_dsp_client COMMAND mixer_dsp_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/mixer-dsp/client/arm-vectors.txt)
  add_executable(mixer_state_tests tests/mixer_state_tests.cpp)
  target_link_libraries(mixer_state_tests PRIVATE presonus::uc)
  add_test(NAME mixer_state_client COMMAND mixer_state_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/mixer-state/runs/20261026T202623.516205Z/client/arm-vectors.txt)
  add_test(NAME mixer_state_server COMMAND mixer_state_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/mixer-state/runs/20261026T202623.516205Z/server/arm-vectors.txt)
  add_executable(core_uc_tests tests/core_uc_tests.cpp)
  target_link_libraries(core_uc_tests PRIVATE presonus::uc)
  add_test(NAME core_uc_tests COMMAND core_uc_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/core-uc/arm-vectors.bin)
  add_executable(uc_event_tests tests/uc_event_tests.cpp)
  target_link_libraries(uc_event_tests PRIVATE presonus::uc)
  add_test(NAME uc_event_tests COMMAND uc_event_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-events/arm-vectors.bin)
  add_executable(uc_transport_tests tests/uc_transport_tests.cpp)
  target_link_libraries(uc_transport_tests PRIVATE presonus::uc)
  add_test(NAME uc_transport_tests COMMAND uc_transport_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transport/arm-vectors.bin)
  add_executable(uc_factory_tests tests/uc_factory_tests.cpp)
  target_link_libraries(uc_factory_tests PRIVATE presonus::uc)
  add_test(NAME uc_factory_tests COMMAND uc_factory_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-factory/arm-vectors.bin)
  add_executable(uc_dispatch_tests tests/uc_dispatch_tests.cpp)
  target_link_libraries(uc_dispatch_tests PRIVATE presonus::uc)
  add_test(NAME uc_dispatch_tests COMMAND uc_dispatch_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-dispatch/arm-vectors.bin)
  add_executable(uc_meter_tests tests/uc_meter_tests.cpp)
  target_link_libraries(uc_meter_tests PRIVATE presonus::uc)
  add_test(NAME uc_meter_tests COMMAND uc_meter_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-meter/arm-vectors.bin)
  add_executable(uc_parameter_tests tests/uc_parameter_tests.cpp)
  target_link_libraries(uc_parameter_tests PRIVATE presonus::uc)
  add_test(NAME uc_parameter_tests COMMAND uc_parameter_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-parameter/arm-vectors.bin)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  add_executable(panel_output_pin_tests tests/panel_output_pin_tests.cpp)
  target_link_libraries(panel_output_pin_tests PRIVATE presonus::uc)
  add_test(NAME panel_output_pin_tests COMMAND panel_output_pin_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-output-pin/arm-vectors.txt)
  add_executable(panel_input_pin_tests tests/panel_input_pin_tests.cpp)
  target_link_libraries(panel_input_pin_tests PRIVATE presonus::uc)
  add_test(NAME panel_input_pin_tests COMMAND panel_input_pin_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-input-pin/arm-vectors.txt)
  add_executable(panel_led_state_tests tests/panel_led_state_tests.cpp)
  target_link_libraries(panel_led_state_tests PRIVATE presonus::uc)
  add_test(NAME panel_led_state_tests COMMAND panel_led_state_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-led-state/arm-vectors.txt)
  add_executable(uc_socket_channel_tests tests/uc_socket_channel_tests.cpp)
  target_link_libraries(uc_socket_channel_tests PRIVATE presonus::uc)
  add_test(NAME uc_socket_channel_tests COMMAND uc_socket_channel_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-socket-channel/arm-vectors.bin)
  add_executable(uc_socket_channel_virtual_tests tests/uc_socket_channel_virtual_tests.cpp)
  target_link_libraries(uc_socket_channel_virtual_tests PRIVATE presonus::uc)
  add_test(NAME uc_socket_channel_virtual_tests COMMAND uc_socket_channel_virtual_tests)
  add_executable(uc_basic_connection_tests tests/uc_basic_connection_tests.cpp)
  target_link_libraries(uc_basic_connection_tests PRIVATE presonus::uc)
  add_test(NAME uc_basic_connection_tests COMMAND uc_basic_connection_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-basic-connection/arm-vectors.bin)
  add_executable(panel_bitmap_drawing_tests tests/panel_bitmap_drawing_tests.cpp)
  target_link_libraries(panel_bitmap_drawing_tests PRIVATE presonus::uc)
  add_test(NAME panel_bitmap_drawing_tests COMMAND panel_bitmap_drawing_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-bitmap-drawing/arm-vectors.txt)
  add_executable(uc_event_queue_tests tests/uc_event_queue_tests.cpp)
  target_link_libraries(uc_event_queue_tests PRIVATE presonus::uc)
  add_test(NAME uc_event_queue_tests COMMAND uc_event_queue_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-event-queue/arm-vectors.bin)
  add_executable(panel_meter_control_tests tests/panel_meter_control_tests.cpp)
  target_compile_options(panel_meter_control_tests PRIVATE ${PRESONUS_DSP_FLOAT_OPTIONS} -fno-builtin-powf)
  target_link_libraries(panel_meter_control_tests PRIVATE presonus::uc)
  add_test(NAME panel_meter_control_tests COMMAND panel_meter_control_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-meter-control/arm-vectors.txt)
  find_package(ZLIB REQUIRED)
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_executable(avb_receive_tests tests/avb_receive_tests.cpp)
    target_link_libraries(avb_receive_tests PRIVATE presonus::uc ZLIB::ZLIB)
    target_link_options(avb_receive_tests PRIVATE
      "-Wl,--wrap=_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi"
      "-Wl,--wrap=_ZN8Presonus3AVB11AvbListener6updateEhhh"
      "-Wl,--wrap=_ZN8Presonus3AVB9AvbTalker6updateEhh")
    add_test(NAME avb_receive_tests COMMAND avb_receive_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-receive-candidate/runs/20261027T003044.766641Z/receive-vectors.txt.gz)
  endif()
  add_executable(avb_streams_tests tests/avb_streams_tests.cpp)
  target_link_libraries(avb_streams_tests PRIVATE presonus::uc ZLIB::ZLIB)
  add_test(NAME avb_streams_tests COMMAND avb_streams_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-streams/runs/20261027T000739.509106Z/client-vectors.bin.gz
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-streams/runs/20261027T000739.509106Z/server-vectors.bin.gz)
  add_executable(avb_protocol_tests tests/avb_protocol_tests.cpp)
  target_link_libraries(avb_protocol_tests PRIVATE presonus::uc ZLIB::ZLIB)
  add_test(NAME avb_protocol_tests COMMAND avb_protocol_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-protocol/runs/20261026T235518.530958Z/accept-vectors.txt
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-protocol/runs/20261026T235518.530958Z/reverse-vectors.txt
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/avb-protocol/runs/20261026T235518.530958Z/memory-vectors.bin.gz)
  add_executable(panel_db_table_tests tests/panel_db_table_tests.cpp)
  target_compile_options(panel_db_table_tests PRIVATE ${PRESONUS_DSP_FLOAT_OPTIONS} -fno-builtin-powf)
  target_link_libraries(panel_db_table_tests PRIVATE presonus::uc)
  add_test(NAME panel_db_table_tests COMMAND panel_db_table_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-db-table/arm-vectors.txt)
  add_executable(uc_external_connection_tests tests/uc_external_connection_tests.cpp)
  target_link_libraries(uc_external_connection_tests PRIVATE presonus::uc)
  add_test(NAME uc_external_connection_tests COMMAND uc_external_connection_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-external-connection/arm-vectors.bin)
  add_executable(dice_programmer_tests tests/dice_programmer_tests.cpp)
  target_compile_options(dice_programmer_tests PRIVATE -fno-fast-math)
  target_link_libraries(dice_programmer_tests PRIVATE presonus::uc)
  add_test(NAME dice_programmer_tests COMMAND dice_programmer_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer/runs/20261026T234533.340055Z/arm-vectors.txt)
  add_executable(filter_control_tests tests/filter_control_tests.cpp)
  target_compile_options(filter_control_tests PRIVATE ${PRESONUS_DSP_FLOAT_OPTIONS})
  target_link_libraries(filter_control_tests PRIVATE presonus::uc)
  add_test(NAME filter_control_tests COMMAND filter_control_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/filter-control/arm-vectors.txt)
  add_executable(uc_connection_tests tests/uc_connection_tests.cpp)
  target_link_libraries(uc_connection_tests PRIVATE presonus::uc)
  add_test(NAME uc_connection_tests COMMAND uc_connection_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-connection/arm-vectors.bin)
  foreach(event_suite IN ITEMS file_control misc file_data)
    add_executable(uc_${event_suite}_tests tests/uc_${event_suite}_tests.cpp)
    target_link_libraries(uc_${event_suite}_tests PRIVATE presonus::uc)
    string(REPLACE "_" "-" fixture_directory "${event_suite}")
    add_test(NAME uc_${event_suite}_tests COMMAND uc_${event_suite}_tests
      ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-${fixture_directory}/arm-vectors.bin)
  endforeach()
  add_executable(embedded_dice_mix_tests validation/dice-image/mix_differential.cpp)
  target_link_libraries(embedded_dice_mix_tests PRIVATE presonus::uc)
  add_test(NAME embedded_dice_mix COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_image_mix_replay.py
    --executable $<TARGET_FILE:embedded_dice_mix_tests>
    --oracle ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-image/mix-runs/20261026T200643.844086Z/arm-oracle.json)
  set(efm_checks_cases 5642)
  set(efm_version_cases 8199)
  set(efm_composition_cases 768)
  foreach(efm_suite checks version composition)
    add_executable(efm_${efm_suite}_driver tests/efm_${efm_suite}_driver.cpp)
    target_link_libraries(efm_${efm_suite}_driver PRIVATE presonus::cs18_components)
    add_test(NAME embedded_efm_${efm_suite} COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/embedded_efm_replay.py
      --executable $<TARGET_FILE:efm_${efm_suite}_driver>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/arm-output.txt
      --cases ${efm_${efm_suite}_cases})
  endforeach()
  set(efm_fields_cases 35306)
  set(efm_packed_cases 20179)
  set(efm_fields_fixture fixtures.stdin.gz)
  set(efm_fields_expected arm-output.txt.gz)
  set(efm_packed_fixture fixtures.bin.gz)
  set(efm_packed_expected arm-output.bin.gz)
  foreach(efm_suite fields packed)
    set(efm_replay_extra)
    if(efm_suite STREQUAL "packed")
      set(efm_replay_extra --binary-records)
    endif()
    add_executable(efm_${efm_suite}_driver tests/efm_${efm_suite}_driver.cpp)
    target_link_libraries(efm_${efm_suite}_driver PRIVATE presonus::cs18_components)
    add_test(NAME embedded_efm_${efm_suite} COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/embedded_efm_replay.py
      --executable $<TARGET_FILE:efm_${efm_suite}_driver>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/${efm_${efm_suite}_fixture}
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/${efm_${efm_suite}_expected}
      --cases ${efm_${efm_suite}_cases} ${efm_replay_extra})
  endforeach()
  add_executable(panel_input_pin_lifetime_tests tests/panel_input_pin_lifetime_tests.cpp tests/panel_input_pin_virtual_calls.cpp)
  target_link_libraries(panel_input_pin_lifetime_tests PRIVATE presonus::uc)
  target_compile_options(panel_input_pin_lifetime_tests PRIVATE -fno-lto)
  target_link_options(panel_input_pin_lifetime_tests PRIVATE -fno-lto -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME panel_input_pin_lifetime_tests COMMAND panel_input_pin_lifetime_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-input-pin-lifetime/original/vectors.txt)
  add_executable(panel_input_pin_stdio_tests tests/panel_input_pin_stdio_tests.cpp)
  target_link_libraries(panel_input_pin_stdio_tests PRIVATE presonus::uc)
  target_compile_options(panel_input_pin_stdio_tests PRIVATE -fno-lto)
  target_link_options(panel_input_pin_stdio_tests PRIVATE -fno-lto -Wl,--wrap=fopen -Wl,--wrap=fprintf -Wl,--wrap=__fprintf_chk -Wl,--wrap=fclose -Wl,--wrap=fwrite -Wl,--wrap=setvbuf -Wl,--wrap=rewind -Wl,--wrap=fflush -Wl,--wrap=fgetc)
  add_test(NAME panel_input_pin_stdio_tests COMMAND panel_input_pin_stdio_tests)
  add_executable(uc_file_transfer_state_bridge tests/uc_file_transfer_state_bridge.cpp)
  target_link_libraries(uc_file_transfer_state_bridge PRIVATE presonus::uc)
  target_link_options(uc_file_transfer_state_bridge PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_file_transfer_state COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_state_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/arm-output.txt --cases 11052)
  add_test(NAME uc_file_transfer_state_provider COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_state_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/provider.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/provider-output.txt --cases 1)
  add_executable(panel_protocol_port_bridge tests/panel_protocol_port_bridge.cpp)
  target_link_libraries(panel_protocol_port_bridge PRIVATE presonus::cs18_components)
  add_test(NAME embedded_panel_protocol COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:panel_protocol_port_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/protocol/fixtures.stdin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/protocol/arm-output.txt.gz --cases 10933)
  add_executable(panel_update_loop_bridge tests/panel_update_loop_bridge.cpp)
  target_link_libraries(panel_update_loop_bridge PRIVATE presonus::cs18_components)
  add_test(NAME embedded_panel_update_loop COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:panel_update_loop_bridge>
    --argument ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/panel_surface_code.bin
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/loop/fixtures.stdin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/loop/arm-output.txt.gz --cases 120)
  # led-server-control-root: shared host classes and bounded raw MCU control.
  add_executable(panel_led_control_bridge tests/panel_led_control_bridge.cpp tests/panel_led_control_virtual_entry.cpp)
  target_link_libraries(panel_led_control_bridge PRIVATE presonus::uc)
  set_target_properties(panel_led_control_bridge PROPERTIES CXX_EXTENSIONS OFF)
  target_compile_options(panel_led_control_bridge PRIVATE -fno-lto)
  target_link_options(panel_led_control_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_Znam
    -Wl,--wrap=_ZdaPv
    -Wl,--wrap=_ZdaPvm
    -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev
    -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
    -Wl,--wrap=_ZN4Core8Portable9Parameter7changedEv
    -Wl,--wrap=_ZNK4Core8Portable12NumericParam8getValueEv
    -Wl,--wrap=_ZN8Presonus5Panel7Control9stopTimerEi
    -Wl,--wrap=_ZN8Presonus5Panel7Control10startTimerEfi
    -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
  )
  add_test(NAME panel_led_control_lifecycle COMMAND panel_led_control_bridge --smoke)
  add_test(NAME panel_led_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_led_control_replay.py
    --binary $<TARGET_FILE:panel_led_control_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-led-control-lifecycle/retained/fixtures.jsonl
    --normalization ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-led-control-lifecycle/retained/getter-normalization.json
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/led-control-ctest)
  add_executable(uc_file_server_service_bridge tests/uc_file_server_service_bridge.cpp)
  target_link_libraries(uc_file_server_service_bridge PRIVATE presonus::uc)
  set_target_properties(uc_file_server_service_bridge PROPERTIES CXX_EXTENSIONS OFF)
  target_link_options(uc_file_server_service_bridge PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_file_server_service_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_file_server_service_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-server-service/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-server-service/arm-output.txt --cases 13312)
  add_test(NAME uc_file_server_service_provider COMMAND uc_file_server_service_bridge --provider-smoke)
  set_source_files_properties(src/embedded_efm/efm_control_dispatch.cpp PROPERTIES
    INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/include/presonus/embedded_efm")
  add_executable(efm_control_driver tests/efm_control_driver.cpp)
  target_include_directories(efm_control_driver PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include/presonus/embedded_efm)
  target_link_libraries(efm_control_driver PRIVATE presonus::cs18_components)
  set_target_properties(efm_control_driver PROPERTIES CXX_EXTENSIONS OFF)
  add_test(NAME embedded_efm_control COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/embedded_efm_control_replay.py
    --executable $<TARGET_FILE:efm_control_driver>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/control/fixtures.bin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/control/arm-output.bin.gz)
  # spi-avb-helpers-root: real RM SPI application closure.
  add_executable(noaa_spi_service_operations tests/noaa_spi_service_operations.cpp)
  target_link_libraries(noaa_spi_service_operations PRIVATE presonus::rm_components)
  target_compile_options(noaa_spi_service_operations PRIVATE -fno-lto)
  target_link_options(noaa_spi_service_operations PRIVATE -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_spi_service_operations COMMAND noaa_spi_service_operations ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-service/operations-vectors.txt)
  add_executable(noaa_spi_service_lifecycle tests/noaa_spi_service_lifecycle.cpp tests/noaa_spi_service_virtual.cpp)
  target_link_libraries(noaa_spi_service_lifecycle PRIVATE presonus::rm_components)
  target_compile_options(noaa_spi_service_lifecycle PRIVATE -fno-lto)
  target_link_options(noaa_spi_service_lifecycle PRIVATE -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME noaa_spi_service_lifecycle COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/run_noaa_spi_lifecycle_test.py $<TARGET_FILE:noaa_spi_service_lifecycle> ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-spi-service/lifecycle-vectors.txt)
  # receiver-transfer-root: three source-preserving application candidates.
  add_executable(noaa_sysex_receiver_tests tests/noaa_sysex_receiver_tests.cpp)
  target_link_libraries(noaa_sysex_receiver_tests PRIVATE presonus::uc)
  target_compile_options(noaa_sysex_receiver_tests PRIVATE -fno-lto)
  target_link_options(noaa_sysex_receiver_tests PRIVATE -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_)
  add_test(NAME noaa_sysex_receiver_tests COMMAND noaa_sysex_receiver_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-sysex-receiver/vectors.txt)
  add_executable(uc_file_transfer_manager_bridge tests/uc_file_transfer_manager_bridge.cpp)
  target_link_libraries(uc_file_transfer_manager_bridge PRIVATE presonus::uc)
  target_link_options(uc_file_transfer_manager_bridge PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_transfer_manager_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_manager_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager/arm-output.txt --cases 6016)
  add_test(NAME uc_transfer_manager_provider COMMAND uc_file_transfer_manager_bridge --provider-smoke)
  add_executable(panel_switch_control_bridge tests/panel_switch_control_bridge.cpp tests/panel_switch_control_virtual_entry.cpp)
  target_link_libraries(panel_switch_control_bridge PRIVATE presonus::uc)
  target_compile_options(panel_switch_control_bridge PRIVATE -fno-lto)
  target_link_options(panel_switch_control_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev
    -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
    -Wl,--wrap=_ZN8presonus13panel_binding20resetSwitchParameterERN4Core8Portable9ParameterE
    -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
  )
  add_test(NAME panel_switch_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_switch_control_replay.py --binary $<TARGET_FILE:panel_switch_control_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-switch-control/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/switch-control-ctest)
  add_test(NAME panel_switch_control_provider COMMAND panel_switch_control_bridge --smoke)
  # dispatch-transfers-root: same original methods, explicit per-image rate profile.
  add_executable(panel_switch_dispatch_bridge tests/panel_switch_dispatch_bridge.cpp)
  target_link_libraries(panel_switch_dispatch_bridge PRIVATE presonus::uc)
  target_compile_options(panel_switch_dispatch_bridge PRIVATE -fno-lto)
  target_link_options(panel_switch_dispatch_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN8presonus13panel_binding23switchParameterDispatchERN4Core8Portable9ParameterEjj
    -Wl,--wrap=_ZN8Presonus5Panel7Control10startTimerEfi
    -Wl,--wrap=_ZN8Presonus5Panel7Control9stopTimerEi
    -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
  )
  add_test(NAME panel_switch_dispatch_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_switch_dispatch_replay.py --binary $<TARGET_FILE:panel_switch_dispatch_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-switch-dispatch/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/switch-dispatch-ctest)
  add_executable(uc_transfer_requests_bridge tests/uc_transfer_requests_bridge.cpp)
  target_link_libraries(uc_transfer_requests_bridge PRIVATE presonus::uc)
  target_link_options(uc_transfer_requests_bridge PRIVATE -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv)
  add_test(NAME uc_transfer_requests_bridge COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_transfer_requests_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager-transfers/uc_transfer_requests_bridge/stdin.txt --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager-transfers/uc_transfer_requests_bridge/expected.txt --cases 2752)
  add_executable(uc_transfer_packets_bridge tests/uc_transfer_packets_bridge.cpp)
  target_link_libraries(uc_transfer_packets_bridge PRIVATE presonus::uc)
  target_link_options(uc_transfer_packets_bridge PRIVATE -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_transfer_packets_bridge COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_transfer_packets_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager-transfers/uc_transfer_packets_bridge/stdin.txt --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager-transfers/uc_transfer_packets_bridge/expected.txt --cases 6598)
  add_executable(panel_pot_fader_bridge tests/panel_pot_fader_bridge.cpp tests/panel_pot_fader_virtual_entry.cpp)
  target_link_libraries(panel_pot_fader_bridge PRIVATE presonus::uc)
  target_compile_options(panel_pot_fader_bridge PRIVATE -fno-lto)
  target_link_options(panel_pot_fader_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN8Presonus5Panel7ControlD2Ev
    -Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE
    -Wl,--wrap=_ZN8presonus13panel_binding24potFaderParameterCommandERN4Core8Portable9ParameterEjj
    -Wl,--wrap=_ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9ParameterE
    -Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv
  )
  add_test(NAME panel_pot_fader_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_pot_fader_replay.py --binary $<TARGET_FILE:panel_pot_fader_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-pot-fader/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/pot-fader-ctest)
  add_test(NAME panel_pot_fader_provider COMMAND panel_pot_fader_bridge --smoke)
  add_executable(dsp_single_pole_tests tests/dsp_single_pole_tests.cpp)
  target_compile_features(dsp_single_pole_tests PRIVATE cxx_std_17)
  target_compile_definitions(dsp_single_pole_tests PRIVATE
    PRESONUS_DSP_GLIBC29_PRIVATE
    PRESONUS_MEASURE_REAL=__real_presonus_glibc29_expf
    PRESONUS_MEASURE_WRAP=__wrap_presonus_glibc29_expf)
  target_compile_options(dsp_single_pole_tests PRIVATE
    -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin-expf)
  target_link_options(dsp_single_pole_tests PRIVATE -Wl,--wrap=presonus_glibc29_expf)
  target_link_libraries(dsp_single_pole_tests PRIVATE presonus::rm_components dl)
  add_test(NAME dsp_single_pole COMMAND dsp_single_pole_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-single-pole/arm-math-vectors.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/dsp-single-pole-differences.txt")
  add_executable(uc_network_services_smoke tests/network_services/network_services_smoke.cpp)
  target_link_libraries(uc_network_services_smoke PRIVATE presonus::uc)
  add_test(NAME uc_network_services_smoke COMMAND uc_network_services_smoke)
  add_executable(uc_network_services_loopback tests/network_services/network_services_loopback.cpp)
  target_link_libraries(uc_network_services_loopback PRIVATE presonus::uc)
  add_test(NAME uc_network_services_loopback COMMAND uc_network_services_loopback)
  add_executable(uc_network_services_bridge tests/network_services/network_services_bridge.cpp)
  target_link_libraries(uc_network_services_bridge PRIVATE presonus::uc)
  target_link_options(uc_network_services_bridge PRIVATE -Wl,--wrap=_ZN8Presonus2UC15EventDispatcher11updateEventERKNS0_5EventE -Wl,--wrap=_ZN8Presonus2UC15EventDispatcher10queueEventEPNS0_9EventItemE -Wl,--wrap=_ZN8Presonus2UC15EventDispatcher11dispatchOneEPNS0_9EventItemE -Wl,--wrap=_ZN8Presonus2UC15EventDispatcher10addHandlerEPNS0_13IEventHandlerEi -Wl,--wrap=_ZN8Presonus2UC15EventDispatcher13removeHandlerEPNS0_13IEventHandlerE -Wl,--wrap=_ZN8Presonus2UC12EventFactory6createERKNS0_5EventE -Wl,--wrap=_ZN8Presonus2UC12EventFactory10createTypeEi -Wl,--wrap=_ZN4Core2IO6Buffer6resizeEj -Wl,--wrap=_ZN4Core2IO6Buffer8copyFromEjPKvj)
  add_test(NAME uc_network_services_bridge COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_network_services_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-services/uc_network_services_bridge/stdin.txt --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-services/uc_network_services_bridge/expected.txt --cases 1732)
  add_executable(uc_network_services_coalescence tests/network_services/network_services_coalescence.cpp)
  target_link_libraries(uc_network_services_coalescence PRIVATE presonus::uc)
  add_test(NAME uc_network_services_coalescence COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_network_services_coalescence> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-services/uc_network_services_coalescence/stdin.txt --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-services/uc_network_services_coalescence/expected.txt --cases 324)
  add_executable(dsp_biquad_constructor_tests tests/dsp_biquad_constructor_tests.cpp)
  target_compile_features(dsp_biquad_constructor_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_constructor_tests PRIVATE presonus::rm_components)
  add_test(NAME dsp_biquad_constructor COMMAND dsp_biquad_constructor_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-constructor/fixtures.txt")
  add_executable(dice_manager_services_bridge tests/dice_manager_services_bridge.cpp)
  target_compile_features(dice_manager_services_bridge PRIVATE cxx_std_17)
  target_compile_options(dice_manager_services_bridge PRIVATE -fno-rtti -fno-lto)
  target_link_libraries(dice_manager_services_bridge PRIVATE presonus::cs18_components)
  target_link_options(dice_manager_services_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3Subsystem7setRateENS0_15Dice3SampleRateE
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3Subsystem14setClockSourceENS0_16Dice3ClockSourceE
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart6onIdleEv
  )
  add_test(NAME dice_manager_services_retained COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_manager_services_replay.py --binary $<TARGET_FILE:dice_manager_services_bridge> --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-services/stdin.txt --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-services/fixtures.jsonl)
  add_test(NAME dice_manager_services_provider COMMAND dice_manager_services_bridge --provider-smoke)
  add_executable(uc_network_next_services_bridge tests/network_next_services/next_services_bridge.cpp tests/network_next_services/next_services_virtual_entry.cpp)
  target_link_libraries(uc_network_next_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_next_services_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_next_services_bridge PRIVATE -fno-lto
    -Wl,--wrap=_Znwm
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
  )
  add_test(NAME uc_network_next_services COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_network_next_services_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-next-services/fixtures.stdin --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-next-services/expected.txt --cases 3572)
  add_executable(dsp_biquad_methods_tests tests/dsp_biquad_methods_tests.cpp)
  target_compile_features(dsp_biquad_methods_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_methods_tests PRIVATE presonus::uc)
  add_test(NAME dsp_biquad_methods COMMAND dsp_biquad_methods_tests "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-methods/fixtures.txt" "${CMAKE_CURRENT_BINARY_DIR}/dsp-biquad-methods-differences.txt")
  add_executable(dice_receiver_lifecycle_bridge tests/dice_receiver_lifecycle_bridge.cpp)
  target_link_libraries(dice_receiver_lifecycle_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_receiver_lifecycle_bridge PRIVATE -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dice_receiver_lifecycle_bridge PRIVATE
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart4postERNS0_11SysexPacketE
    -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_)
  add_test(NAME dice_receiver_lifecycle_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_receiver_lifecycle_replay.py
    --binary $<TARGET_FILE:dice_receiver_lifecycle_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-receiver-lifecycle/fixtures.jsonl
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-receiver-lifecycle/stdin.txt)
  add_executable(uc_network_listener_bridge tests/network_listener_services/listener_bridge.cpp)
  target_link_libraries(uc_network_listener_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_listener_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_listener_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME uc_network_listeners COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_listener_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-listener-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-listener-services/expected.txt --cases 2640)
  add_executable(dsp_biquad_incremental_tests tests/dsp_biquad_incremental_tests.cpp)
  target_compile_features(dsp_biquad_incremental_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_incremental_tests PRIVATE presonus::uc)
  add_test(NAME dsp_biquad_incremental COMMAND dsp_biquad_incremental_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-incremental/fixtures.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/dsp-biquad-incremental-differences.txt")
  add_executable(uc_network_configuration_bridge tests/network_configuration/configuration_bridge.cpp)
  target_link_libraries(uc_network_configuration_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_configuration_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_configuration_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
    -Wl,--wrap=_ZN4Core8Platform11PosixThread11setPriorityEi)
  add_test(NAME uc_network_configuration COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_configuration_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-configuration/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-configuration/expected.txt --cases 3992)
  add_executable(dice_programmer_transactions_bridge tests/dice_programmer_transactions_bridge.cpp)
  target_link_libraries(dice_programmer_transactions_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_transactions_bridge PRIVATE -fno-lto)
  target_link_options(dice_programmer_transactions_bridge PRIVATE -Wl,--wrap=ioctl)
  add_test(NAME dice_programmer_transactions_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_transactions_replay.py
    --binary $<TARGET_FILE:dice_programmer_transactions_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-transactions/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-transactions/fixtures.jsonl)
  add_test(NAME dice_programmer_transactions_provider COMMAND dice_programmer_transactions_bridge --provider-smoke)
  add_executable(uc_network_handler_queries_bridge tests/network_handler_queries/handler_queries_bridge.cpp)
  target_link_libraries(uc_network_handler_queries_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_handler_queries_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_handler_queries_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
    -Wl,--wrap=_ZNK8Presonus2UC15BasicConnection15hasQueuedEventsEv)
  add_test(NAME uc_network_handler_queries COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_handler_queries_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-handler-queries/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-handler-queries/expected.txt --cases 3296)
  add_executable(dice_programmer_pages_bridge tests/dice_programmer_pages_bridge.cpp)
  target_link_libraries(dice_programmer_pages_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_pages_bridge PRIVATE -fno-lto)
  target_link_options(dice_programmer_pages_bridge PRIVATE -Wl,--wrap=ioctl)
  add_test(NAME dice_programmer_pages_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_pages_replay.py
    --binary $<TARGET_FILE:dice_programmer_pages_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-pages/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-pages/fixtures.jsonl)
  add_test(NAME dice_programmer_pages_provider COMMAND dice_programmer_pages_bridge --provider-smoke)
  add_executable(uc_network_registrar_services_bridge tests/network_registrar_services/registrar_services_bridge.cpp)
  target_link_libraries(uc_network_registrar_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_registrar_services_bridge PRIVATE -fno-lto)
  add_test(NAME uc_network_registrar_services COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_registrar_services_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-registrar-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-registrar-services/expected.txt --cases 3058)
  add_executable(dice_programmer_device_bridge tests/dice_programmer_device_bridge.cpp)
  target_link_libraries(dice_programmer_device_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_device_bridge PRIVATE -fno-lto)
  target_link_options(dice_programmer_device_bridge PRIVATE
    -Wl,--wrap=open -Wl,--wrap=__open_2 -Wl,--wrap=close -Wl,--wrap=ioctl)
  add_test(NAME dice_programmer_device_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_device_replay.py
    --binary $<TARGET_FILE:dice_programmer_device_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-device/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-device/fixtures.jsonl)
  add_test(NAME dice_programmer_device_provider COMMAND dice_programmer_device_bridge --provider-smoke)
  add_executable(dsp_eq_type_conversions_tests tests/dsp_eq_type_conversions_tests.cpp)
  target_compile_features(dsp_eq_type_conversions_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_eq_type_conversions_tests PRIVATE presonus_rm_components)
  add_test(NAME dsp_eq_type_conversions COMMAND dsp_eq_type_conversions_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-eq-type-conversions/fixtures.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/dsp-eq-type-conversions-differences.txt")
  add_executable(uc_network_server_metadata_bridge
    tests/network_server_metadata/server_metadata_bridge.cpp
    tests/network_server_metadata/metadata_virtual_entry.cpp)
  target_link_libraries(uc_network_server_metadata_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_server_metadata_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_server_metadata_bridge PRIVATE -fno-lto)
  add_test(NAME uc_network_server_metadata COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_server_metadata_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-server-metadata/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-server-metadata/expected.txt --cases 2884)
  add_executable(dice_programmer_update_bridge tests/dice_programmer_update_bridge.cpp)
  target_link_libraries(dice_programmer_update_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_update_bridge PRIVATE -fno-fast-math -ffp-contract=off -frounding-math -fno-lto)
  target_link_options(dice_programmer_update_bridge PRIVATE
    -fno-lto
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer8busyWaitEi
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer11writeEnableEv
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer18performTransactionENS1_15mp25TransactionE
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer11eraseSectorEi
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer9writePageEiPKhi
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer10verifyPageEiPKhi
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer13printProgressEPKcfb
  )
  add_test(NAME dice_programmer_update_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_update_replay.py
    --binary $<TARGET_FILE:dice_programmer_update_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-update/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-update/fixtures.jsonl)
  add_executable(dsp_interpolators_tests tests/dsp_interpolators_tests.cpp)
  target_link_libraries(dsp_interpolators_tests PRIVATE presonus_uc)
  target_compile_options(dsp_interpolators_tests PRIVATE -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/dsp-interpolators")
  add_test(NAME dsp_interpolators_retained COMMAND dsp_interpolators_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-interpolators/fixtures.txt"
    "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/dsp-interpolators/differences.txt")
  add_executable(dice_manager_firmware_bridge tests/dice_manager_firmware_bridge.cpp)
  target_link_libraries(dice_manager_firmware_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_manager_firmware_bridge PRIVATE -fno-lto)
  target_link_options(dice_manager_firmware_bridge PRIVATE
    -fno-lto
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3ProgrammerC1EPNS_2UC23IFirmwareUpdateListenerEPKhj
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3ProgrammerD1Ev
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer4openEPKc
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer5closeEv
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer6updateEv
    -Wl,--wrap=_ZN8Presonus4DICE15Dice3Programmer8eraseAllEv
  )
  add_test(NAME dice_manager_firmware_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_manager_firmware_replay.py
    --binary $<TARGET_FILE:dice_manager_firmware_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-firmware/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-firmware/fixtures.jsonl)
  add_test(NAME dice_manager_firmware_exceptions COMMAND dice_manager_firmware_bridge --exception-smoke)
  add_executable(dice_manager_firmware_provider tests/dice_manager_firmware_provider.cpp)
  target_link_libraries(dice_manager_firmware_provider PRIVATE presonus::cs18_components)
  target_compile_options(dice_manager_firmware_provider PRIVATE -fno-lto)
  target_link_options(dice_manager_firmware_provider PRIVATE
    -fno-lto
    -Wl,--wrap=open
    -Wl,--wrap=__open_2
    -Wl,--wrap=close
    -Wl,--wrap=ioctl
  )
  add_test(NAME dice_manager_firmware_provider COMMAND dice_manager_firmware_provider)
  add_executable(uc_network_adapter_services_bridge tests/network_adapter_services/adapter_services_bridge.cpp)
  target_link_libraries(uc_network_adapter_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_adapter_services_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_adapter_services_bridge PRIVATE -fno-lto
    -Wl,--wrap=getifaddrs
    -Wl,--wrap=freeifaddrs
    -Wl,--wrap=gethostname
    -Wl,--wrap=inet_ntop
    -Wl,--wrap=__printf_chk
    -Wl,--wrap=getaddrinfo
    -Wl,--wrap=gethostbyname
    -Wl,--wrap=getnameinfo
    -Wl,--wrap=socket
    -Wl,--wrap=connect
    -Wl,--wrap=sendto
    -Wl,--wrap=sendmsg
  )
  add_test(NAME uc_network_adapter_services COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_adapter_services_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-adapter-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-adapter-services/expected.txt --cases 1574)
  add_executable(dsp_formatters_tests tests/dsp_formatters_tests.cpp)
  target_link_libraries(dsp_formatters_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatters_tests PRIVATE -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  add_test(NAME dsp_formatters_retained COMMAND dsp_formatters_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-formatters/fixtures.txt)
  add_executable(uc_network_discovery_services_bridge
    tests/network_discovery_services/discovery_services_bridge.cpp
    tests/network_discovery_services/discovery_virtual_entry.cpp)
  target_link_libraries(uc_network_discovery_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_discovery_services_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_discovery_services_bridge PRIVATE -fno-lto)
  add_test(NAME uc_network_discovery_services COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_discovery_services_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-discovery-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-discovery-services/expected.txt --cases 1586)
  add_executable(dsp_additional_formatters_tests tests/dsp_additional_formatters_tests.cpp)
  target_link_libraries(dsp_additional_formatters_tests PRIVATE presonus_uc)
  target_compile_options(dsp_additional_formatters_tests PRIVATE -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  add_test(NAME dsp_additional_formatters_retained COMMAND dsp_additional_formatters_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-additional-formatters/fixtures.txt)
  add_executable(string_utils_bridge tests/string_utils_bridge.cpp)
  target_link_libraries(string_utils_bridge PRIVATE presonus::cs18_components)
  target_compile_options(string_utils_bridge PRIVATE -fno-lto)
  add_test(NAME string_utils_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:string_utils_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/string-utils/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/string-utils/expected.txt --cases 588)
  add_executable(dice_subsystem_control_bridge tests/dice_subsystem_control_bridge.cpp)
  target_link_libraries(dice_subsystem_control_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_subsystem_control_bridge PRIVATE -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dice_subsystem_control_bridge PRIVATE
    -fno-lto
    -Wl,--wrap=_Znwm
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3UartC2Ev
    -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE
    -Wl,--wrap=_ZN8Presonus4DICE12Dice3Manager12getDice3InfoEPNS0_8DiceInfoE
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3SubsystemC1Ev
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3SubsystemC2Ev
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3SubsystemD1Ev
    -Wl,--wrap=_ZN8Presonus4DICE14Dice3SubsystemD2Ev
  )
  add_test(NAME dice_subsystem_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_subsystem_control_replay.py
    --binary $<TARGET_FILE:dice_subsystem_control_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-subsystem-control/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-subsystem-control/fixtures.jsonl)
  add_executable(dice_subsystem_runtime_provider tests/dice_subsystem_runtime_provider.cpp)
  target_link_libraries(dice_subsystem_runtime_provider PRIVATE presonus::cs18_components)
  target_compile_options(dice_subsystem_runtime_provider PRIVATE -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dice_subsystem_runtime_provider PRIVATE
    -fno-lto
    -Wl,--wrap=open
    -Wl,--wrap=__open_2
    -Wl,--wrap=close
    -Wl,--wrap=ioctl
    -Wl,--wrap=fopen
    -Wl,--wrap=fclose
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart4postERNS0_11SysexPacketE
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart6onIdleEv
  )
  add_test(NAME dice_subsystem_runtime_provider COMMAND dice_subsystem_runtime_provider)
  add_executable(dsp_formatter_lifecycle_tests tests/dsp_formatter_lifecycle_tests.cpp)
  target_link_libraries(dsp_formatter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatter_lifecycle_tests PRIVATE -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_formatter_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_formatter_lifecycle_tests COMMAND dsp_formatter_lifecycle_tests)
  add_executable(uc_network_multicast_socket_bridge tests/network_multicast_sockets/multicast_socket_bridge.cpp)
  target_link_libraries(uc_network_multicast_socket_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_multicast_socket_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_multicast_socket_bridge PRIVATE -fno-lto
    -Wl,--wrap=_Znwm
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN4Core8Platform11PosixSocketC1Eiii
    -Wl,--wrap=_ZN4Core8Platform11PosixSocketD1Ev
    -Wl,--wrap=_ZN4Core8Platform11PosixSocket9setOptionEii
    -Wl,--wrap=_ZN4Core8Platform11PosixSocket4bindERKNS_7Sockets11SocketTypes13SocketAddressE
    -Wl,--wrap=_ZNK4Core8Platform11PosixSocket15getLocalAddressERNS_7Sockets11SocketTypes13SocketAddressE
    -Wl,--wrap=_ZN4Core8Platform11PosixSocket18joinMulticastGroupERKNS_7Sockets11SocketTypes9IPAddressES6_
    -Wl,--wrap=_ZNK4Core8Platform11PosixSocket10isAnyErrorEi
    -Wl,--wrap=socket
    -Wl,--wrap=close
    -Wl,--wrap=fcntl
    -Wl,--wrap=bind
    -Wl,--wrap=getsockname
    -Wl,--wrap=setsockopt
    -Wl,--wrap=getifaddrs
    -Wl,--wrap=freeifaddrs
    -Wl,--wrap=select
    -Wl,--wrap=getsockopt
    -Wl,--wrap=clock_gettime
    -Wl,--wrap=__printf_chk
    -Wl,--wrap=getaddrinfo
    -Wl,--wrap=gethostbyname
    -Wl,--wrap=getnameinfo
    -Wl,--wrap=connect
    -Wl,--wrap=sendto
    -Wl,--wrap=sendmsg
    -Wl,--wrap=accept
    -Wl,--wrap=freeaddrinfo
    -Wl,--wrap=gethostname
    -Wl,--wrap=getpeername
    -Wl,--wrap=ioctl
    -Wl,--wrap=listen
    -Wl,--wrap=recv
    -Wl,--wrap=recvfrom
    -Wl,--wrap=send
    -Wl,--wrap=shutdown
    -Wl,--wrap=pthread_create
  )
  add_test(NAME uc_network_multicast_sockets COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_multicast_socket_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-multicast-sockets/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-multicast-sockets/expected.txt --cases 742)
  add_executable(dsp_formatter_option_lifecycle_tests tests/dsp_formatter_option_lifecycle_tests.cpp)
  target_link_libraries(dsp_formatter_option_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatter_option_lifecycle_tests PRIVATE -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_formatter_option_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_formatter_option_lifecycle_tests COMMAND dsp_formatter_option_lifecycle_tests)
  add_executable(dice_manager_lifecycle_tests tests/dice_manager_lifecycle_tests.cpp)
  target_link_libraries(dice_manager_lifecycle_tests PRIVATE presonus::cs18_components)
  target_compile_options(dice_manager_lifecycle_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dice_manager_lifecycle_tests PRIVATE -Wl,--wrap=pthread_create -Wl,--wrap=pthread_join -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dice_manager_lifecycle COMMAND dice_manager_lifecycle_tests)
  add_test(NAME dice_manager_lifecycle_shutdown COMMAND dice_manager_lifecycle_tests shutdown)
  add_executable(dice_receiver_state_sync_tests tests/dice_receiver_state_sync_tests.cpp)
  target_link_libraries(dice_receiver_state_sync_tests PRIVATE presonus::cs18_components)
  target_compile_options(dice_receiver_state_sync_tests PRIVATE -fno-rtti -fno-lto)
  add_test(NAME dice_receiver_state_sync COMMAND dice_receiver_state_sync_tests)
  add_executable(uc_network_discovery_ownership_bridge
    tests/network_discovery_lifecycle/ownership_bridge.cpp
    tests/network_discovery_lifecycle/ownership_virtual_entry.cpp)
  target_link_libraries(uc_network_discovery_ownership_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_discovery_ownership_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_discovery_ownership_bridge PRIVATE -fno-lto
    -Wl,--wrap=_Znwm
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE
    -Wl,--wrap=_ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE
    -Wl,--wrap=_ZN8Presonus2UC15BasicConnection9sendEventERKNS0_5EventE
    -Wl,--wrap=socket
    -Wl,--wrap=connect
    -Wl,--wrap=bind
    -Wl,--wrap=close
    -Wl,--wrap=setsockopt
    -Wl,--wrap=fcntl
    -Wl,--wrap=getsockname
    -Wl,--wrap=getsockopt
    -Wl,--wrap=select
    -Wl,--wrap=accept
    -Wl,--wrap=getpeername
    -Wl,--wrap=ioctl
    -Wl,--wrap=listen
    -Wl,--wrap=recv
    -Wl,--wrap=recvfrom
    -Wl,--wrap=send
    -Wl,--wrap=sendto
    -Wl,--wrap=sendmsg
    -Wl,--wrap=shutdown
    -Wl,--wrap=gethostname
    -Wl,--wrap=pthread_create
    -Wl,--wrap=getifaddrs
    -Wl,--wrap=freeifaddrs
    -Wl,--wrap=getaddrinfo
    -Wl,--wrap=freeaddrinfo
    -Wl,--wrap=getnameinfo
    -Wl,--wrap=gethostbyname
    -Wl,--wrap=clock_gettime
  )
  add_test(NAME uc_network_discovery_ownership COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_discovery_ownership_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-discovery-lifecycle/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-discovery-lifecycle/expected.txt --cases 1132)
  add_executable(dsp_fader_curve_bridge tests/dsp_fader_curve_bridge.cpp)
  target_link_libraries(dsp_fader_curve_bridge PRIVATE presonus_uc)
  target_compile_options(dsp_fader_curve_bridge PRIVATE -fno-rtti -fno-lto)
  add_test(NAME dsp_fader_curve_retained COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:dsp_fader_curve_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-fader-curve/stdin.txt --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-fader-curve/expected.txt --cases 7392)
  add_executable(dsp_fader_curve_lifecycle_tests tests/dsp_fader_curve_lifecycle_tests.cpp)
  target_link_libraries(dsp_fader_curve_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_fader_curve_lifecycle_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_fader_curve_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm)
  add_test(NAME dsp_fader_curve_lifecycle COMMAND dsp_fader_curve_lifecycle_tests)
  add_executable(noaa_router_commands_tests tests/noaa_router_commands_tests.cpp)
  target_link_libraries(noaa_router_commands_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_commands_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_commands_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx)
  add_test(NAME noaa_router_commands COMMAND noaa_router_commands_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-route-commands/stdin.txt)
  add_executable(noaa_router_provider_tests tests/noaa_router_provider_tests.cpp)
  target_link_libraries(noaa_router_provider_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_provider_tests PRIVATE -fno-rtti -fno-lto)
  target_link_options(noaa_router_provider_tests PRIVATE -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
  add_test(NAME noaa_router_provider_idle COMMAND noaa_router_provider_tests)
  add_test(NAME noaa_router_provider_zero COMMAND noaa_router_provider_tests --zero-transfer)
  add_executable(dice_packet_queue_lifetime_tests tests/dice_packet_queue_lifetime_tests.cpp)
  target_link_libraries(dice_packet_queue_lifetime_tests PRIVATE presonus::uc)
  target_link_options(dice_packet_queue_lifetime_tests PRIVATE
    -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dice_packet_queue_lifetime_tests COMMAND dice_packet_queue_lifetime_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-packet-queue-continuation/fixtures.txt)
  # Keep recovered-source verification assertions enabled in Release.
  target_compile_options(dsp_fader_curve_bridge PRIVATE -UNDEBUG)
  target_compile_options(dsp_fader_curve_lifecycle_tests PRIVATE -UNDEBUG)
  target_compile_options(dice_packet_queue_lifetime_tests PRIVATE -UNDEBUG)
  target_compile_options(noaa_router_commands_tests PRIVATE -UNDEBUG)
  target_compile_options(noaa_router_provider_tests PRIVATE -UNDEBUG)
  add_executable(dsp_bpm_counter_lifecycle_tests tests/dsp_bpm_counter_lifecycle_tests.cpp)
  target_link_libraries(dsp_bpm_counter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_bpm_counter_lifecycle_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_bpm_counter_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_bpm_counter_lifecycle_tests COMMAND dsp_bpm_counter_lifecycle_tests)
  add_executable(noaa_router_control_tests tests/noaa_router_control_tests.cpp)
  target_link_libraries(noaa_router_control_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_control_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_control_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_router_control_original COMMAND noaa_router_control_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-control/stdin.txt)
  add_test(NAME noaa_router_control_source_locks COMMAND noaa_router_control_tests --source-locks)
  add_executable(packet_queue_operations_tests tests/packet_queue_operations_tests.cpp)
  target_link_libraries(packet_queue_operations_tests PRIVATE presonus::uc)
  target_compile_options(packet_queue_operations_tests PRIVATE -UNDEBUG)
  target_link_options(packet_queue_operations_tests PRIVATE
    -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock)
  add_test(NAME packet_queue_operations_tests COMMAND packet_queue_operations_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/packet-queue-operations/fixtures.txt)
  add_executable(dsp_gate_meter_lifecycle_tests tests/dsp_gate_meter_lifecycle_tests.cpp)
  target_link_libraries(dsp_gate_meter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gate_meter_lifecycle_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_gate_meter_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm)
  add_test(NAME dsp_gate_meter_lifecycle_tests COMMAND dsp_gate_meter_lifecycle_tests)
  add_executable(noaa_router_lookup_tests tests/noaa_router_lookup_tests.cpp)
  target_link_libraries(noaa_router_lookup_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_lookup_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto)
  add_test(NAME noaa_router_lookups COMMAND noaa_router_lookup_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-lookups/stdin.txt)
  add_executable(dsp_param_descriptor_list_tests tests/dsp_param_descriptor_list_tests.cpp)
  target_link_libraries(dsp_param_descriptor_list_tests PRIVATE presonus_uc)
  target_compile_options(dsp_param_descriptor_list_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_param_descriptor_list_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit -Wl,--wrap=_ZN4Core18LinearInterpolatorC1Eff)
  add_test(NAME dsp_param_descriptor_list_tests COMMAND dsp_param_descriptor_list_tests)
  add_executable(uc_message_attributes_tests tests/message_attributes_tests.cpp)
  target_link_libraries(uc_message_attributes_tests PRIVATE presonus::uc)
  target_compile_options(uc_message_attributes_tests PRIVATE -fno-rtti -UNDEBUG)
  target_link_options(uc_message_attributes_tests PRIVATE
    -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN4Core8Portable18AttributeAllocator10getDefaultEv
    -Wl,--wrap=_ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE
    -Wl,--wrap=_ZN4Core8Portable10AttributesD2Ev
    -Wl,--wrap=_ZNK4Core8Portable10Attributes9getStringEPKc
    -Wl,--wrap=_ZN4Core8Portable10Attributes11lookupOrAddEPKc
    -Wl,--wrap=_ZN4Core8Portable14AttributeValue3setEPKcb)
  add_test(NAME uc_message_attributes_tests COMMAND uc_message_attributes_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/message-attributes/fixtures.txt)
  add_executable(noaa_setup_property_tests tests/noaa_setup_property_tests.cpp)
  target_link_libraries(noaa_setup_property_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_setup_property_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  add_test(NAME noaa_setup_property COMMAND noaa_setup_property_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-setup-property/stdin.txt)
  add_executable(noaa_tcard_setup_tests tests/noaa_tcard_setup_tests.cpp)
  target_link_libraries(noaa_tcard_setup_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_setup_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_tcard_setup_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA8TCardSPI4openEPKc -Wl,--wrap=_ZN4Core8Platform13CurrentThread5sleepEj)
  add_test(NAME noaa_tcard_setup COMMAND noaa_tcard_setup_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-setup/stdin.txt)
  add_executable(dsp_eq_parameter_lists_tests tests/dsp_eq_parameter_lists_tests.cpp)
  target_link_libraries(dsp_eq_parameter_lists_tests PRIVATE presonus_uc)
  target_compile_options(dsp_eq_parameter_lists_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_eq_parameter_lists_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_eq_parameter_lists_metadata COMMAND dsp_eq_parameter_lists_tests unconfigured)
  add_test(NAME dsp_eq_parameter_lists_bootstrap COMMAND dsp_eq_parameter_lists_tests bootstrap)
  add_executable(dsp_eq_source_providers_tests tests/dsp_eq_source_providers_tests.cpp)
  target_link_libraries(dsp_eq_source_providers_tests PRIVATE presonus_uc)
  target_compile_options(dsp_eq_source_providers_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  add_test(NAME dsp_eq_source_providers_math_bootstrap COMMAND dsp_eq_source_providers_tests normal)
  add_test(NAME dsp_eq_source_providers_formatter_conflict COMMAND dsp_eq_source_providers_tests formatter-conflict)
  add_test(NAME dsp_eq_source_providers_factory_conflict COMMAND dsp_eq_source_providers_tests factory-conflict)
  add_executable(uc_message_attributes_event_tests tests/message_attributes_event_tests.cpp)
  target_link_libraries(uc_message_attributes_event_tests PRIVATE presonus::uc ZLIB::ZLIB)
  target_compile_options(uc_message_attributes_event_tests PRIVATE -fno-rtti -UNDEBUG)
  target_link_options(uc_message_attributes_event_tests PRIVATE
    -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN4Core8Portable18AttributeAllocator10getDefaultEv
    -Wl,--wrap=_ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE
    -Wl,--wrap=_ZN4Core8Portable10Attributes9removeAllEv
    -Wl,--wrap=_ZN4Core2IO12MemoryStreamC1EPvj
    -Wl,--wrap=_ZN4Core2IO12MemoryStreamC1Ej
    -Wl,--wrap=_ZN4Core8Portable22ThreadAwareCompression5unzipERNS_2IO6StreamEPKvii
    -Wl,--wrap=_ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi
    -Wl,--wrap=_ZN4Core8Portable8Archiver4loadERNS0_10AttributesE
    -Wl,--wrap=_ZN4Core2IO6BufferD1Ev
    -Wl,--wrap=_ZN4Core2IO6BufferD2Ev)
  add_test(NAME uc_message_attributes_event_tests COMMAND uc_message_attributes_event_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/message-attributes-event/fixtures.txt)
  add_executable(noaa_tcard_status_tests tests/noaa_tcard_status_tests.cpp)
  target_link_libraries(noaa_tcard_status_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_status_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_tcard_status_tests PRIVATE -Wl,--wrap=_ZN8Presonus15ResourceLibrary3getEPKc -Wl,--wrap=_ZN8Presonus15ResourceLibrary18getRequiredVersionEPKc -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
  add_test(NAME noaa_tcard_status COMMAND noaa_tcard_status_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-status/stdin.txt)
  add_executable(uc_mutable_message_event_tests tests/mutable_message_event_tests.cpp)
  target_link_libraries(uc_mutable_message_event_tests PRIVATE presonus::uc ZLIB::ZLIB)
  target_compile_options(uc_mutable_message_event_tests PRIVATE -fno-rtti -UNDEBUG)
  target_link_options(uc_mutable_message_event_tests PRIVATE
    -Wl,--wrap=_ZN4Core2IO6BufferC1EPvjb
    -Wl,--wrap=_ZN4Core2IO6Buffer6resizeEj
    -Wl,--wrap=_ZN4Core2IO6Buffer4takeERS1_
    -Wl,--wrap=_ZN4Core2IO12MemoryStreamC1Ej
    -Wl,--wrap=_ZNK4Core2IO12MemoryStream9getBufferEv
    -Wl,--wrap=_ZNK4Core2IO12MemoryStream15getBytesWrittenEv
    -Wl,--wrap=_ZN4Core2IO12MemoryStream14allocateMemoryEjb
    -Wl,--wrap=_ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi
    -Wl,--wrap=_ZN4Core8Portable8Archiver4saveERKNS0_10AttributesE
    -Wl,--wrap=_ZN4Core8Portable22ThreadAwareCompression3zipERNS_2IO6StreamEPKvii
    -Wl,--wrap=_ZN4Core2IO6BufferD1Ev
    -Wl,--wrap=_ZN4Core2IO6BufferD2Ev
    -Wl,--wrap=core_free
)
  add_test(NAME uc_mutable_message_event_tests COMMAND uc_mutable_message_event_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/mutable-message-event/fixtures.txt)
  add_executable(noaa_tcard_command_tests tests/noaa_tcard_command_tests.cpp)
  target_link_libraries(noaa_tcard_command_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_command_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_tcard_command_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
  add_test(NAME noaa_tcard_commands COMMAND noaa_tcard_command_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-commands/stdin.txt)
  add_executable(dsp_eq8_limiter_parameter_lists_tests tests/dsp_eq8_limiter_parameter_lists_tests.cpp)
  target_link_libraries(dsp_eq8_limiter_parameter_lists_tests PRIVATE presonus_uc)
  target_compile_options(dsp_eq8_limiter_parameter_lists_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_eq8_limiter_parameter_lists_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_eq8_limiter_metadata COMMAND dsp_eq8_limiter_parameter_lists_tests unconfigured)
  add_test(NAME dsp_eq8_limiter_bootstrap COMMAND dsp_eq8_limiter_parameter_lists_tests bootstrap)
  add_executable(uc_message_queue_tests tests/message_queue_tests.cpp)
  target_link_libraries(uc_message_queue_tests PRIVATE presonus::uc)
  target_compile_options(uc_message_queue_tests PRIVATE -fno-rtti -UNDEBUG)
  target_link_options(uc_message_queue_tests PRIVATE
    -Wl,--wrap=_Znwm
    -Wl,--wrap=_ZdlPv
    -Wl,--wrap=_ZdlPvm
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLockD1Ev
    -Wl,--wrap=_ZN4Core8Platform9PosixLockD2Ev
)
  add_test(NAME uc_message_queue_tests COMMAND uc_message_queue_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/message-queue/fixtures.txt)
  add_executable(noaa_tcard_rate_status_tests tests/noaa_tcard_rate_status_tests.cpp)
  target_link_libraries(noaa_tcard_rate_status_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_rate_status_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_tcard_rate_status_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz)
  add_test(NAME noaa_tcard_rate_status COMMAND noaa_tcard_rate_status_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-rate-status/stdin.txt)
  add_executable(dsp_eq_control_biquad_tests tests/dsp_eq_control_biquad_tests.cpp)
  target_link_libraries(dsp_eq_control_biquad_tests PRIVATE presonus_cs18_components)
  target_compile_options(dsp_eq_control_biquad_tests PRIVATE -UNDEBUG -fno-lto)
  add_test(NAME dsp_eq_control_biquad COMMAND dsp_eq_control_biquad_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-eq-control-biquad/validation/original-02/vectors.txt)
  add_executable(uc_network_activity_manager_tests tests/network_activity_manager_tests.cpp)
  target_link_libraries(uc_network_activity_manager_tests PRIVATE presonus::uc)
  target_compile_options(uc_network_activity_manager_tests PRIVATE -UNDEBUG)
  target_link_options(uc_network_activity_manager_tests PRIVATE
    -Wl,--wrap=_Znam
    -Wl,--wrap=_ZdaPv
    -Wl,--wrap=_ZdaPvm
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLockD1Ev
    -Wl,--wrap=_ZN4Core8Platform9PosixLockD2Ev
)
  add_test(NAME uc_network_activity_manager_tests COMMAND uc_network_activity_manager_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/network-activity/fixtures.txt)
  add_executable(dsp_filter_parameter_lists_tests tests/dsp_filter_parameter_lists_tests.cpp)
  target_link_libraries(dsp_filter_parameter_lists_tests PRIVATE presonus_uc)
  target_compile_options(dsp_filter_parameter_lists_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_filter_parameter_lists_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_filter_parameter_lists_metadata COMMAND dsp_filter_parameter_lists_tests unconfigured)
  add_test(NAME dsp_filter_parameter_lists_bootstrap COMMAND dsp_filter_parameter_lists_tests bootstrap)
  add_executable(dsp_filter_registry_exit_tests tests/dsp_filter_registry_exit_tests.cpp)
  target_link_libraries(dsp_filter_registry_exit_tests PRIVATE presonus_uc)
  target_compile_options(dsp_filter_registry_exit_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_filter_registry_exit_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_filter_registry_exit COMMAND dsp_filter_registry_exit_tests)
  add_test(NAME dsp_eq_source_providers_integer_frequency_conflict COMMAND dsp_eq_source_providers_tests integer-frequency-conflict)
  add_executable(uc_client_state_tracking_tests tests/client_state_tracking_tests.cpp)
  target_link_libraries(uc_client_state_tracking_tests PRIVATE presonus::uc)
  target_compile_options(uc_client_state_tracking_tests PRIVATE -UNDEBUG)
  target_link_options(uc_client_state_tracking_tests PRIVATE -Wl,--wrap=clock_gettime)
  add_test(NAME uc_client_state_tracking_tests COMMAND uc_client_state_tracking_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/client-state-tracking/fixtures.txt)
  target_compile_options(dsp_additional_formatters_tests PRIVATE -UNDEBUG)
  add_executable(noaa_tcard_receive_start_tests tests/noaa_tcard_receive_start_tests.cpp)
  target_link_libraries(noaa_tcard_receive_start_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_receive_start_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_tcard_receive_start_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver15waitResponseSetERjx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN8Presonus4NOAA8TCardSPI6onIdleEb -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_)
  add_test(NAME noaa_tcard_receive_start COMMAND noaa_tcard_receive_start_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-receive-start/stdin.txt)
  add_executable(dsp_gain_pan_family_tests tests/dsp_gain_pan_family_tests.cpp)
  target_link_libraries(dsp_gain_pan_family_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gain_pan_family_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_gain_pan_family_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_gain_pan_family COMMAND dsp_gain_pan_family_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-gain-pan-family/validation/original-01/client-vectors.txt)
  add_executable(dsp_fader_interpolator_tests tests/dsp_fader_interpolator_tests.cpp)
  target_link_libraries(dsp_fader_interpolator_tests PRIVATE presonus_uc)
  target_compile_options(dsp_fader_interpolator_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_fader_interpolator_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_fader_interpolator COMMAND dsp_fader_interpolator_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-fader-interpolator/validation/original-03/client-vectors.txt)
  add_executable(noaa_router_routes_tests tests/noaa_router_routes_tests.cpp)
  target_link_libraries(noaa_router_routes_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_routes_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto)
  target_link_options(noaa_router_routes_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_router_routes_tests COMMAND noaa_router_routes_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-routes/stdin.txt)
  add_executable(noaa_tcard_handler_tests tests/noaa_tcard_handler_tests.cpp)
  target_link_libraries(noaa_tcard_handler_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_tcard_handler_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto)
  target_link_options(noaa_tcard_handler_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA5TCard17getStatusPropertyERNS0_18NOAAStatusPropertyE -Wl,--wrap=_ZN8Presonus4NOAA5TCard20generateAlternateMacEj -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx)
  add_test(NAME noaa_tcard_handler_tests COMMAND noaa_tcard_handler_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-tcard-handler/stdin.txt)
  add_executable(uc_client_event_values_tests tests/client_event_values_tests.cpp)
  target_link_libraries(uc_client_event_values_tests PRIVATE presonus::uc)
  target_compile_options(uc_client_event_values_tests PRIVATE -UNDEBUG)
  target_link_options(uc_client_event_values_tests PRIVATE -Wl,--wrap=socket -Wl,--wrap=connect -Wl,--wrap=getaddrinfo -Wl,--wrap=getifaddrs)
  add_test(NAME uc_client_event_values_tests COMMAND uc_client_event_values_tests)

  add_executable(noaa_ucnet_handler_tests tests/noaa_ucnet_handler_tests.cpp)
  target_link_libraries(noaa_ucnet_handler_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_ucnet_handler_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_ucnet_handler_tests PRIVATE -Wl,--wrap=clock_gettime)
  add_test(NAME noaa_ucnet_handler_tests COMMAND noaa_ucnet_handler_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-ucnet-handler/stdin.txt)
  add_executable(uc_client_connection_dispatch_tests tests/client_connection_dispatch_tests.cpp)
  target_link_libraries(uc_client_connection_dispatch_tests PRIVATE presonus::uc)
  target_compile_options(uc_client_connection_dispatch_tests PRIVATE -UNDEBUG)
  target_link_options(uc_client_connection_dispatch_tests PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_client_connection_dispatch_tests COMMAND uc_client_connection_dispatch_tests)

  add_executable(dsp_compressor_parameter_list_tests tests/dsp_compressor_parameter_list_tests.cpp)
  target_link_libraries(dsp_compressor_parameter_list_tests PRIVATE presonus_uc)
  target_compile_options(dsp_compressor_parameter_list_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_compressor_parameter_list_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_compressor_metadata COMMAND dsp_compressor_parameter_list_tests unconfigured)
  add_test(NAME dsp_compressor_bootstrap COMMAND dsp_compressor_parameter_list_tests bootstrap)
  add_executable(dsp_compressor_source_providers_tests tests/dsp_compressor_source_providers_tests.cpp)
  target_link_libraries(dsp_compressor_source_providers_tests PRIVATE presonus_uc)
  target_compile_options(dsp_compressor_source_providers_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  add_test(NAME dsp_compressor_providers_normal COMMAND dsp_compressor_source_providers_tests normal)
  add_test(NAME dsp_compressor_providers_without_eq COMMAND dsp_compressor_source_providers_tests without-eq)
  add_test(NAME dsp_compressor_providers_time_conflict COMMAND dsp_compressor_source_providers_tests time-conflict)
  add_test(NAME dsp_compressor_providers_ratio_conflict COMMAND dsp_compressor_source_providers_tests ratio-conflict)
  add_test(NAME dsp_compressor_providers_range_conflict COMMAND dsp_compressor_source_providers_tests range-conflict)
  add_test(NAME dsp_compressor_providers_factory_conflict COMMAND dsp_compressor_source_providers_tests factory-conflict)
  add_executable(dsp_compressor_registry_exit_tests tests/dsp_compressor_registry_exit_tests.cpp)
  target_link_libraries(dsp_compressor_registry_exit_tests PRIVATE presonus_uc)
  target_compile_options(dsp_compressor_registry_exit_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_compressor_registry_exit_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_compressor_registry_exit COMMAND dsp_compressor_registry_exit_tests)
  add_executable(noaa_router_bus_routes_tests tests/noaa_router_bus_routes_tests.cpp)
  target_link_libraries(noaa_router_bus_routes_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_bus_routes_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_bus_routes_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_router_bus_routes_tests COMMAND noaa_router_bus_routes_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-bus-routes/stdin.txt)
  add_executable(uc_onoff_formatter_tests tests/uc_onoff_formatter_tests.cpp)
  target_link_libraries(uc_onoff_formatter_tests PRIVATE presonus_uc)
  target_compile_options(uc_onoff_formatter_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(uc_onoff_formatter_tests PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_onoff_formatter COMMAND uc_onoff_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-gate-parameter-list/validation/onoff-original-03/vectors.tsv)
  add_executable(noaa_router_geq_input_routes_tests tests/noaa_router_geq_input_routes_tests.cpp)
  target_link_libraries(noaa_router_geq_input_routes_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_geq_input_routes_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_geq_input_routes_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_router_geq_input_routes_tests COMMAND noaa_router_geq_input_routes_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-geq-input-routes/stdin.txt)
  add_executable(uc_event_queue_lifecycle_tests tests/event_queue_lifecycle_tests.cpp)
  target_link_libraries(uc_event_queue_lifecycle_tests PRIVATE presonus::uc)
  target_compile_options(uc_event_queue_lifecycle_tests PRIVATE -UNDEBUG -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(uc_event_queue_lifecycle_tests PRIVATE -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock -Wl,--wrap=pthread_mutex_destroy -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_event_queue_lifecycle_tests COMMAND uc_event_queue_lifecycle_tests )
  add_executable(uc_owned_event_queue_coalescer_replay tests/owned_event_queue_coalescer_replay.cpp)
  target_link_libraries(uc_owned_event_queue_coalescer_replay PRIVATE presonus::uc)
  target_compile_options(uc_owned_event_queue_coalescer_replay PRIVATE -UNDEBUG -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(uc_owned_event_queue_coalescer_replay PRIVATE -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock -Wl,--wrap=pthread_mutex_destroy)
  add_test(NAME uc_owned_event_queue_coalescer_replay COMMAND uc_owned_event_queue_coalescer_replay ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-event-queue/arm-vectors.bin)
  add_executable(dsp_gate_parameter_list_tests tests/dsp_gate_parameter_list_tests.cpp)
  target_link_libraries(dsp_gate_parameter_list_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gate_parameter_list_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_gate_parameter_list_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_gate_metadata COMMAND dsp_gate_parameter_list_tests unconfigured)
  add_test(NAME dsp_gate_bootstrap COMMAND dsp_gate_parameter_list_tests bootstrap)
  add_executable(dsp_gate_source_providers_tests tests/dsp_gate_source_providers_tests.cpp)
  target_link_libraries(dsp_gate_source_providers_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gate_source_providers_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  add_test(NAME dsp_gate_providers_normal COMMAND dsp_gate_source_providers_tests normal)
  add_test(NAME dsp_gate_providers_without_eq COMMAND dsp_gate_source_providers_tests without-eq)
  add_test(NAME dsp_gate_providers_without_compressor COMMAND dsp_gate_source_providers_tests without-compressor)
  add_test(NAME dsp_gate_providers_onoff_conflict COMMAND dsp_gate_source_providers_tests onoff-conflict)
  add_test(NAME dsp_gate_providers_exp_conflict COMMAND dsp_gate_source_providers_tests exp-conflict)
  add_test(NAME dsp_gate_providers_gaterange_conflict COMMAND dsp_gate_source_providers_tests gaterange-conflict)
  add_test(NAME dsp_gate_providers_invalid_labels COMMAND dsp_gate_source_providers_tests invalid-labels)
  add_executable(dsp_gate_registry_exit_tests tests/dsp_gate_registry_exit_tests.cpp)
  target_link_libraries(dsp_gate_registry_exit_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gate_registry_exit_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  target_link_options(dsp_gate_registry_exit_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_gate_registry_exit COMMAND dsp_gate_registry_exit_tests )
  add_executable(dsp_gate_core_consumer_tests tests/dsp_gate_core_consumer_tests.cpp)
  target_link_libraries(dsp_gate_core_consumer_tests PRIVATE presonus_uc)
  target_compile_options(dsp_gate_core_consumer_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG)
  add_test(NAME dsp_gate_core_consumer COMMAND dsp_gate_core_consumer_tests )
  add_executable(dsp_geq_parameter_list_tests tests/dsp_geq_parameter_list_tests.cpp)
  target_link_libraries(dsp_geq_parameter_list_tests PRIVATE presonus_uc)
  target_compile_options(dsp_geq_parameter_list_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  target_link_options(dsp_geq_parameter_list_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_geq_metadata COMMAND dsp_geq_parameter_list_tests unconfigured)
  add_test(NAME dsp_geq_bootstrap COMMAND dsp_geq_parameter_list_tests bootstrap)
  add_executable(dsp_geq_source_providers_tests tests/dsp_geq_source_providers_tests.cpp)
  target_link_libraries(dsp_geq_source_providers_tests PRIVATE presonus_uc)
  target_compile_options(dsp_geq_source_providers_tests PRIVATE -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively -UNDEBUG -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  add_test(NAME dsp_geq_source_providers COMMAND dsp_geq_source_providers_tests normal)
  add_test(NAME dsp_geq_source_providers_conflict COMMAND dsp_geq_source_providers_tests conflict)
  add_test(NAME dsp_gate_interpolation_math COMMAND dsp_interpolators_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-gate-parameter-list/validation/gate-math-original-01/vectors.txt ${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/dsp-gate-interpolation-differences.txt)
  add_executable(dsp_ratio_formatter_lifecycle_tests tests/dsp_ratio_formatter_lifecycle_tests.cpp)
  target_link_libraries(dsp_ratio_formatter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_ratio_formatter_lifecycle_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_ratio_formatter_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_ratio_formatter_lifecycle COMMAND dsp_ratio_formatter_lifecycle_tests )
  add_executable(dsp_milliseconds_formatter_lifecycle_tests tests/dsp_milliseconds_formatter_lifecycle_tests.cpp)
  target_link_libraries(dsp_milliseconds_formatter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_milliseconds_formatter_lifecycle_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_milliseconds_formatter_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_milliseconds_formatter_lifecycle COMMAND dsp_milliseconds_formatter_lifecycle_tests )
  add_executable(dsp_milliseconds_singleton_tests tests/dsp_milliseconds_singleton_tests.cpp)
  target_link_libraries(dsp_milliseconds_singleton_tests PRIVATE presonus_uc)
  target_compile_options(dsp_milliseconds_singleton_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_milliseconds_singleton_tests PRIVATE -Wl,--wrap=__cxa_atexit)
  add_test(NAME dsp_milliseconds_singleton_false COMMAND dsp_milliseconds_singleton_tests false)
  add_test(NAME dsp_milliseconds_singleton_true COMMAND dsp_milliseconds_singleton_tests true)
  add_test(NAME dsp_milliseconds_singleton_threads COMMAND dsp_milliseconds_singleton_tests threads)
  add_executable(uc_midi_connection_lifecycle tests/uc_midi_connection_lifecycle_tests.cpp)
  target_link_libraries(uc_midi_connection_lifecycle PRIVATE presonus::uc)
  target_compile_options(uc_midi_connection_lifecycle PRIVATE -UNDEBUG -fno-lto -fsized-deallocation -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(uc_midi_connection_lifecycle PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_midi_connection_lifecycle COMMAND uc_midi_connection_lifecycle )
  add_executable(noaa_router_mixer_input_routes_tests tests/noaa_router_mixer_input_routes_tests.cpp)
  target_link_libraries(noaa_router_mixer_input_routes_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_mixer_input_routes_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_mixer_input_routes_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME noaa_router_mixer_input_routes_tests COMMAND noaa_router_mixer_input_routes_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-mixer-input-routes/stdin.txt)
  add_executable(dsp_exp_bilinear_lifecycle_tests tests/dsp_exp_bilinear_lifecycle_tests.cpp)
  target_link_libraries(dsp_exp_bilinear_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_exp_bilinear_lifecycle_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_exp_bilinear_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_exp_bilinear_lifecycle COMMAND dsp_exp_bilinear_lifecycle_tests lifecycle)
  add_test(NAME dsp_exp_bilinear_constructor_virtual_fixtures COMMAND dsp_exp_bilinear_lifecycle_tests fixtures ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-exp-bilinear-lifecycle/validation/original-01/fixtures.txt)
  add_executable(dsp_ratio_skew_lifecycle_tests tests/dsp_ratio_skew_lifecycle_tests.cpp)
  target_link_libraries(dsp_ratio_skew_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_ratio_skew_lifecycle_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(dsp_ratio_skew_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME dsp_ratio_skew_lifecycle COMMAND dsp_ratio_skew_lifecycle_tests lifecycle)
  add_test(NAME dsp_ratio_skew_constructor_virtual_fixtures COMMAND dsp_ratio_skew_lifecycle_tests fixtures ${CMAKE_CURRENT_SOURCE_DIR}/candidates/dsp-ratio-skew-lifecycle/validation/original-01/fixtures.txt)
  add_executable(noaa_programmer_transport_tests tests/noaa_programmer_transport_tests.cpp)
  target_link_libraries(noaa_programmer_transport_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_transport_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  target_link_options(noaa_programmer_transport_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME noaa_programmer_transport_tests COMMAND noaa_programmer_transport_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-transport/stdin.txt)
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/noaa-router-route-script")
  add_executable(noaa_router_initialization_tests tests/noaa_router_initialization_tests.cpp)
  target_link_libraries(noaa_router_initialization_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_initialization_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_initialization_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv -Wl,--wrap=_ZN8Presonus4NOAA11TCardRouter15doRouteCommandsEPNS0_9DiceRouteEih)
  add_test(NAME noaa_router_initialization COMMAND noaa_router_initialization_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-remaining/initialization-stdin.txt ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-remaining/print-stdin.txt)
  add_executable(noaa_router_script_tests tests/noaa_router_script_tests.cpp)
  target_link_libraries(noaa_router_script_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_script_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_script_tests PRIVATE -Wl,--wrap=_ZN8Presonus4NOAA13SysexReceiver7waitAckEx -Wl,--wrap=_ZN4Core11DebugPrintfEPKcz -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv -Wl,--wrap=_ZN8Presonus4NOAA11TCardRouter14doRouteCommandEhhhhh -Wl,--wrap=getenv -Wl,--wrap=fopen -Wl,--wrap=fclose)
  add_test(NAME noaa_router_script COMMAND noaa_router_script_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-remaining/script-stdin.txt ${PRESONUS_REPOSITORY_ROOT}/temp/test-work/noaa-router-route-script)
  add_executable(noaa_router_lifecycle_tests tests/noaa_router_lifecycle_tests.cpp tests/noaa_router_lifecycle_core_scope.cpp)
  target_link_libraries(noaa_router_lifecycle_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_router_lifecycle_tests PRIVATE -UNDEBUG -frtti -fno-lto -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(noaa_router_lifecycle_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_Znam -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_destroy -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_ -Wl,--wrap=_ZN8Presonus4NOAA8TCardSPI16registerReceiverEPNS0_14ISysexReceiverE -Wl,--wrap=_ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE)
  add_test(NAME noaa_router_lifecycle COMMAND noaa_router_lifecycle_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-router-remaining/lifecycle-stdin.txt)
  add_executable(mixer_decay_time_formatter_tests tests/mixer_decay_time_formatter_tests.cpp)
  target_link_libraries(mixer_decay_time_formatter_tests PRIVATE presonus_uc)
  target_compile_options(mixer_decay_time_formatter_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(mixer_decay_time_formatter_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME mixer_decay_time_formatter_native COMMAND mixer_decay_time_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/mixer-decay-time-formatter/validation/native-01/fixtures.txt)
  add_executable(mixer_feedback_formatter_tests tests/mixer_feedback_formatter_tests.cpp)
  target_link_libraries(mixer_feedback_formatter_tests PRIVATE presonus_uc)
  target_compile_options(mixer_feedback_formatter_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(mixer_feedback_formatter_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME mixer_feedback_formatter_native COMMAND mixer_feedback_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/mixer-feedback-formatter/validation/native-02/fixtures.txt)
  add_executable(noaa_programmer_safe_host_serial_tests tests/noaa_programmer_safe_host_serial_tests.cpp)
  target_link_libraries(noaa_programmer_safe_host_serial_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_safe_host_serial_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  add_test(NAME noaa_programmer_safe_host_serial_tests COMMAND noaa_programmer_safe_host_serial_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-safe-host/serial-stdin.txt)
  add_executable(noaa_programmer_safe_host_information_tests tests/noaa_programmer_safe_host_information_tests.cpp)
  target_link_libraries(noaa_programmer_safe_host_information_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_safe_host_information_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  add_test(NAME noaa_programmer_safe_host_information_tests COMMAND noaa_programmer_safe_host_information_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-safe-host/information-stdin.txt)
  add_executable(noaa_programmer_safe_host_protocol_tests tests/noaa_programmer_safe_host_protocol_tests.cpp)
  target_link_libraries(noaa_programmer_safe_host_protocol_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_safe_host_protocol_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  add_test(NAME noaa_programmer_safe_host_protocol_tests COMMAND noaa_programmer_safe_host_protocol_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-safe-host/protocol-stdin.txt)
  add_executable(noaa_programmer_safe_host_receive_tests tests/noaa_programmer_safe_host_receive_tests.cpp)
  target_link_libraries(noaa_programmer_safe_host_receive_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_safe_host_receive_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  add_test(NAME noaa_programmer_safe_host_receive_tests COMMAND noaa_programmer_safe_host_receive_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-safe-host/wait-response-stdin.txt)
  add_executable(noaa_programmer_safe_host_alias_tests tests/noaa_programmer_safe_host_alias_tests.cpp)
  target_link_libraries(noaa_programmer_safe_host_alias_tests PRIVATE presonus::rm_components)
  target_compile_options(noaa_programmer_safe_host_alias_tests PRIVATE -UNDEBUG -frtti -fno-lto)
  add_test(NAME noaa_programmer_safe_host_alias_tests COMMAND noaa_programmer_safe_host_alias_tests ${CMAKE_CURRENT_SOURCE_DIR}/validation/noaa-programmer-safe-host/alias-stdin.txt)
  add_executable(mixer_scaled_time_formatter_tests tests/mixer_scaled_time_formatter_tests.cpp)
  target_link_libraries(mixer_scaled_time_formatter_tests PRIVATE presonus_uc)
  target_compile_options(mixer_scaled_time_formatter_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(mixer_scaled_time_formatter_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME mixer_scaled_time_formatter_native COMMAND mixer_scaled_time_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/mixer-scaled-time-formatter/validation/native-01/fixtures.txt)
  add_executable(mixer_filter_q_formatter_tests tests/mixer_filter_q_formatter_tests.cpp)
  target_link_libraries(mixer_filter_q_formatter_tests PRIVATE presonus_uc)
  target_compile_options(mixer_filter_q_formatter_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(mixer_filter_q_formatter_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME mixer_filter_q_formatter_native COMMAND mixer_filter_q_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/mixer-filter-q-formatter/validation/native-01/fixtures.txt)
  add_executable(mixer_geq_gain_formatter_tests tests/mixer_geq_gain_formatter_tests.cpp)
  target_link_libraries(mixer_geq_gain_formatter_tests PRIVATE presonus_uc)
  target_compile_options(mixer_geq_gain_formatter_tests PRIVATE -UNDEBUG -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin -fno-devirtualize -fno-devirtualize-speculatively)
  target_link_options(mixer_geq_gain_formatter_tests PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME mixer_geq_gain_formatter_native COMMAND mixer_geq_gain_formatter_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/mixer-geq-gain-formatter/validation/native-01/fixtures.txt)
  add_executable(uc_activity_singleton_provider tests/activity_singleton_tests.cpp)
  target_link_libraries(uc_activity_singleton_provider PRIVATE presonus::uc)
  target_compile_options(uc_activity_singleton_provider PRIVATE -UNDEBUG)
  target_link_options(uc_activity_singleton_provider PRIVATE -Wl,--wrap=_Znam -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_destroy -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock)
  add_test(NAME uc_activity_singleton_provider COMMAND uc_activity_singleton_provider)
  add_executable(uc_basic_connection_lifecycle tests/basic_connection_lifecycle_tests.cpp)
  target_link_libraries(uc_basic_connection_lifecycle PRIVATE presonus::uc)
  target_compile_options(uc_basic_connection_lifecycle PRIVATE -UNDEBUG)
  target_link_options(uc_basic_connection_lifecycle PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm -Wl,--wrap=pthread_mutex_init -Wl,--wrap=pthread_mutex_destroy -Wl,--wrap=pthread_mutex_lock -Wl,--wrap=pthread_mutex_unlock)
  add_test(NAME uc_basic_connection_lifecycle COMMAND uc_basic_connection_lifecycle functional)
  # Coordinator-owned CMake insertions; CPP bodies go only in COMMON OBJECT partition.
  add_executable(uc_owned_data_factory tests/owned_data_factory_tests.cpp)
  target_link_libraries(uc_owned_data_factory PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_owned_data_factory PRIVATE -UNDEBUG)
  add_test(NAME uc_owned_data_factory COMMAND uc_owned_data_factory )
  add_executable(uc_owned_data_writer_differential tests/owned_data_writer_differential.cpp)
  target_link_libraries(uc_owned_data_writer_differential PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_owned_data_writer_differential PRIVATE -UNDEBUG)
  add_test(NAME uc_owned_data_writer_differential COMMAND uc_owned_data_writer_differential ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-10-29/uc-event-factory-owned-data/original-write02/writer-vectors.bin)
  add_executable(uc_factory_bootstrap_production tests/factory_bootstrap_production_tests.cpp)
  target_link_libraries(uc_factory_bootstrap_production PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_factory_bootstrap_production PRIVATE -UNDEBUG)
  target_link_options(uc_factory_bootstrap_production PRIVATE -Wl,--wrap=_Znam -Wl,--wrap=_Znwm -Wl,--wrap=_ZdaPv -Wl,--wrap=_ZdaPvm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_factory_bootstrap_production COMMAND uc_factory_bootstrap_production )
  add_executable(uc_network_callbacks_discovery_production tests/network_manager_callbacks_report_multicast/discovery/native_callbacks.cpp)
  target_link_libraries(uc_network_callbacks_discovery_production PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_network_callbacks_discovery_production PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(uc_network_callbacks_discovery_production PRIVATE -Wl,--wrap=vsnprintf -Wl,--wrap=__vsnprintf_chk -Wl,--wrap=_ZNK8Presonus2UC15ServerRegistrar4findEPvb -Wl,--wrap=_ZN8Presonus2UC11LocalServer4castEPNS0_6ServerE -Wl,--wrap=_ZN8Presonus2UC12RemoteServer4castEPNS0_6ServerE -Wl,--wrap=_ZN8Presonus2UC15ServerRegistrar16serverRegisteredEPNS0_11LocalServerE -Wl,--wrap=_ZN8Presonus2UC15ServerRegistrar19notifyServerChangedEPNS0_6ServerE)
  add_test(NAME uc_network_callbacks_discovery_production COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/candidates/uc-factory-callbacks-hierarchy-native-profile/tests/replay_production.py --suite discovery --executable $<TARGET_FILE:uc_network_callbacks_discovery_production> --input ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-10-29/uc-network-manager-callbacks/original-01/validation.json --input-sha256 42a93b6fddbdaaa91341f6f184bc817d78e9f7ba4bb4b4771d1a61c83161d816 --work ${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/uc_network_callbacks_discovery_production)
  add_executable(uc_network_callbacks_multicast_production tests/network_manager_callbacks_report_multicast/multicast/native_tests.cpp)
  target_link_libraries(uc_network_callbacks_multicast_production PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_network_callbacks_multicast_production PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(uc_network_callbacks_multicast_production PRIVATE -Wl,--wrap=_ZNK8Presonus2UC15ServerRegistrar4findEib -Wl,--wrap=_ZNK8Presonus2UC15ServerRegistrar4findEPKcti -Wl,--wrap=_ZN8Presonus2UC14NetworkManager9sendEventERKNS0_5EventEi)
  add_test(NAME uc_network_callbacks_multicast_production COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/candidates/uc-factory-callbacks-hierarchy-native-profile/tests/replay_production.py --suite multicast --executable $<TARGET_FILE:uc_network_callbacks_multicast_production> --input ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-10-29/uc-network-manager-callbacks-report-multicast/multicast-native-01/fixtures.txt --input-sha256 c2e128b28dfd9471d84617c4ce691b8f15335a5bdf4d039f1408175e823357a7 --work ${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/uc_network_callbacks_multicast_production)
  add_executable(uc_network_callbacks_report_production tests/network_manager_callbacks_report_multicast/report_native_tests.cpp)
  target_link_libraries(uc_network_callbacks_report_production PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_network_callbacks_report_production PRIVATE -frtti -fno-lto -UNDEBUG)
  target_link_options(uc_network_callbacks_report_production PRIVATE -Wl,--wrap=vsnprintf -Wl,--wrap=__vsnprintf_chk)
  add_test(NAME uc_network_callbacks_report_production COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/candidates/uc-factory-callbacks-hierarchy-native-profile/tests/replay_production.py --suite report --executable $<TARGET_FILE:uc_network_callbacks_report_production> --input ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/recovery/2026-10-29/uc-network-manager-callbacks-report-multicast/report-native-01/fixtures.txt --input-sha256 a997b19911303a788f4884027323a85d8695f8015629e343699c4b27273b90c5 --work ${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/uc_network_callbacks_report_production)
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/candidates/graph-live-trial-03-pcm/fixtures.txt" graph_trial03_pcm_fixture_sha)
  if(NOT graph_trial03_pcm_fixture_sha STREQUAL "601ed290b333c07038a868adb86282cf4d0d572c0128fce32eb281e32c916a5c")
    message(FATAL_ERROR "graph_trial03_pcm native fixture hash mismatch")
  endif()
  add_executable(graph_trial03_pcm_tests tests/graph_trial03_pcm_tests.cpp)
  target_link_libraries(graph_trial03_pcm_tests PRIVATE stdc++ presonus::cs18_components)
  target_compile_options(graph_trial03_pcm_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME graph_trial03_pcm_replay COMMAND graph_trial03_pcm_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/graph-live-trial-03-pcm/fixtures.txt)
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/candidates/graph-live-trial-03-daw/fixtures.txt" graph_trial03_daw_fixture_sha)
  if(NOT graph_trial03_daw_fixture_sha STREQUAL "37614196d6bdba5b77f721b98d41d049f7f8f8900411eb7fc0615836f4a1ee3b")
    message(FATAL_ERROR "graph_trial03_daw native fixture hash mismatch")
  endif()
  add_executable(graph_trial03_daw_tests tests/graph_trial03_daw_tests.cpp)
  target_link_libraries(graph_trial03_daw_tests PRIVATE stdc++ presonus::cs18_components)
  target_compile_options(graph_trial03_daw_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME graph_trial03_daw_replay COMMAND graph_trial03_daw_tests ${CMAKE_CURRENT_SOURCE_DIR}/candidates/graph-live-trial-03-daw/fixtures.txt)
  add_executable(native_book_tests tests/native_book_tests.cpp)
  target_link_libraries(native_book_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(native_book_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME native_book_differential COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/recovery/native_fixture_replay.py --kind book --executable $<TARGET_FILE:native_book_tests> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/candidates/native-live-trial-02-book/fixture.json --sha256 1eb6b812cab78e9d820318285810906e3f776643a1c0569d7f3e4ddc4fec5818)
  add_executable(native_beast_tests tests/native_beast_tests.cpp)
  target_link_libraries(native_beast_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(native_beast_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME native_beast_differential COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/recovery/native_fixture_replay.py --kind beast --executable $<TARGET_FILE:native_beast_tests> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/candidates/native-live-trial-02-beast/fixture.json --sha256 a0a492aca8ea5f477c7e0507860102fc8bb712d695a69b529fc0e9bf1110cd38)
  add_executable(panel_registrar_access_tests tests/panel_registrar_access_tests.cpp)
  target_link_libraries(panel_registrar_access_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(panel_registrar_access_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME panel_registrar_access COMMAND panel_registrar_access_tests ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/panel_registrar_access.txt)
  add_executable(uc_outgoing_socket_identity_tests tests/outgoing_socket_identity_tests.cpp)
  target_link_libraries(uc_outgoing_socket_identity_tests PRIVATE stdc++ presonus::uc)
  target_compile_options(uc_outgoing_socket_identity_tests PRIVATE -frtti -fno-lto -UNDEBUG)
  add_test(NAME uc_outgoing_socket_identity_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_outgoing_socket_identity_tests> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-outgoing-socket-identity/fixtures.stdin --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-outgoing-socket-identity/expected.txt --cases 180)
  if(TARGET uc_connection_receive_ccl_tests)
    target_include_directories(uc_connection_receive_ccl_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_connection_receive_ccl_tests PRIVATE -frtti -fno-lto)
  endif()
  if(TARGET uc_ccl_provider_tests)
    target_include_directories(uc_ccl_provider_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_ccl_provider_tests PRIVATE -frtti -fno-lto)
  endif()
  if(TARGET uc_connection_tests)
    target_include_directories(uc_connection_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_connection_tests PRIVATE -frtti -fno-lto)
  endif()
  if(TARGET uc_external_connection_tests)
    target_include_directories(uc_external_connection_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_external_connection_tests PRIVATE -frtti -fno-lto)
  endif()
  if(TARGET uc_network_services_loopback)
    target_include_directories(uc_network_services_loopback PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_network_services_loopback PRIVATE -frtti -fno-lto)
  endif()
  if(TARGET uc_network_handler_queries_bridge)
    target_include_directories(uc_network_handler_queries_bridge PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    target_compile_options(uc_network_handler_queries_bridge PRIVATE -frtti -fno-lto)
  endif()
  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)
  target_compile_features(uc_symbol_catalog_check PRIVATE cxx_std_17)
endif()
add_executable(uc_loopback examples/loopback.cpp)
find_package(Threads REQUIRED)
target_link_libraries(uc_loopback PRIVATE presonus::uc Threads::Threads)
install(TARGETS presonus_uc presonus_cs18_components presonus_rm_components EXPORT presonus_uc_targets ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
set(PRESONUS_UC_PUBLIC_HEADERS
  presonus/mixer/NetworkSetupComponent.hpp
  presonus/surface/WifiSetupComponent.hpp
  presonus/surface/PresetsPageComponent.hpp
  presonus/surface/GroupsEditPageComponent.hpp
  presonus/surface/CapturePageComponent.hpp
  presonus/panel/GeqUIComponent.hpp
  presonus/panel/PresetComponent.hpp
  presonus/mixer/NetworkSelectComponent.hpp
  presonus/mixer/InputComponent.hpp
  presonus/mixer/MasterSectionComponent.hpp
  presonus/PageComponent.hpp
  presonus/surface/DawFxPageComponent.hpp
  presonus/surface/GroupsPageComponent.hpp
  presonus/StormMixSceneComponent.hpp
  presonus/mixer/FXComponent.hpp
  presonus/mixer/AVBCascadeManager.hpp
  presonus/MeterManagerBase.hpp
  presonus/LinkControl.hpp
  presonus/mixer/PermissionsComponent.hpp
  presonus/PanControl.hpp
  presonus/uc/DataChannel.hpp
  presonus/MackieControlModel.hpp
  presonus/MappingTable.hpp
  presonus/LinkableComponent.hpp
  presonus/dsp/Controller.hpp
  presonus/avb/AvbComponent.hpp
  presonus/panel/MixerLCD.hpp
  presonus/MuteGroupBase.hpp
  presonus/surface/MidiMixerHandler.hpp
  presonus/panel/PanelComponent.hpp
  presonus/pcm4104/Pcm4104Spi.hpp
  presonus/DAWTimeInfo.hpp
  presonus/panel/Book.hpp
  presonus/panel/BeastPanelRegistrar.hpp
  presonus/panel/uart_led_state_token.hpp
  presonus/panel/lcd_display_control.hpp
  presonus/panel/temperature_control.hpp
  presonus/mixer_update/FirmwareUpdateComponent.hpp
  presonus/surface/mapping_input_routes.hpp
  presonus/surface_update/CallbackText.hpp
  presonus/surface_update/FirmwareUpdateComponent.hpp
  presonus/panel/phantom_power_control.hpp
  presonus/panel/uart_message_sender.hpp
  presonus/surface/DisplayManager.hpp
  presonus/surface/IDisplayPort.hpp
  presonus/surface/LCDPort.hpp
  presonus/surface/ScribbleStripMgr.hpp
  presonus/surface_panel/IDisplay.hpp
  presonus/surface_panel/TinyFontMetrics.hpp
  presonus/uux/FirmwareUpdaterPaths.hpp
  presonus/surface/sl_mixer_encoder.hpp
  presonus/application/LPCProgrammerGeometry.hpp
  presonus/panel/motorized_fader_control.hpp
  presonus/panel/encoder_control.hpp
  presonus/panel/key_input_provider.hpp
  presonus/panel/blink_led_control.hpp
  presonus/panel/input_gpio_control.hpp
  presonus/uc/source_default_factory.hpp
  presonus/uc/report.hpp
  presonus/uc/owned_data_factory_codec.hpp
  presonus/uc/outgoing_connection.hpp
  presonus/uc/basic_connection_runtime.hpp
  presonus/uc/activity_singleton.hpp
  presonus/mixer/GeqGainFormatter.hpp
  presonus/mixer/FilterQFormatter.hpp
  presonus/mixer/ScaledTimeFormatter.hpp
  presonus/mixer/FeedbackFormatter.hpp
  presonus/mixer/DecayTimeFormatter.hpp
  presonus/noaa/diagnostics.hpp
  presonus/noaa/programmer.hpp
  presonus/uc/midi_connection.hpp
  presonus/uc/connection_interfaces.hpp
  presonus/mixer_dsp/GateParameterList.hpp
  presonus/mixer_dsp/GateSourceProviders.hpp
  presonus/mixer_dsp/GEQParameterList.hpp
  presonus/mixer_dsp/GEQSourceProviders.hpp
  presonus/uc/OnOff.hpp
  presonus/mixer_dsp/CompressorParameterList.hpp
  presonus/mixer_dsp/CompressorSourceProviders.hpp
  presonus/noaa/ucnet_handler.hpp
  presonus/noaa/ucnet_handler_state.hpp
  presonus/uc/client_typed_origins.hpp
  presonus/noaa/card_handler.hpp
  presonus/noaa/card_handler_state.hpp
  presonus/uc/client_event_values.hpp
  presonus/mixer_dsp/FaderInterpolator.hpp
  presonus/dsp/audio_hal.hpp
  presonus/uc/client_implementation.hpp
  presonus/mixer_dsp/FilterParameterLists.hpp
  presonus/uc/network_activity_manager.hpp
  presonus/mixer_dsp/EQControl.hpp
  presonus/uc/message_queue.hpp
  presonus/mixer_dsp/Eq8LimiterParameterLists.hpp
  presonus/uc/mutable_message_event.hpp
  presonus/noaa/status_property.hpp
  presonus/device_dfu.hpp
  presonus/noaa/card.hpp
  presonus/mixer_dsp/EqParameterLists.hpp
  presonus/mixer_dsp/EqSourceProviders.hpp
  presonus/noaa/setup_property.hpp
  presonus/uc/firmware_update_listener.hpp
  presonus/uc/network_client_factory.hpp
  presonus/mixer/setup_property_applications.hpp
  presonus/uc/message_attributes.hpp
  presonus/noaa/router_slot_tables.hpp
  presonus/mixer_dsp/ParamDescriptorList.hpp
  presonus/mixer_dsp/GateMeterInterpolators.hpp
  presonus/mixer_dsp/FaderCurveInterpolator.hpp
  presonus/noaa/router.hpp
  presonus/dice/manager_lifetime.hpp
  presonus/uc/discovery_handler.hpp
  presonus/uc/discovery_ownership.hpp
  presonus/uc/multicast_connection.hpp
  presonus/dice/sysex_receiver_interface.hpp
  presonus/dice/subsystem_runtime.hpp
  presonus/mixer_dsp/AdditionalFormatters.hpp
  presonus/utilities/string_utils.hpp
  presonus/mixer_dsp/Formatters.hpp
  presonus/uc/udp_discovery.hpp
  presonus/uc/adapter_handler.hpp
  presonus/dice/manager_programmer_services.hpp
  presonus/mixer_dsp/Interpolators.hpp
  presonus/embedded_efm/efm_control_dispatch.hpp
  presonus/uc/file_transfer.hpp
  presonus/mcu/panel_protocol.hpp
  presonus/mcu/update_loop.hpp
  presonus/embedded_efm/efm_parameter_fields.hpp
  presonus/embedded_efm/efm_packed_parameters.hpp
  presonus/embedded_efm/efm_packet_checks.hpp
  presonus/embedded_efm/efm_version_packet.hpp
  presonus/uc/protocol.hpp
  presonus/uc/network.hpp
  presonus/uc/abi32.hpp
  presonus/uc/DicePacketQueue.hpp
  presonus/uc/events.hpp
  presonus/uc/transport_events.hpp
  presonus/uc/event_factory.hpp
  presonus/uc/discovery_events.hpp
  presonus/uc/primitive_dispatch.hpp
  presonus/uc/typed_factory_codec.hpp
  presonus/uc/meter_events.hpp
  presonus/uc/parameter_events.hpp
  presonus/uc/no_member_events.hpp
  presonus/uc/file_control_events.hpp
  presonus/uc/misc_events.hpp
  presonus/uc/file_data_events.hpp
  presonus/uc/connection.hpp
  presonus/uc/external_connection.hpp
  presonus/uc/event_queue.hpp
  presonus/uc/basic_connection.hpp
  presonus/uc/socket_channel.hpp
  presonus/dice/sysex.hpp
  presonus/dice/codec.hpp
  presonus/dice/manager.hpp
  presonus/dice/programmer.hpp
  presonus/avb/protocol.hpp
  presonus/avb/receive_services.hpp
  presonus/avb/streams.hpp
  presonus/core_uc/buffer.hpp
  presonus/mixer_dsp/Dsp.hpp
  presonus/mixer_dsp/FilterControllers.hpp
  presonus/mixer_state/MixerState.hpp
  presonus/surface_panel/ControlHelpers.hpp
  presonus/panel/registrar_group_registry.hpp
  presonus/surface_panel/DbTable.hpp
  presonus/surface_panel/MeterControl.hpp
  presonus/surface_panel/BitmapDrawing.hpp
  presonus/surface_panel/LEDState.hpp
  presonus/surface_panel/InputPin.hpp
  presonus/surface_panel/OutputPin.hpp
  presonus/embedded_dice/mix.hpp
)
if(PRESONUS_ENABLE_UPSTREAM_CORE)
  list(APPEND PRESONUS_UC_PUBLIC_HEADERS
    presonus/uc/file_transfer_manager.hpp
    presonus/uc/network_manager_services.hpp
    presonus/dsp/biquad_calc.hpp
    presonus/uc/server_registrar.hpp
    presonus/dice/programmer_services.hpp
    presonus/uc/connection_handler.hpp
    presonus/dice/programmer_device_services.hpp
    presonus/uc/server.hpp
    presonus/dice/manager_services.hpp
    presonus/dsp/single_pole.hpp
    presonus/panel/pot_fader_control.hpp
    presonus/panel/switch_control.hpp
    presonus/noaa/spi_service.hpp
    presonus/uc/file_server_service.hpp
    presonus/panel/control.hpp
    presonus/uc/file_services.hpp
    presonus/noaa/spi_packets.hpp
    presonus/panel/param_edit_handler.hpp
    presonus/panel/uart_message_handler.hpp
    presonus/application/ResourceLibrary.hpp
    presonus/delay_timer.hpp
    presonus/application/SurfaceApplication.hpp
    presonus/panel/simulate_comm.hpp
    presonus/application/FileCleanup.hpp
    presonus/panel/protocol_comm.hpp
    presonus/panel/uart_message.hpp
    presonus/panel/uart_comm.hpp
    presonus/panel/alert_manager.hpp
    presonus/application/SimpleReader.hpp
    presonus/application/SimpleReaderEnvironment.hpp
    presonus/dice/packet_logging.hpp
    presonus/dice/uart_packet_log.hpp
    presonus/noaa/sysex_packet.hpp
    presonus/application/ApplicationManagers.hpp
    presonus/uc/data_codecs.hpp
    presonus/dice/uart_assembly.hpp
    presonus/surface_panel/DigitalPotControl.hpp
    presonus/uc/event_dispatcher.hpp
    presonus/surface_panel/ControlGroup.hpp
    presonus/dice/response_wait_detail.hpp
    presonus/dice/packet_services.hpp
    presonus/dice/response_services.hpp
    presonus/noaa/sysex_receiver.hpp
    presonus/uc/ccl_bindings.hpp presonus/uc/connection_receive.hpp)
endif()
foreach(header IN LISTS PRESONUS_UC_PUBLIC_HEADERS)
  get_filename_component(header_directory "${header}" DIRECTORY)
  install(FILES "include/${header}" DESTINATION "include/${header_directory}")
endforeach()
install(FILES "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}/libpresonus_private_glibc29.a"
  DESTINATION lib)
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/vendor/glibc-2.9/"
  DESTINATION share/presonus_uc/sources/glibc-2.9)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_private_glibc29.py"
              "${CMAKE_CURRENT_SOURCE_DIR}/cmake/PrivateGlibc29.cmake"
  DESTINATION share/presonus_uc/sources/glibc-2.9/build-support)
install(FILES "${PRESONUS_PRIVATE_GLIBC29_OUTPUT}/provider-validation.json"
  DESTINATION share/presonus_uc/sources/glibc-2.9/build-receipts)
install(EXPORT presonus_uc_targets NAMESPACE presonus:: DESTINATION lib/cmake/presonus_uc)
include(CMakePackageConfigHelpers)
if(PRESONUS_ENABLE_UPSTREAM_CORE)
  install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/upstream-core/sdk/"
          DESTINATION "." USE_SOURCE_PERMISSIONS)
endif()
configure_package_config_file(cmake/presonus_ucConfig.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/presonus_ucConfig.cmake"
  INSTALL_DESTINATION lib/cmake/presonus_uc)
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/presonus_ucConfigVersion.cmake"
  VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/presonus_ucConfig.cmake"
              "${CMAKE_CURRENT_BINARY_DIR}/presonus_ucConfigVersion.cmake"
        DESTINATION lib/cmake/presonus_uc)

include(cmake/PanelHALControls.cmake)

include(cmake/PanelSLMixer.cmake)
include(cmake/LPCProgrammerGeometry.cmake)

include(cmake/UUXHostProcess.cmake)

include(cmake/SurfaceDisplay.cmake)

include(cmake/LPCProgrammerImageGeometry.cmake)

if(BUILD_TESTING)
  include(cmake/LPCProgrammerInput.cmake)
endif()

include(cmake/UARTMessageSender.cmake)

include(cmake/UARTLedMeterSender.cmake)

if(BUILD_TESTING)
  include(cmake/LPCProgrammerCommandInfo.cmake)
endif()

include(cmake/PanelPhantomPower.cmake)

if(BUILD_TESTING)
  include(cmake/LPCProgrammerTransport.cmake)
endif()

if(BUILD_TESTING)
  include(cmake/LPCProgrammerHandshake.cmake)
endif()

include(cmake/SurfaceMapping.cmake)

include(cmake/FirmwareUpdateCallbacks.cmake)

include(cmake/UARTSenderExtensions.cmake)

include(cmake/SurfaceFaderControls.cmake)

include(cmake/PanelLCDDisplayControl.cmake)

include(cmake/PanelTemperature.cmake)

include(cmake/GraphTrial04.cmake)

include(cmake/GraphTrial05.cmake)

include(cmake/GraphTrial06.cmake)
