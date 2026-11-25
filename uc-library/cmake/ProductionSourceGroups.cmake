set(PRESONUS_common_SOURCES
  src/Presonus/DAWClientComponent.cpp
  src/Presonus/UC/ServerRootComponent.cpp
  src/Presonus/DAWFocusChannel.cpp
  src/Presonus/DAWChannel.cpp
  src/Presonus/DAWChannelGroup.cpp
  src/Presonus/DAWDeviceFolder.cpp
  src/Presonus/DAWDeviceSlot.cpp
  src/Presonus/UC/ClientRootComponent.cpp
  src/Presonus/UC/DiscoveryAttributes.cpp
  src/Presonus/UC/Format/Celsius.cpp
  src/Presonus/UC/Format/ChannelNameFormatter.cpp
  src/Presonus/UC/ParamRange.cpp
  src/Presonus/UC/ServerImplementation.cpp
  src/Presonus/Panel/MeterLevelControl.cpp
  src/Presonus/Panel/MeterPeakControl.cpp
  src/Presonus/UC/Element.cpp
  src/Presonus/UC/MetaElement.cpp
  src/Presonus/UC/MidiEndpoint.cpp
  src/Presonus/UC/MidiEndpointRegistry.cpp
  src/Presonus/UC/RemoteEventSender.cpp
  src/Presonus/UC/ServerDescription.cpp
  src/Presonus/IDAWDialogHandler.cpp
  src/Presonus/Panel/GPIOControlGroup.cpp
  src/Presonus/TouchInputEvent.cpp
  src/Presonus/UC/ClientComponent.cpp
  src/Presonus/UC/LocalServer.cpp
  src/Presonus/UC/ServerComponent.cpp
  src/Presonus/MixerClientPresetCleanup.cpp
  src/Presonus/Mixer/DecayTimeFormatterT6.cpp
  src/Presonus/Mixer/DecayTimeFormatterT7.cpp
  src/Presonus/Mixer/DecayTimeFormatterT8.cpp
  src/Presonus/Mixer/DecayTimeFormatterT9.cpp
  src/Presonus/Mixer/EarlyRefFormatterT2.cpp
  src/Presonus/Mixer/PreDelayFormatterT2.cpp
  src/Presonus/Panel/LCDComponent.cpp
  src/Presonus/MeterMaid.cpp
  src/Presonus/Mixer/DecayTimeFormatterT1.cpp
  src/Presonus/Mixer/DecayTimeFormatterT2.cpp
  src/Presonus/Mixer/DecayTimeFormatterT3.cpp
  src/Presonus/Mixer/DecayTimeFormatterT4.cpp
  src/Presonus/Mixer/DecayTimeFormatterT5.cpp
  src/Presonus/Mixer/DelayTimeFormatter.cpp
  src/Presonus/Mixer/EarlyRefFormatterT3.cpp
  src/Presonus/Mixer/EarlyRefFormatterT4.cpp
  src/Presonus/Mixer/EarlyRefFormatterT5.cpp
  src/Presonus/Mixer/EarlyRefFormatterT6.cpp
  src/Presonus/Mixer/PreDelayFormatterT3.cpp
  src/Presonus/Mixer/PreDelayFormatterT4.cpp
  src/Presonus/Mixer/PreDelayFormatterT5.cpp
  src/Presonus/Mixer/StereoSpreadFormatter.cpp
  src/Presonus/Panel/ControlRegistrarDelegate.cpp
  src/Presonus/MeterBallistics.cpp
  src/Presonus/Mixer/ChDelayFormatter.cpp
  src/Presonus/Mixer/ChGainFormatter.cpp
  src/Presonus/Mixer/ChHPFFormatter.cpp
  src/Presonus/Mixer/EarlyRefFormatter.cpp
  src/Presonus/Mixer/FilterFreqFormatter.cpp
  src/Presonus/Mixer/FilterGainFormatter.cpp
  src/Presonus/Mixer/GeqFreqFormatter.cpp
  src/Presonus/Mixer/NumberPrepender.cpp
  src/Presonus/Mixer/PreDelayFormatter.cpp
  src/Presonus/Mixer/SubDelayFormatter.cpp
  src/Presonus/Panel/FillElement.cpp
  src/Presonus/Panel/StaticElement.cpp
  src/Presonus/Panel/FieldElement.cpp
  src/Presonus/Panel/OffscreenElement.cpp
  src/Presonus/Panel/LCDManager.cpp
  src/Presonus/Panel/Page.cpp
  src/Presonus/Panel/TextEntryElement.cpp
  src/Presonus/Panel/ControlRegistrarCommands.cpp
  src/Presonus/MuteGroupActivation.cpp
  src/Presonus/Mixer/FxPresetFilter.cpp
  src/Presonus/Mixer/GEQPresetFilter.cpp
  src/Presonus/Mixer/ChannelParamTagFilter.cpp
  src/Presonus/Mixer/SmaartStoreFilter.cpp
  src/Presonus/Mixer/ChannelParameterController.cpp
  src/Presonus/AltMemoryFilter.cpp
  src/Presonus/UC/ClientSubscription.cpp
  src/Presonus/Dsp/EqSourceProviders.cpp
  src/Presonus/Panel/Element.cpp
  src/Presonus/MappableMixer.cpp
  src/Presonus/Panel/SharedMemoryComm.cpp
  src/Presonus/MixerClientComponentBase.cpp
  src/Presonus/SLChannel.cpp
  src/Presonus/UC/EventDispatcherLifetime.cpp
  src/Presonus/UC/AdapterHandlerLifetime.cpp
  src/Presonus/UC/ServerRegistrarLifetime.cpp
  src/Presonus/UC/ServerLifetime.cpp
  src/Presonus/MuteGroupBase.cpp
  src/Presonus/MuteGroupFilter.cpp
  src/Presonus/ChannelGroupFilter.cpp
  src/Presonus/VUMeterControl.cpp
  src/Presonus/LinkableComponent.cpp
  src/Presonus/Panel/FrontPanelRouting.cpp
  src/Presonus/Panel/PanelRegistrar.cpp
  src/Presonus/Surface/PanelRegistrarPort.cpp
  src/Presonus/Dsp/ShelbyGEQController.cpp
  src/Presonus/Dsp/EQControllerProcess.cpp
  src/Presonus/EQControlBandParams.cpp
  src/Presonus/AVB/AvbComponentChannels.cpp
  src/Presonus/AVB/SurfaceAvbComponent.cpp
  src/Presonus/Mixer/NetworkSetupMixerBinding.cpp
  src/Presonus/Surface/NetworkSetupSlaveLookup.cpp
  src/Presonus/UC/NetworkItem.cpp
  src/Presonus/PotControl.cpp
  src/Presonus/FocusHelperButton.cpp
  src/Presonus/AllMutesGroup.cpp
  src/Presonus/FileMuteGroup.cpp
  src/Presonus/McuVpotControl.cpp
  src/Presonus/MappingTableHardwareParameter.cpp
  src/Presonus/Panel/PanelComponentTests.cpp
  src/Presonus/Panel/Book.cpp
  src/Presonus/Panel/ControlRegistrarAccess.cpp
  src/Presonus/UARTPowerGainSender.cpp
  src/Presonus/UARTColorBrightnessSender.cpp
  src/Presonus/UARTLedStateSender.cpp
  src/Presonus/Panel/LCDDisplayControl.cpp
  src/Presonus/Panel/TemperatureControl.cpp
  src/common/FirmwareCallbackText.cpp
  src/Presonus/Panel/PhantomPowerControl.cpp
  src/Presonus/LPCProgrammerTransport.cpp
  src/Presonus/LPCProgrammerHandshake.cpp
  src/Presonus/UARTMessageSender.cpp
  src/Presonus/UARTLedMeterSender.cpp
  src/Presonus/LPCProgrammerCommandInfo.cpp
  src/Presonus/LPCProgrammerImageGeometry.cpp
  src/Presonus/LPCProgrammerInput.cpp
  src/Presonus/OutputPinLifecycle.cpp
  src/Presonus/Panel/BitmapCopy.cpp
  src/Presonus/Panel/BitmapFlush.cpp
  src/Presonus/Panel/BitmapLifecycle.cpp
  src/Presonus/Panel/BitmapText.cpp
  src/Presonus/Panel/FontMidData.cpp
  src/Presonus/Panel/TinyFontMetrics.cpp
  src/Presonus/UUX/FirmwareUpdaterDispatch.cpp
  src/Presonus/UUX/FirmwareUpdaterHostProcess.cpp
  src/Presonus/UUX/FirmwareUpdaterPaths.cpp
  src/Presonus/LPCProgrammerGeometry.cpp
  src/Presonus/Panel/MotorizedFaderControl.cpp
  src/Presonus/Panel/EncoderControl.cpp
  src/Presonus/Panel/KeyInputProvider.cpp
  src/Presonus/Panel/BlinkLEDControl.cpp
  src/Presonus/Panel/InputGPIOControl.cpp
  src/Presonus/UC/SocketConnectionIdentity.cpp
  src/Presonus/UC/ReportFunctions.cpp
  src/Presonus/UC/NetworkManagerMulticastCallback.cpp
  src/Presonus/UC/NetworkManagerDiscoveryCallbacks.cpp
  src/Presonus/UC/EventItem.cpp
  src/Presonus/UC/EventFactoryLifetime.cpp
  src/Presonus/UC/NetworkActivityBootstrap.cpp
  src/Presonus/UC/BasicConnectionQueueStorage.cpp
  src/Presonus/UC/BasicConnectionLifetime.cpp
  src/Presonus/Mixer/GeqGainFormatter.cpp
  src/Presonus/Mixer/FilterQFormatter.cpp
  src/Presonus/Mixer/ScaledTimeFormatter.cpp
  src/Presonus/Mixer/FeedbackFormatter.cpp
  src/Presonus/Mixer/DecayTimeFormatter.cpp
  src/Presonus/UC/MidiConnection.cpp
  src/Presonus/Dsp/MillisecondsFormatterSingleton.cpp
  src/Presonus/UC/EventQueueLifetime.cpp
  src/Presonus/UC/Format/OnOff.cpp
  src/Presonus/UC/ClientTypedOrigins.cpp
  src/Presonus/UC/ClientConnectionDispatch.cpp
  src/Presonus/UC/ClientEventValues.cpp
  src/Presonus/Dsp/FaderInterpolator.cpp
  src/Presonus/UC/ClientStateTracking.cpp
  src/Presonus/UC/NetworkActivityManager.cpp
  src/Presonus/UC/MessageQueue.cpp
  src/Presonus/UC/MutableMessageEvent.cpp
  src/Presonus/UC/MessageAttributesEvent.cpp
  src/Presonus/UC/MessageAttributes.cpp
  src/Presonus/Dsp/GateMeterInterpolators.cpp
  src/Presonus/Dsp/FaderCurveInterpolator.cpp
  src/Presonus/UC/UDPDiscoveryLifecycle.cpp
  src/portable/dice/OwnedUartServices.cpp
  src/Presonus/UC/MulticastSocketServices.cpp
  src/mixer_dsp/AdditionalFormatters.cpp
  src/mixer_dsp/Formatters.cpp
  src/mixer_dsp/Power.cpp
  src/Presonus/UC/UDPDiscoveryServices.cpp
  src/Presonus/UC/AdapterServices.cpp
  src/mixer_dsp/Interpolators.cpp
  src/mixer_dsp/Logarithm.cpp
  src/Presonus/UC/ServerMetadata.cpp
  src/Presonus/UC/ServerRegistrarServices.cpp
  src/Presonus/UC/ConnectionHandlerQueries.cpp
  src/Presonus/UC/NetworkManagerConfiguration.cpp
  src/DSP/BiquadIncremental.cpp
  src/DSP/BiquadSine.cpp
  src/Presonus/UC/ServerRegistrarListeners.cpp
  src/Presonus/UC/NetworkManagerListeners.cpp
  src/Presonus/UC/NetworkManagerNextServices.cpp
  src/DSP/BiquadMethods.cpp
  src/Presonus/UC/NetworkManagerServices.cpp
  src/Presonus/Panel/PotFaderControl.cpp
  src/portable/panel/PotFaderParameterGateway.cpp
  src/Presonus/Panel/SwitchDispatch.cpp
  src/portable/panel/SwitchDispatchParameterGateway.cpp
  src/Presonus/UC/FileTransferManagerTransfers.cpp
  src/Presonus/UC/FileTransferManager.cpp
  src/Presonus/Panel/SwitchControl.cpp
  src/portable/panel/SwitchParameterGateway.cpp
  src/Presonus/Panel/LEDControlLifecycle.cpp
  src/Presonus/UC/FileServerImplementation.cpp
  src/Presonus/UC/FileTransfer.cpp
  src/Presonus/Panel/input_pin_lifetime.cpp
  src/Presonus/Panel/control.cpp
  src/Presonus/UC/FileServices.cpp
  src/Presonus/Panel/param_edit_handler.cpp
  src/application/FirmwareBundleStreams.cpp
  src/Presonus/UARTMessageHandler.cpp
  src/application/ResourceLibrary.cpp
  src/Presonus/DelayTimer.cpp
  src/Presonus/Panel/simulate_comm.cpp
  src/application/FileCleanup.cpp
  src/Presonus/Panel/protocol_comm.cpp
  src/Presonus/Panel/uart_protocol.cpp
  src/Presonus/Panel/UARTComm.cpp
  src/Presonus/Panel/alert_manager.cpp
  src/application/SimpleReader.cpp
  src/portable/dice/PacketLogging.cpp
  src/application/ApplicationManagers.cpp
  src/Presonus/UC/data_codecs.cpp
  src/Presonus/AVB/AvbManagerLookup.cpp
  src/Presonus/AVB/AvbManagerReceive.cpp
  src/Presonus/AVB/Protocol.cpp
  src/Presonus/AVB/Streams.cpp
  src/Presonus/DICE/Codec.cpp
  src/Presonus/DICE/PacketClockGateway.cpp
  src/Presonus/UC/basic_connection.cpp
  src/Presonus/UC/ccl_bindings.cpp
  src/Presonus/UC/connection.cpp
  src/Presonus/UC/connection_receive.cpp
  src/Presonus/UC/discovery_events.cpp
  src/Presonus/UC/dispatcher_registration.cpp
  src/Presonus/UC/event_dispatcher.cpp
  src/Presonus/UC/event_factory.cpp
  src/Presonus/UC/event_queue.cpp
  src/Presonus/UC/events.cpp
  src/Presonus/UC/external_connection.cpp
  src/Presonus/UC/file_control_events.cpp
  src/Presonus/UC/file_data_events.cpp
  src/Presonus/UC/meter_events.cpp
  src/Presonus/UC/misc_events.cpp
  src/Presonus/UC/no_member_events.cpp
  src/Presonus/UC/parameter_events.cpp
  src/Presonus/UC/primitive_dispatch.cpp
  src/Presonus/UC/socket_channel.cpp
  src/Presonus/UC/transport_events.cpp
  src/core_uc/buffer.cpp
  src/embedded_dice/mix.cpp
  src/mixer_dsp/Dsp.cpp
  src/mixer_state/MixerState.cpp
  src/network.cpp
  src/portable/dice/CclResponseServices.cpp
  src/portable/dice/ResponseWait.cpp
  src/protocol.cpp
  src/surface_panel/BitmapDrawing.cpp
  src/surface_panel/ControlGroup.cpp
  src/surface_panel/DigitalPotControl.cpp
  src/surface_panel/ControlHelpers.cpp
  src/surface_panel/DbTable.cpp
  src/surface_panel/InputPin.cpp
  src/surface_panel/LEDState.cpp
  src/surface_panel/MeterControl.cpp
  src/surface_panel/OutputPin.cpp
  src/Presonus/Panel/Fat24FrontPanelComponent.cpp
)
set(PRESONUS_cs18_SOURCES
  src/Presonus/Surface/FatChannelClipboardSelection.cpp
  src/application/SurfaceApplicationSkinDirectory.cpp
  src/Presonus/DynamicsControl.cpp
  src/ColorButton.cpp
  src/IconManager.cpp
  src/Presonus/Surface/SoloPageComponent.cpp
  src/DefaultMeterInterpolator.cpp
  src/LPFControl.cpp
  src/Presonus/Surface/UCMidiInputAdapter.cpp
  src/Presonus/Surface/UCMidiOutputAdapter.cpp
  src/Presonus/Surface/ChannelInfoPageComponent.cpp
  src/Presonus/Surface/MixSettingsPageComponent.cpp
  src/Presonus/Surface/FatChannelClipboard.cpp
  src/Presonus/Surface/ScenesPageComponent.cpp
  src/Presonus/Surface/GatePageComponent.cpp
  src/Presonus/Surface/PageHeaderComponent.cpp
  src/Presonus/Surface/CascadeHandler.cpp
  src/Presonus/Surface/MonitorPageComponent.cpp
  src/Presonus/Surface/ControlName.cpp
  src/Presonus/FocusRestorer.cpp
  src/Presonus/Surface/TBRoutingPageComponent.cpp
  src/Presonus/Surface/FXHomePageComponent.cpp
  src/Presonus/Surface/FxPresetsPageComponent.cpp
  src/Presonus/Surface/FXEditPageComponent.cpp
  src/Presonus/GridPainter.cpp
  src/Presonus/GridPainterLifecycle.cpp
  src/Presonus/GridPainterRendering.cpp
  src/Presonus/DAWTimeMapsConstruction.cpp
  src/Presonus/MappingTablePageName.cpp
  src/Presonus/MappingTableItem.cpp
  src/Presonus/Surface/SurfaceRootMappingPredicate.cpp
  src/Presonus/BackgroundPainter.cpp
  src/Presonus/MappingTableConnect.cpp
  src/Presonus/MappablePageComponent.cpp
  src/Presonus/ModalPageComponent.cpp
  src/Presonus/Surface/PageParam.cpp
  src/Presonus/Surface/MappingControllerParameters.cpp
  src/Presonus/Surface/SLMixerLifecycle.cpp
  src/Presonus/Color/MixerColorConverter.cpp
  src/Presonus/Color/ColorMappingName.cpp
  src/Presonus/Surface/GroupsPageRecovery.cpp
  src/Presonus/Surface/PanelRegistrarTests.cpp
  src/Presonus/Surface/SurfaceRootComponent.cpp
  src/Presonus/PanControlBindings.cpp
  src/Presonus/MeterControlConnection.cpp
  src/Presonus/MeterScaleControl.cpp
  src/Presonus/Surface/MuteGroupsComponent.cpp
  src/Presonus/Surface/MixerPageComponent.cpp
  src/Presonus/Surface/SubAssignPageComponent.cpp
  src/Presonus/Surface/EQPageEncoderMode.cpp
  src/Presonus/Surface/SLMixerMapping.cpp
  src/Presonus/Surface/MarkerPageComponent.cpp
  src/Presonus/Surface/DAWDialogHandler.cpp
  src/Presonus/Surface/DawFxPageMapping.cpp
  src/Presonus/Surface/MidiMixerState.cpp
  src/Presonus/Surface/SurfaceChannelComponent.cpp
  src/Presonus/Surface/ScribbleStripController.cpp
  src/Presonus/Surface/SurfaceOutputComponent.cpp
  src/Presonus/Surface/SurfaceInputComponent.cpp
  src/Presonus/SpectrumPainter.cpp
  src/Presonus/DisplayCommandList.cpp
  src/Presonus/ColorMapping.cpp
  src/Presonus/DAWTimeInfoEvents.cpp
  src/Presonus/IDAWTimeInfo.cpp
  src/Presonus/Surface/TransportHandler.cpp
  src/Presonus/AssignmentHandlerRegistration.cpp
  src/Presonus/Surface/DAWMixerActivation.cpp
  src/Presonus/Surface/SLMixerGeqState.cpp
  src/Presonus/Surface/GeqPageComponent.cpp
  src/Presonus/Surface/EQPageObservers.cpp
  src/Presonus/Surface/PresetsPageMappingController.cpp
  src/Presonus/Surface/MappingMainMixLock.cpp
  src/Presonus/MackieControlModelMappings.cpp
  src/Presonus/IFaderPanel.cpp
  src/Presonus/MackieControlComponentModel.cpp
  src/Presonus/DisplayManagerTouch.cpp
  src/Presonus/MackieControlModelHostConnection.cpp
  src/Presonus/Surface/MidiMixerControls.cpp
  src/Presonus/FaderUnitComponent.cpp
  src/Presonus/MackieControlExtender.cpp
  src/Presonus/MackieControlComponent.cpp
  src/Presonus/Surface/AudioUtilitiesPage.cpp
  src/Presonus/Surface/StartPageComponent.cpp
  src/Presonus/Surface/FaderUtilitiesPage.cpp
  src/Presonus/Surface/DAWLoadDocumentPage.cpp
  src/Presonus/Surface/SLMixerHandler.cpp
  src/Presonus/MackieControlUnit.cpp
  src/Presonus/Surface/PageObservers.cpp
  src/Presonus/Surface/NetworkListSelection.cpp
  src/Presonus/MainLCDPageStack.cpp
  src/Presonus/DisplayManagerInstance.cpp
  src/Presonus/DAWTimeMaps.cpp
  src/Presonus/AssignmentHandlerTable.cpp
  src/Presonus/EQControl.cpp
  src/Presonus/MainLCDComponent.cpp
  src/Presonus/Surface/MappingComponent.cpp
  src/Presonus/Surface/DAWMixerHandler.cpp
  src/Presonus/MeterControl.cpp
  src/Presonus/Surface/NetworkSetupComponent.cpp
  src/Presonus/Surface/RadioToggleButton.cpp
  src/Presonus/Surface/CapturePageComponent.cpp
  src/Presonus/Surface/GroupsEditPageComponent.cpp
  src/Presonus/Surface/PresetsPageComponent.cpp
  src/Presonus/Surface/WifiSetupComponent.cpp
  src/Presonus/PanControl.cpp
  src/Presonus/LinkControl.cpp
  src/Presonus/Surface/GroupsPageComponent.cpp
  src/Presonus/Surface/DawFxPageComponent.cpp
  src/Presonus/PageComponent.cpp
  src/Presonus/Surface/MidiMixerHandler.cpp
  src/Presonus/Surface/MidiMixerLifecycle.cpp
  src/Presonus/Surface/PanelRegistrarMidiDispatch.cpp
  src/Presonus/MappingTable.cpp
  src/Presonus/MackieControlModel.cpp
  src/Presonus/PCM4104/Pcm4104Spi.cpp
  src/Presonus/DAWTimeInfo.cpp
  src/Presonus/Surface/PanelRegistrarFaderCommands.cpp
  src/Presonus/Surface/PanelRegistrarFaderReadout.cpp
  src/Presonus/Surface/PanelRegistrarFaderParameterWrites.cpp
  src/Presonus/Surface/MappingInputRoutes.cpp
  src/Presonus/Surface/MappingRadioRoutes.cpp
  src/Presonus/Surface/MappingRadioValidation.cpp
  src/Presonus/Surface/MappingMeterRouting.cpp
  src/Presonus/Surface/FirmwareUpdateCallbacks.cpp
  src/Presonus/DisplayManagerFlush.cpp
  src/Presonus/ScribbleStripMgr.cpp
  src/Presonus/Surface/LCDPort.cpp
  src/Presonus/Surface/LCDPortLifecycle.cpp
  src/Presonus/Surface/SLMixerEncoder.cpp
  src/Presonus/Surface/SLMixerFootswitch.cpp
  src/Presonus/Surface/SLMixerDigitalParams.cpp
  src/Presonus/EQControlBiquad.cpp
  src/Presonus/DICE/Dice3ManagerLifecycle.cpp
  src/portable/dice/CclManagerOwnedRuntime.cpp
  src/portable/dice/ManagerWorkerGuard.cpp
  src/Presonus/DICE/Dice3SubsystemLifecycle.cpp
  src/Presonus/DICE/Dice3ManagerControl.cpp
  src/Presonus/DICE/Dice3SubsystemControl.cpp
  src/portable/dice/CclSubsystemRuntime.cpp
  src/utilities/StringUtils.cpp
  src/Presonus/DICE/Dice3ManagerFirmware.cpp
  src/portable/dice/ManagerProgrammerServices.cpp
  src/Presonus/DICE/Dice3ProgrammerErase.cpp
  src/Presonus/DICE/Dice3ProgrammerUpdate.cpp
  src/Presonus/DICE/Dice3ProgrammerDevice.cpp
  src/portable/dice/LinuxProgrammerDeviceServices.cpp
  src/Presonus/DICE/Dice3ProgrammerPages.cpp
  src/Presonus/DICE/Dice3ProgrammerTransactions.cpp
  src/portable/dice/CclProgrammerServices.cpp
  src/Presonus/DICE/SysexReceiverLifecycle.cpp
  src/Presonus/DICE/Dice3ManagerServices.cpp
  src/portable/dice/CclManagerServices.cpp
  src/embedded_efm/efm_control_dispatch.cpp
  src/embedded_panel/PanelProtocol.cpp
  src/embedded_panel/UpdateLoop.cpp
  src/embedded_efm/efm_parameter_fields.cpp
  src/embedded_efm/efm_packed_parameters.cpp
  src/embedded_efm/efm_packet_checks.cpp
  src/embedded_efm/efm_version_packet.cpp
  src/application/SurfaceApplicationIdentity.cpp
  src/Presonus/DICE/Dice3UartLifetime.cpp
  src/Presonus/DICE/Dice3UartTransport.cpp
  src/application/SurfaceApplicationSerial.cpp
  src/Presonus/DICE/SysexPacketLog.cpp
  src/portable/dice/CclPacketLogSink.cpp
  src/Presonus/DICE/Dice3UartAssembly.cpp
  src/Presonus/DICE/UartRegistration.cpp
  src/portable/dice/UartAssemblyState.cpp
  src/portable/dice/CclAssemblyCallbacks.cpp
  src/Presonus/DICE/Dice3Manager.cpp
  src/Presonus/DICE/Dice3Programmer.cpp
  src/Presonus/DICE/Dice3Subsystem.cpp
  src/Presonus/DICE/Dice3SubsystemCommands.cpp
  src/Presonus/DICE/SysexPacket.cpp
  src/Presonus/DICE/SysexPacketConstruction.cpp
  src/Presonus/DICE/SysexReceiver.cpp
  src/Presonus/DICE/SysexReceiverWait.cpp
  src/Presonus/IFaderUnit.cpp
  src/Presonus/Surface/AssignEditPageComponent.cpp
  src/Presonus/Surface/CalibrateTouchComponent.cpp
  src/Presonus/Surface/ChannelPresetsPageComponent.cpp
  src/Presonus/Surface/FirmwarePageComponent.cpp
  src/Presonus/Surface/GeqPresetsPageComponent.cpp
  src/Presonus/Surface/LockoutPageComponent.cpp
  src/Presonus/Surface/MainScreenComponent.cpp
  src/Presonus/Surface/PreampsPageComponent.cpp
  src/Presonus/Surface/StChannelSettingsPageComponent.cpp
  src/Presonus/ThroughputTest.cpp
)
set(PRESONUS_rm_SOURCES
  src/Presonus/Dsp/EQ4Controller.cpp
  src/Presonus/Dsp/EQ5Controller.cpp
  src/Presonus/Mixer/MixerApplication.cpp
  src/Presonus/Dsp/LimiterController.cpp
  src/Presonus/Mixer/DCALevelHandler.cpp
  src/Presonus/Panel/AlertPage.cpp
  src/DSPManager.cpp
  src/utilities/DfuDiagnostic.cpp
  src/utilities/TableElements.cpp
  src/Presonus/Panel/GambitPanelComponent.cpp
  src/Presonus/Panel/WolverinePanelComponent.cpp
  src/Presonus/Mixer/AudioComponent.cpp
  src/Presonus/Mixer/BeastMixerComponent.cpp
  src/Presonus/Mixer/StormMixerComponent.cpp
  src/Presonus/Mixer/MonoMainComponent.cpp
  src/Presonus/Mixer/TapeInputComponent.cpp
  src/Presonus/Mixer/GroupChangeObserver.cpp
  src/Presonus/Panel/AlertBook.cpp
  src/Presonus/Panel/PanelParameterTables.cpp
  src/Presonus/Dsp/OMAPTargetHandler.cpp
  src/Presonus/Panel/BeastFrontPanelComponent.cpp
  src/Presonus/Mixer/GEQComponent.cpp
  src/Presonus/Mixer/MonoBusComponent.cpp
  src/Presonus/Mixer/EQComponent.cpp
  src/Presonus/Mixer/GateComponent.cpp
  src/Presonus/Mixer/HPFilterComponent.cpp
  src/Presonus/Mixer/LPFilterComponent.cpp
  src/Presonus/Mixer/LimiterComponent.cpp
  src/Presonus/Panel/FXMainPage.cpp
  src/Presonus/Panel/JoinNetworkPage.cpp
  src/Presonus/Panel/SystemAboutPage.cpp
  src/Presonus/Panel/RogueFrontPanelComponent.cpp
  src/Presonus/Panel/FATLEDOverridePage.cpp
  src/Presonus/Mixer/AutoFilterGroupManager.cpp
  src/Presonus/Panel/FXPage.cpp
  src/Presonus/Panel/WolverinePanelRegistrar.cpp
  src/Presonus/Panel/GEQPage.cpp
  src/Presonus/Mixer/WolverineRMLApplication.cpp
  src/Presonus/Mixer/GambitRMLApplication.cpp
  src/Presonus/Mixer/ControlMapping.cpp
  src/Presonus/Mixer/ReverbComponent.cpp
  src/Presonus/Mixer/GambitMixerComponent.cpp
  src/Presonus/Panel/RoguePanelRegistrar.cpp
  src/Presonus/Panel/GambitPanelRegistrar.cpp
  src/Presonus/Panel/StormPanelRegistrar.cpp
  src/Presonus/Mixer/CascadeLinkHandler.cpp
  src/Presonus/Mixer/DelayComponent.cpp
  src/Presonus/Mixer/TalkbackInputComponent.cpp
  src/Presonus/Mixer/MicLineComponent.cpp
  src/Presonus/Mixer/SceneFilter.cpp
  src/Presonus/Panel/RackPanelBurnIn.cpp
  src/Presonus/Panel/PanelRegistrarDualMessage.cpp
  src/Presonus/NOAA/TCardUCNetHandlerLifecycle.cpp
  src/Presonus/Dsp/ControllerInterface.cpp
  src/Presonus/StormMuteActivation.cpp
  src/Presonus/StormMixScenePaths.cpp
  src/Presonus/Panel/PanelRegistrarReset.cpp
  src/Presonus/NOAA/TCardFirmware.cpp
  src/Presonus/Panel/ParamEnablementHandler.cpp
  src/Presonus/Mixer/ChannelPresetFilter.cpp
  src/Presonus/Mixer/FilterGroupComponent.cpp
  src/Presonus/StormSafeMuteFilter.cpp
  src/Presonus/Dsp/ControllerInfo.cpp
  src/Presonus/Link/Messenger.cpp
  src/Presonus/Panel/FrontPanelUartTest.cpp
  src/Presonus/Mixer/MixerRouteInputsToNet.cpp
  src/Presonus/Panel/ChannelPresetComponent.cpp
  src/Presonus/Panel/GeqPresetComponent.cpp
  src/Presonus/Panel/ScenesComponent.cpp
  src/Presonus/AVB/AvbComponentRouting.cpp
  src/Presonus/Mixer/AVBRemoteMixerHandler.cpp
  src/Presonus/Mixer/AVBCascadeConnections.cpp
  src/Presonus/Dsp/EQController.cpp
  src/Presonus/Panel/PanelComponentLifecycle.cpp
  src/Presonus/Panel/FrontPanelLifecycle.cpp
  src/Presonus/Mixer/ApplicationSetup.cpp
  src/Presonus/Panel/SceneBook.cpp
  src/Presonus/Mixer/GlobalComponent.cpp
  src/Presonus/Mixer/FXBusComponent.cpp
  src/Presonus/Panel/FXBook.cpp
  src/Presonus/Mixer/RackMixerApplication.cpp
  src/Presonus/Mixer/RackMixerComponent.cpp
  src/Presonus/Mixer/SendOutputComponent.cpp
  src/Presonus/Mixer/GEQLinkHandler.cpp
  src/Presonus/MixerSceneLoader.cpp
  src/Presonus/Panel/SPIControl.cpp
  src/Presonus/Panel/FxPresetComponent.cpp
  src/Presonus/Panel/PresetComponentSlotPaths.cpp
  src/Presonus/Mixer/FilterGroupManager.cpp
  src/Presonus/Panel/SPIControlGroup.cpp
  src/Presonus/Panel/PresetNameManager.cpp
  src/Presonus/Panel/GeqAssignedChannel.cpp
  src/Presonus/Mixer/OutputComponent.cpp
  src/Presonus/Mixer/MixerBaseLinks.cpp
  src/Presonus/Dsp/RuntimeGlobals.cpp
  src/Presonus/Dsp/ControllerSetupProcess.cpp
  src/Presonus/AliasComponent.cpp
  src/Presonus/DspComponent.cpp
  src/Presonus/Mixer/MixerComponent.cpp
  src/Presonus/Mixer/MixerComponentBase.cpp
  src/Presonus/Panel/FXPresetRecallComponent.cpp
  src/Presonus/Panel/StormFrontPanelComponent.cpp
  src/Presonus/StormMuteGroupComponent.cpp
  src/Presonus/Mixer/ChannelComponent.cpp
  src/Presonus/Panel/FrontPanelComponent.cpp
  src/Presonus/Dsp/SLReverbController.cpp
  src/Presonus/Panel/PresetNameCache.cpp
  src/Presonus/Panel/RackPanelComponent.cpp
  src/Presonus/Panel/PanelTask.cpp
  src/Presonus/Panel/LEDNotifyTask.cpp
  src/Presonus/Mixer/MasterSectionComponent.cpp
  src/Presonus/Mixer/InputComponent.cpp
  src/Presonus/Mixer/NetworkSelectComponent.cpp
  src/Presonus/Panel/PresetComponent.cpp
  src/Presonus/Panel/GeqUIComponent.cpp
  src/Presonus/Mixer/NetworkSetupComponent.cpp
  src/Presonus/Mixer/PermissionsComponent.cpp
  src/Presonus/MeterManagerBase.cpp
  src/Presonus/Mixer/AVBCascadeManager.cpp
  src/Presonus/Mixer/FXComponent.cpp
  src/Presonus/StormMixSceneComponent.cpp
  src/Presonus/Panel/PanelComponent.cpp
  src/Presonus/Panel/MixerLCD.cpp
  src/Presonus/AVB/AvbComponent.cpp
  src/Presonus/Dsp/Controller.cpp
  src/Presonus/UC/DataChannel.cpp
  src/Presonus/UC/DiceEndPoint.cpp
  src/Presonus/Panel/BeastPanelRegistrar.cpp
  src/Presonus/Mixer/FirmwareUpdateCallbacks.cpp
  src/Presonus/NOAA/TCardProgrammerProtocol.cpp
  src/Presonus/NOAA/TCardProgrammerInformation.cpp
  src/Presonus/NOAA/TCardProgrammerReceive.cpp
  src/Presonus/NOAA/TCardProgrammerSerial.cpp
  src/Presonus/NOAA/TCardRouterLifecycle.cpp
  src/Presonus/NOAA/TCardRouterScript.cpp
  src/Presonus/NOAA/TCardRouterInitialization.cpp
  src/Presonus/NOAA/TCardProgrammerLifecycle.cpp
  src/Presonus/NOAA/TCardProgrammerTransport.cpp
  src/Presonus/NOAA/TCardProgrammerUpdate.cpp
  src/Presonus/NOAA/TCardRouterMixerInputRoutes.cpp
  src/Presonus/Dsp/GEQSourceProviders.cpp
  src/Presonus/Dsp/GEQParameterList.cpp
  src/Presonus/Dsp/GateSourceProviders.cpp
  src/Presonus/Dsp/GateParameterList.cpp
  src/Presonus/NOAA/TCardRouterGeqInputRoutes.cpp
  src/Presonus/NOAA/TCardRouterBusRoutes.cpp
  src/Presonus/Dsp/CompressorSourceProviders.cpp
  src/Presonus/Dsp/CompressorParameterList.cpp
  src/Presonus/NOAA/TCardUCNetHandlerIO.cpp
  src/Presonus/NOAA/TCardHandlerLifecycle.cpp
  src/Presonus/NOAA/TCardHandlerProperties.cpp
  src/Presonus/NOAA/TCardHandlerRelease.cpp
  src/Presonus/NOAA/TCardLifecycle.cpp
  src/Presonus/NOAA/TCardSerial.cpp
  src/Presonus/NOAA/TCardHandlerEvents.cpp
  src/Presonus/NOAA/TCardHandlerEventQueue.cpp
  src/Presonus/NOAA/TCardFPGAUpdater.cpp
  src/Presonus/NOAA/TCardRouterRoutes.cpp
  src/Presonus/NOAA/TCardReceive.cpp
  src/Presonus/NOAA/TCardStart.cpp
  src/Presonus/Dsp/FilterParameterLists.cpp
  src/Presonus/NOAA/TCardDiagnostics.cpp
  src/Presonus/NOAA/TCardRate.cpp
  src/Presonus/Dsp/Eq8LimiterParameterLists.cpp
  src/Presonus/NOAA/TCardCommands.cpp
  src/Presonus/NOAA/TCardResources.cpp
  src/Presonus/NOAA/TCardStatus.cpp
  src/Presonus/Dsp/EqParameterLists.cpp
  src/Presonus/NOAA/TCardSetup.cpp
  src/Presonus/NOAA/TCardState.cpp
  src/Presonus/Mixer/BeastSetupProperty.cpp
  src/Presonus/Mixer/GambitSetupProperty.cpp
  src/Presonus/Mixer/RogueSetupProperty.cpp
  src/Presonus/Mixer/StormSetupProperty.cpp
  src/Presonus/Mixer/WolverineSetupProperty.cpp
  src/Presonus/NOAA/TCardRouterOpen.cpp
  src/Presonus/Dsp/ParamDescriptorList.cpp
  src/Presonus/NOAA/TCardRouterLookups.cpp
  src/portable/noaa/BeastRouterSlots.cpp
  src/portable/noaa/GambitRouterSlots.cpp
  src/portable/noaa/RogueRouterSlots.cpp
  src/portable/noaa/StormRouterSlots.cpp
  src/portable/noaa/WolverineRouterSlots.cpp
  src/Presonus/NOAA/TCardRouterControl.cpp
  src/Presonus/UC/PacketQueueOperations.cpp
  src/Presonus/NOAA/TCardRouterCommands.cpp
  src/Presonus/UC/DicePacketQueueLifetime.cpp
  src/portable/noaa/RouterLookupImage.cpp
  src/mixer_dsp/EQTypeConversions.cpp
  src/DSP/BiquadCalcConstructor.cpp
  src/DSP/SinglePole.cpp
  src/Presonus/NOAA/SysexReceiver.cpp
  src/Presonus/NOAA/TCardSPIService.cpp
  src/Presonus/NOAA/SysexPacketConstruction.cpp
  src/Presonus/NOAA/TCardSPIPackets.cpp
  src/Presonus/NOAA/SysexPacketLog.cpp
  src/Presonus/NOAA/SysexReceiverWait.cpp
  src/Presonus/UC/DicePacketQueue.cpp
  src/mixer_dsp/FilterControllers.cpp
  src/Presonus/Mixer/AliasMapping.cpp
  src/Presonus/Mixer/ChannelDCAComponent.cpp
  src/Presonus/Mixer/ParamLink.cpp
  src/Presonus/TargetedComponent.cpp
)
set(PRESONUS_PUBLIC_HEADERS
  presonus/DAWClientComponent.hpp
  presonus/uc/ServerRootComponent.hpp
  presonus/DAWFocusChannel.hpp
  presonus/mixer_dsp/EQ4Controller.hpp
  presonus/mixer_dsp/EQ5Controller.hpp
  presonus/DAWChannel.hpp
  presonus/DAWChannelGroup.hpp
  presonus/DAWDeviceFolder.hpp
  presonus/DAWDeviceSlot.hpp
  presonus/uc/ClientRootComponent.hpp
  presonus/DynamicsControl.hpp
  presonus/dsp/LimiterController.hpp
  presonus/mixer/DCALevelHandler.hpp
  presonus/uc/Celsius.hpp
  presonus/uc/ChannelNameFormatter.hpp
  presonus/uc/discovery_attributes.hpp
  presonus/uc/param_range.hpp
  presonus/uc/server_implementation.hpp
  presonus/panel/meter_level_control.hpp
  presonus/panel/meter_peak_control.hpp
  presonus/uc/element.hpp
  presonus/uc/meta_element.hpp
  presonus/uc/midi_endpoint.hpp
  presonus/uc/midi_endpoint_registry.hpp
  presonus/uc/remote_event_sender.hpp
  presonus/uc/server_description.hpp
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
  presonus/surface/MidiMixerHandler.hpp
  presonus/SLChannel.hpp
  presonus/panel/FieldElement.hpp
  presonus/panel/OffscreenElement.hpp
  presonus/MeterManagerBase.hpp
  presonus/panel/LCDManager.hpp
  presonus/panel/Page.hpp
  presonus/panel/TextEntryElement.hpp
  presonus/panel/MixerLCD.hpp
  presonus/ModalPageComponent.hpp
  presonus/PageComponent.hpp
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
  presonus/surface/ChannelInfoPageComponent.hpp
  presonus/surface/MixSettingsPageComponent.hpp
  presonus/panel/AlertBook.hpp
  presonus/panel/PanelParameterTables.hpp
  presonus/surface/FatChannelClipboard.hpp
  presonus/surface/ScenesPageComponent.hpp
  presonus/surface_update/FirmwareUpdateComponent.hpp
  presonus/dsp/OMAPTargetHandler.hpp
  presonus/surface/PageParam.hpp
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
  presonus/LinkableComponent.hpp
  presonus/panel/FXPage.hpp
  presonus/panel/WolverinePanelRegistrar.hpp
  presonus/panel/GEQPage.hpp
  presonus/mixer/WolverineRMLApplication.hpp
  presonus/mixer/GambitRMLApplication.hpp
  presonus/surface/ControlName.hpp
  presonus/mixer/ControlMapping.hpp
  presonus/mixer/ReverbComponent.hpp
  presonus/mixer/GambitMixerComponent.hpp
  presonus/FocusRestorer.hpp
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
  presonus/uc/ClientSubscription.hpp
  presonus/dsp/IController.hpp
  presonus/dsp/ControllerInfo.hpp
  presonus/panel/Element.hpp
  presonus/MappableMixer.hpp
  presonus/link/Messenger.hpp
  presonus/panel/SharedMemoryComm.hpp
  presonus/color/IColorConverter.hpp
  presonus/color/MixerColorConverter.hpp
  presonus/surface/GroupsPageComponent.hpp
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
  presonus/panel/PanelComponent.hpp
  presonus/mixer/AVBCascadeManager.hpp
  presonus/avb/AvbComponent.hpp
  presonus/PanControl.hpp
  presonus/MuteGroupBase.hpp
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
  presonus/IBackgroundGridProvider.hpp
  presonus/GridPainter.hpp
  presonus/surface/sl_mixer_encoder.hpp
  presonus/surface/IDisplayPort.hpp
  presonus/surface/DisplayManager.hpp
  presonus/panel/SPIControlGroup.hpp
  presonus/panel/PresetNameManager.hpp
  presonus/mixer/OutputComponent.hpp
  presonus/dsp/RuntimeGlobals.hpp
  presonus/dsp/Controller.hpp
  presonus/AliasComponent.hpp
  presonus/DspComponent.hpp
  presonus/MappingTable.hpp
  presonus/MackieControlModel.hpp
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
  presonus/mixer/SceneFilter.hpp
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
  presonus/pcm4104/Pcm4104Spi.hpp
  presonus/DAWTimeInfo.hpp
  presonus/panel/Book.hpp
  presonus/panel/BeastPanelRegistrar.hpp
  presonus/panel/uart_led_state_token.hpp
  presonus/panel/lcd_display_control.hpp
  presonus/panel/temperature_control.hpp
  presonus/panel/uart_message_sender.hpp
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
  presonus/uc/server.hpp
  presonus/dice/programmer_device_services.hpp
  presonus/uc/connection_handler.hpp
  presonus/dice/programmer_services.hpp
  presonus/uc/server_registrar.hpp
  presonus/dice/manager_services.hpp
  presonus/uc/network_manager_services.hpp
  presonus/dsp/biquad_calc.hpp
  presonus/dsp/single_pole.hpp
  presonus/panel/pot_fader_control.hpp
  presonus/uc/file_transfer_manager.hpp
  presonus/panel/switch_control.hpp
  presonus/noaa/spi_service.hpp
  presonus/uc/file_server_service.hpp
  presonus/embedded_efm/efm_control_dispatch.hpp
  presonus/uc/file_transfer.hpp
  presonus/mcu/panel_protocol.hpp
  presonus/mcu/update_loop.hpp
  presonus/embedded_efm/efm_parameter_fields.hpp
  presonus/embedded_efm/efm_packed_parameters.hpp
  presonus/embedded_efm/efm_packet_checks.hpp
  presonus/embedded_efm/efm_version_packet.hpp
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
  presonus/avb/protocol.hpp
  presonus/avb/receive_services.hpp
  presonus/avb/streams.hpp
  presonus/core_uc/buffer.hpp
  presonus/dice/codec.hpp
  presonus/dice/manager.hpp
  presonus/dice/packet_services.hpp
  presonus/dice/programmer.hpp
  presonus/dice/response_services.hpp
  presonus/dice/response_wait_detail.hpp
  presonus/dice/sysex.hpp
  presonus/embedded_dice/mix.hpp
  presonus/mixer_dsp/FilterControllers.hpp
  presonus/mixer_state/MixerState.hpp
  presonus/noaa/sysex_receiver.hpp
  presonus/surface_panel/BitmapDrawing.hpp
  presonus/surface_panel/ControlGroup.hpp
  presonus/surface_panel/DigitalPotControl.hpp
  presonus/panel/registrar_group_registry.hpp
  presonus/surface_panel/DbTable.hpp
  presonus/surface_panel/InputPin.hpp
  presonus/surface_panel/LEDState.hpp
  presonus/surface_panel/MeterControl.hpp
  presonus/surface_panel/OutputPin.hpp
  presonus/uc/DicePacketQueue.hpp
  presonus/uc/abi32.hpp
  presonus/uc/basic_connection.hpp
  presonus/uc/ccl_bindings.hpp
  presonus/uc/connection.hpp
  presonus/uc/connection_receive.hpp
  presonus/uc/discovery_events.hpp
  presonus/uc/event_dispatcher.hpp
  presonus/uc/event_factory.hpp
  presonus/uc/event_queue.hpp
  presonus/uc/events.hpp
  presonus/uc/external_connection.hpp
  presonus/uc/file_control_events.hpp
  presonus/uc/file_data_events.hpp
  presonus/uc/meter_events.hpp
  presonus/uc/misc_events.hpp
  presonus/uc/network.hpp
  presonus/uc/no_member_events.hpp
  presonus/uc/parameter_events.hpp
  presonus/uc/primitive_dispatch.hpp
  presonus/uc/protocol.hpp
  presonus/uc/socket_channel.hpp
  presonus/uc/transport_events.hpp
  presonus/uc/typed_factory_codec.hpp
  presonus/IFaderUnit.hpp
  presonus/TargetedComponent.hpp
  presonus/ThroughputTest.hpp
  presonus/mixer/AliasMapping.hpp
  presonus/mixer/ChannelDCAComponent.hpp
  presonus/mixer/DigitalInputComponent.hpp
  presonus/mixer/FXComponent.hpp
  presonus/mixer/MixerComponentBaseDelegate.hpp
  presonus/mixer/ParamLink.hpp
  presonus/panel/Fat24FrontPanelComponent.hpp
  presonus/surface/AssignEditPageComponent.hpp
  presonus/surface/CalibrateTouchComponent.hpp
  presonus/surface/ChannelPresetsPageComponent.hpp
  presonus/surface/FirmwarePageComponent.hpp
  presonus/surface/GeqPresetsPageComponent.hpp
  presonus/surface/LockoutPageComponent.hpp
  presonus/surface/MainScreenComponent.hpp
  presonus/surface/PreampsPageComponent.hpp
  presonus/surface/StChannelSettingsPageComponent.hpp
)

