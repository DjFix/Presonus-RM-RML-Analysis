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
# Permissions now derives from the actual CCL-backed ServerComponent provider.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/PermissionsComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
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
set_property(SOURCE src/mixer_dsp/FilterControllers.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20)
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
# This historical test-enabled setting affects a production translation unit.
# Keep it outside the test-only registration boundary.
if(BUILD_TESTING)
  set_source_files_properties(src/embedded_efm/efm_control_dispatch.cpp PROPERTIES
    INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/include/presonus/embedded_efm")
endif()
include(cmake/tests/RecoveryTests.cmake)
add_executable(uc_loopback examples/loopback.cpp)
find_package(Threads REQUIRED)
target_link_libraries(uc_loopback PRIVATE presonus::uc Threads::Threads)
install(TARGETS presonus_uc presonus_cs18_components presonus_rm_components EXPORT presonus_uc_targets ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
set(PRESONUS_UC_PUBLIC_HEADERS
  presonus/IDAWDialogHandler.hpp
  presonus/panel/GPIOControlGroup.hpp
  presonus/uc/ClientComponent.hpp
  presonus/mixer/DecayTimeFormatterT6.hpp
  presonus/mixer/DecayTimeFormatterT7.hpp
  presonus/mixer/DecayTimeFormatterT8.hpp
  presonus/mixer/DecayTimeFormatterT9.hpp
  presonus/mixer/EarlyRefFormatterT2.hpp
  presonus/mixer/PreDelayFormatterT2.hpp
  presonus/panel/LCDComponent.hpp
  presonus/MeterMaid.hpp
  presonus/mixer/DecayTimeFormatterT1.hpp
  presonus/mixer/DecayTimeFormatterT2.hpp
  presonus/mixer/DecayTimeFormatterT3.hpp
  presonus/mixer/DecayTimeFormatterT4.hpp
  presonus/mixer/DecayTimeFormatterT5.hpp
  presonus/mixer/DelayTimeFormatter.hpp
  presonus/mixer/EarlyRefFormatterT3.hpp
  presonus/mixer/EarlyRefFormatterT4.hpp
  presonus/mixer/EarlyRefFormatterT5.hpp
  presonus/mixer/EarlyRefFormatterT6.hpp
  presonus/mixer/PreDelayFormatterT3.hpp
  presonus/mixer/PreDelayFormatterT4.hpp
  presonus/mixer/PreDelayFormatterT5.hpp
  presonus/mixer/StereoSpreadFormatter.hpp
  presonus/panel/AlertPage.hpp
  presonus/MeterBallistics.hpp
  presonus/dsp/OMAPTargetHandler.hpp
  presonus/mixer/ChDelayFormatter.hpp
  presonus/mixer/ChGainFormatter.hpp
  presonus/mixer/ChHPFFormatter.hpp
  presonus/mixer/EarlyRefFormatter.hpp
  presonus/mixer/FilterFreqFormatter.hpp
  presonus/mixer/FilterGainFormatter.hpp
  presonus/mixer/GeqFreqFormatter.hpp
  presonus/mixer/NumberPrepender.hpp
  presonus/mixer/PreDelayFormatter.hpp
  presonus/mixer/SubDelayFormatter.hpp
  presonus/panel/FillElement.hpp
  presonus/panel/StaticElement.hpp
  presonus/panel/FieldElement.hpp
  presonus/panel/OffscreenElement.hpp
  presonus/panel/LCDManager.hpp
  presonus/panel/Page.hpp
  presonus/panel/TextEntryElement.hpp
  presonus/dsp/DSPManager.hpp
  presonus/utilities/dfu_diagnostic.hpp
  presonus/utilities/table_elements.hpp
  presonus/ColorButton.hpp
  presonus/IconManager.hpp
  presonus/surface/SoloPageComponent.hpp
  presonus/DefaultMeterInterpolator.hpp
  presonus/LPFControl.hpp
  presonus/surface/UCMidiInputAdapter.hpp
  presonus/surface/UCMidiOutputAdapter.hpp
  presonus/panel/GambitPanelComponent.hpp
  presonus/panel/WolverinePanelComponent.hpp
  presonus/mixer/AudioComponent.hpp
  presonus/mixer/BeastMixerComponent.hpp
  presonus/mixer/StormMixerComponent.hpp
  presonus/mixer/MonoMainComponent.hpp
  presonus/mixer/TapeInputComponent.hpp
  presonus/mixer/GroupChangeObserver.hpp
  presonus/surface/PageHeaderComponent.hpp
  presonus/surface/MonitorPageComponent.hpp
  presonus/surface/GatePageComponent.hpp
  presonus/surface/CascadeHandler.hpp
  presonus/panel/SystemAboutPage.hpp
  presonus/panel/RogueFrontPanelComponent.hpp
  presonus/panel/JoinNetworkPage.hpp
  presonus/panel/FXMainPage.hpp
  presonus/panel/FATLEDOverridePage.hpp
  presonus/panel/BeastFrontPanelComponent.hpp
  presonus/mixer/GEQComponent.hpp
  presonus/mixer/MonoBusComponent.hpp
  presonus/mixer/EQComponent.hpp
  presonus/mixer/GateComponent.hpp
  presonus/mixer/HPFilterComponent.hpp
  presonus/mixer/LPFilterComponent.hpp
  presonus/mixer/LimiterComponent.hpp
  presonus/mixer/AutoFilterGroupManager.hpp
  presonus/surface/TBRoutingPageComponent.hpp
  presonus/surface/FxPresetsPageComponent.hpp
  presonus/surface/FXHomePageComponent.hpp
  presonus/surface/FXEditPageComponent.hpp
  presonus/panel/StormPanelRegistrar.hpp
  presonus/panel/RoguePanelRegistrar.hpp
  presonus/panel/GambitPanelRegistrar.hpp
  presonus/mixer/TalkbackInputComponent.hpp
  presonus/mixer/MicLineComponent.hpp
  presonus/mixer/DelayComponent.hpp
  presonus/mixer/CascadeLinkHandler.hpp
  presonus/panel/ParamEnablementHandler.hpp
  presonus/BackgroundPainter.hpp
  presonus/mixer/ChannelPresetFilter.hpp
  presonus/mixer/FilterGroupComponent.hpp
  presonus/mixer/FxPresetFilter.hpp
  presonus/mixer/GEQPresetFilter.hpp
  presonus/mixer/ChannelParamTagFilter.hpp
  presonus/mixer/SmaartStoreFilter.hpp
  presonus/mixer/ChannelParameterController.hpp
  presonus/mixer/StorageFilterForwarding.hpp
  presonus/AltMemoryFilter.hpp
  presonus/panel/PanelTask.hpp
  presonus/panel/LEDNotifyTask.hpp
  presonus/surface/RadioToggleButton.hpp
  presonus/dsp/ControllerInfo.hpp
  presonus/panel/Element.hpp
  presonus/MappableMixer.hpp
  presonus/link/Messenger.hpp
  presonus/panel/SharedMemoryComm.hpp
  presonus/MixerClientComponentBase.hpp
  presonus/SLChannel.hpp
  presonus/IMainScreenPageController.hpp
  presonus/FocusRestorer.hpp
  presonus/mixer/GambitMixerComponent.hpp
  presonus/mixer/ReverbComponent.hpp
  presonus/mixer/ControlMapping.hpp
  presonus/surface/ControlName.hpp
  presonus/mixer/GambitRMLApplication.hpp
  presonus/mixer/WolverineRMLApplication.hpp
  presonus/panel/WolverinePanelRegistrar.hpp
  presonus/panel/FXPage.hpp
  presonus/panel/GEQPage.hpp
  presonus/MappablePageComponent.hpp
  presonus/ModalPageComponent.hpp
  presonus/surface/PageParam.hpp
  presonus/color/IColorConverter.hpp
  presonus/color/MixerColorConverter.hpp
  presonus/surface_panel/ControlHelpers.hpp
  presonus/VUMeterControl.hpp
  presonus/MeterScaleControl.hpp
  presonus/surface/MuteGroupsComponent.hpp
  presonus/surface/MixerPageComponent.hpp
  presonus/surface/SubAssignPageComponent.hpp
  presonus/panel/ChannelPresetComponent.hpp
  presonus/panel/GeqPresetComponent.hpp
  presonus/panel/ScenesComponent.hpp
  presonus/uc/ServerComponent.hpp
  presonus/avb/ComponentResource.hpp
  presonus/mixer/AVBRemoteMixerHandler.hpp
  presonus/dsp/ControllerProperties.hpp
  presonus/surface/SLMappingState.hpp
  presonus/ChannelGroupFilter.hpp
  presonus/panel/PanelRegistrar.hpp
  presonus/surface/MarkerPageComponent.hpp
  presonus/surface/DAWDialogHandler.hpp
  presonus/mixer/AudioSetup.hpp
  presonus/surface/SurfaceChannelComponent.hpp
  presonus/surface/SurfaceInputComponent.hpp
  presonus/surface/SurfaceOutputComponent.hpp
  presonus/surface/ScribbleStripController.hpp
  presonus/SpectrumPainter.hpp
  presonus/DisplayCommandList.hpp
  presonus/ColorMapping.hpp
  presonus/IDAWTimeInfo.hpp
  presonus/surface/TransportHandler.hpp
  presonus/surface/AssignmentHandlerTable.hpp
  presonus/surface/DAWMixerHandler.hpp
  presonus/surface/MappingComponent.hpp
  presonus/surface/PresetsPageComponent.hpp
  presonus/mixer_dsp/Dsp.hpp
  presonus/mixer_dsp/EQControl.hpp
  presonus/IFaderPanel.hpp
  presonus/avb/SurfaceAvbComponent.hpp
  presonus/panel/SceneBook.hpp
  presonus/panel/FXBook.hpp
  presonus/uc/NetworkItem.hpp
  presonus/MixerSceneLoader.hpp
  presonus/panel/SPIControl.hpp
  presonus/panel/FxPresetComponent.hpp
  presonus/mixer/RackMixerComponent.hpp
  presonus/mixer/SendOutputComponent.hpp
  presonus/mixer/FXBusComponent.hpp
  presonus/mixer/GlobalComponent.hpp
  presonus/mixer/GEQLinkHandler.hpp
  presonus/PotControl.hpp
  presonus/FocusHelperButton.hpp
  presonus/AllMutesGroup.hpp
  presonus/FileMuteGroup.hpp
  presonus/McuVpotControl.hpp
  presonus/FaderUnitComponent.hpp
  presonus/MackieControlExtender.hpp
  presonus/MackieControlComponent.hpp
  presonus/surface/AudioUtilitiesPage.hpp
  presonus/surface/StartPageComponent.hpp
  presonus/surface/FaderUtilitiesPage.hpp
  presonus/MackieControlUnit.hpp
  presonus/surface/DAWLoadDocumentPage.hpp
  presonus/mixer/FilterGroupManager.hpp
  presonus/GridPainter.hpp
  presonus/panel/SPIControlGroup.hpp
  presonus/panel/PresetNameManager.hpp
  presonus/mixer/OutputComponent.hpp
  presonus/dsp/RuntimeGlobals.hpp
  presonus/AliasComponent.hpp
  presonus/DspComponent.hpp
  presonus/mixer/MixerComponent.hpp
  presonus/mixer/MixerComponentBase.hpp
  presonus/panel/FXPresetRecallComponent.hpp
  presonus/panel/StormFrontPanelComponent.hpp
  presonus/MainLCDComponent.hpp
  presonus/surface/NetworkSetupComponent.hpp
  presonus/panel/RackPanelComponent.hpp
  presonus/MeterControl.hpp
  presonus/panel/PresetNameCache.hpp
  presonus/dsp/SLReverbController.hpp
  presonus/panel/FrontPanelComponent.hpp
  presonus/mixer/ChannelComponent.hpp
  presonus/StormMuteGroupComponent.hpp
  presonus/mixer/NetworkSetupComponent.hpp
  presonus/surface/WifiSetupComponent.hpp
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
  presonus/uc/ClientSubscription.hpp
  presonus/PanControl.hpp
  presonus/uc/DataChannel.hpp
  presonus/uc/DiceEndPoint.hpp
  presonus/MackieControlModel.hpp
  presonus/MappingTable.hpp
  presonus/LinkableComponent.hpp
  presonus/dsp/Controller.hpp
  presonus/dsp/IController.hpp
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
  presonus/noaa/TCardFPGAUpdater.hpp
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
  presonus/noaa/card_handler_events.hpp
  presonus/uc/client_event_values.hpp
  presonus/mixer_dsp/FaderInterpolator.hpp
  presonus/dsp/audio_hal.hpp
  presonus/uc/client_implementation.hpp
  presonus/mixer_dsp/FilterParameterLists.hpp
  presonus/uc/network_activity_manager.hpp
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
  presonus/mixer_dsp/FilterControllers.hpp
  presonus/mixer_state/MixerState.hpp
  presonus/panel/registrar_group_registry.hpp
  presonus/surface_panel/DbTable.hpp
  presonus/surface_panel/MeterControl.hpp
  presonus/surface_panel/BitmapDrawing.hpp
  presonus/surface_panel/LEDState.hpp
  presonus/surface_panel/InputPin.hpp
  presonus/surface_panel/OutputPin.hpp
  presonus/embedded_dice/mix.hpp
  presonus/IFaderUnit.hpp
  presonus/TargetedComponent.hpp
  presonus/ThroughputTest.hpp
  presonus/mixer/AliasMapping.hpp
  presonus/mixer/ChannelDCAComponent.hpp
  presonus/mixer/DigitalInputComponent.hpp
  presonus/mixer/MixerComponentBaseDelegate.hpp
  presonus/mixer/ParamLink.hpp
  presonus/panel/AlertBook.hpp
  presonus/panel/Fat24FrontPanelComponent.hpp
  presonus/surface/AssignEditPageComponent.hpp
  presonus/surface/CalibrateTouchComponent.hpp
  presonus/surface/ChannelInfoPageComponent.hpp
  presonus/surface/ChannelPresetsPageComponent.hpp
  presonus/surface/FirmwarePageComponent.hpp
  presonus/surface/GeqPresetsPageComponent.hpp
  presonus/surface/LockoutPageComponent.hpp
  presonus/surface/MainScreenComponent.hpp
  presonus/surface/PreampsPageComponent.hpp
  presonus/surface/ScenesPageComponent.hpp
  presonus/surface/StChannelSettingsPageComponent.hpp
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
list(APPEND PRESONUS_UC_PUBLIC_HEADERS
  presonus/DAWClientComponent.hpp
  presonus/surface/FatChannelClipboard.hpp
  presonus/uc/ServerRootComponent.hpp
)
list(APPEND PRESONUS_UC_PUBLIC_HEADERS
  presonus/IBackgroundGridProvider.hpp
  presonus/LcdView.hpp
  presonus/dsp/CompController.hpp
  presonus/dsp/GateController.hpp
  presonus/mixer/StereoLineComponent.hpp
  presonus/uc/ClientRootComponent.hpp
  presonus/uc/server_description.hpp
)
list(APPEND PRESONUS_UC_PUBLIC_HEADERS
  presonus/DAWChannel.hpp
  presonus/DAWChannelGroup.hpp
)
list(APPEND PRESONUS_UC_PUBLIC_HEADERS
  presonus/MixerClassManager.hpp
  presonus/dsp/SimpleController.hpp
)
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

include(cmake/tests/LPCProgrammerInputRegistration.cmake)

include(cmake/UARTMessageSender.cmake)

include(cmake/UARTLedMeterSender.cmake)

include(cmake/tests/LPCProgrammerCommandInfoRegistration.cmake)

include(cmake/PanelPhantomPower.cmake)

include(cmake/tests/LPCProgrammerTransportRegistration.cmake)

include(cmake/tests/LPCProgrammerHandshakeRegistration.cmake)

include(cmake/SurfaceMapping.cmake)

include(cmake/FirmwareUpdateCallbacks.cmake)

include(cmake/UARTSenderExtensions.cmake)

include(cmake/SurfaceFaderControls.cmake)

include(cmake/PanelLCDDisplayControl.cmake)

include(cmake/PanelTemperature.cmake)

include(cmake/GraphTrial04.cmake)

include(cmake/GraphTrial05.cmake)

include(cmake/GraphTrial06.cmake)

include(cmake/GraphTrial07.cmake)

include(cmake/GraphTrial08.cmake)

include(cmake/GraphRanked09.cmake)

include(cmake/GraphRank20Cycle01.cmake)

include(cmake/GraphFrontierSmall01.cmake)

include(cmake/GraphFrontierScale01.cmake)

include(cmake/GraphFrontierScale02.cmake)

include(cmake/Reconstruction200Stage01.cmake)

include(cmake/Reconstruction200Stage02.cmake)

include(cmake/Large02LifecycleFix.cmake)

include(cmake/tests/AVBRouteRegistration.cmake)

include(cmake/tests/NetworkRegistration.cmake)

# Stabilized production cycle01: real provider composition, compile once per role.
set_source_files_properties(src/Presonus/SLChannel.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti")
include(cmake/tests/StabilizedRegistration.cmake)

include(cmake/Rolling200Implementation01.cmake)
include(cmake/Rolling200Implementation02.cmake)
include(cmake/Rolling200Closeout02.cmake)

include(cmake/ComponentReadonlyReplays.cmake)

include(cmake/ProductionRecoveryReplays.cmake)

include(cmake/ComponentCallbackReplays.cmake)

include(cmake/ComponentParameterReplays.cmake)

include(cmake/tests/NextFlowOMAPReplays.cmake)

include(cmake/tests/NextFlowGateReplays.cmake)

include(cmake/tests/NextFlowHandlersReplays.cmake)

include(cmake/tests/NextFlowFirmwareReplays.cmake)

include(cmake/tests/NextFlowScenesReplays.cmake)

include(cmake/tests/NextFlowMackieReplays.cmake)

include(cmake/tests/NextFlowSurfaceAVBReplays.cmake)

include(cmake/tests/NextFlowCopyReplays.cmake)

include(cmake/tests/NextFlowMixerAVBReplays.cmake)

include(cmake/tests/NextFlowScenesConstructorReplays.cmake)

include(cmake/tests/NextFlowPanelLookupReplays.cmake)

include(cmake/tests/NextFlowPagesReplays.cmake)

include(cmake/tests/NextFlowFocusLifecycleReplays.cmake)

include(cmake/tests/Remaining14GlobalInitializeReplay.cmake)

include(cmake/tests/NextFlowMainLCDReplays.cmake)

include(cmake/tests/Base6Replays.cmake)

include(cmake/tests/PhaseBFinalReplays.cmake)

include(cmake/tests/Trial10x2Replays.cmake)

include(cmake/tests/Next39Replays.cmake)

include(cmake/tests/Control10x20Replays.cmake)