# These ports use the pinned CCL core_cast/type-info provider, not C++ RTTI.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/TalkbackInputComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/TransportHandler.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/FXEditPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/FXHomePageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/FxPresetsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/TBRoutingPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/MicLineComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-fast-math -ffp-contract=off)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/GambitPanelComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation -fno-rtti -fno-lto)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/WolverinePanelComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation -fno-rtti -fno-lto)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/BeastMixerComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/StormMixerComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -O0 -fno-sized-deallocation)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/MonoMainComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/TapeInputComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DisplayManagerInstance.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/IFaderUnit.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MainLCDComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/AutoFilterGroupManager.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/ChannelDCAComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/InputComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/ChannelPresetComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/AssignEditPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/CalibrateTouchComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/CapturePageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/ChannelInfoPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/ChannelPresetsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/FirmwarePageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/GeqPresetsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/GroupsEditPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/LockoutPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MainScreenComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/PreampsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/PresetsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/ScenesPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/StChannelSettingsPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/TargetedComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Root-review: actual worker per-TU RTTI/deallocation behavior options.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/ThroughputTest.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation -fno-rtti)

# Derived portable vtables follow the existing no-RTTI key-destructor providers.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/AutoFilterGroupManager.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/ChannelDCAComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/Fat24FrontPanelComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/RogueFrontPanelComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
# Native deleting destructors for both source ports invoke operator delete(void*).
set_property(SOURCE
  "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/LinkableComponent.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/DspComponent.cpp"
  APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DefaultMeterInterpolator.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/LPFControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/ColorButton.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/IconManager.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/SoloPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

# Keep the scoped production compile options of these recovered CCL classes.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/EQComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/FXComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/GEQComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/GateComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/HPFilterComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/LPFilterComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/LimiterComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/ScenesPageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/MappingComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/SLMixerEncoder.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DefaultMeterInterpolator.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/StormFrontPanelComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-rtti -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/Element.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Surface/DAWMixerHandler.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MeterBallistics.cpp" APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off -fno-fast-math)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/ChHPFFormatter.cpp" APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/FillElement.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Panel/StaticElement.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-sized-deallocation)

# Per-source compile requirements established by the exact native/provider replays.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MeterBallistics.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/MeterMaid.cpp" APPEND PROPERTY COMPILE_OPTIONS -ffp-contract=off -fno-fast-math -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/EarlyRefFormatterT3.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/PreDelayFormatterT3.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/PreDelayFormatterT4.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/PageComponent.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/surface_panel/DigitalPotControl.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

# Match the non-RTTI DecayTimeFormatter base in the canonical common role.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT1.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT2.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT3.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT4.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT5.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT6.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT7.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT8.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT9.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

# Match the exact original unsized D0 deallocation paths.
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT1.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT2.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT3.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT4.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT5.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT6.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT7.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT8.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/DecayTimeFormatterT9.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/EarlyRefFormatterT2.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/Mixer/PreDelayFormatterT2.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/surface_panel/ControlHelpers.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-sized-deallocation)

set_property(SOURCE src/Presonus/DynamicsControl.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)

set_property(SOURCE src/Presonus/Mixer/DCALevelHandler.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-sized-deallocation)

set_property(SOURCE src/Presonus/Dsp/LimiterController.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-rtti -fno-fast-math -ffp-contract=off -fno-sized-deallocation)

set_property(SOURCE src/Presonus/UC/Format/Celsius.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
set_property(SOURCE src/Presonus/UC/Format/ChannelNameFormatter.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-sized-deallocation)

set_property(SOURCE src/Presonus/DAWDeviceFolder.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-rtti -fno-sized-deallocation)

set_property(SOURCE src/Presonus/DAWDeviceSlot.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-rtti -fno-sized-deallocation)

set_property(SOURCE src/Presonus/Dsp/EQ4Controller.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-fast-math -ffp-contract=off)
set_property(SOURCE src/Presonus/Dsp/EQ5Controller.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-rtti -ffp-contract=off -fno-sized-deallocation)
set_property(SOURCE src/Presonus/DAWFocusChannel.cpp APPEND PROPERTY COMPILE_OPTIONS -std=c++20 -fno-rtti)

set_property(SOURCE src/Presonus/DAWClientComponent.cpp APPEND PROPERTY COMPILE_OPTIONS -Ulinux -fno-rtti -fno-lto -ffunction-sections -fdata-sections)


set_property(SOURCE src/Presonus/UC/ServerRootComponent.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -std=c++20 -fno-lto -fno-fast-math -ffp-contract=off)

set_property(SOURCE src/application/SurfaceApplicationSkinDirectory.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto)
set_property(SOURCE src/Presonus/Surface/FatChannelClipboardSelection.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-rtti)
