# Canonical production organization audit

Read-only inventory; no production migration or readiness promotion claimed.

Tracked inventory index: `INVENTORY_INDEX.json`; complete hash-bound local inventory: `INVENTORY.json`. It records compiler-observed declarations and definitions, direct/transitive consumers, current SQLite original identities/proof links, build partitions, active claims, owners and proposed destinations. Forty existing compiler observations were reused with audited source hash checks; no reconstruction or compiler refresh was repeated.

## Migration map

| Current file | Canonical destinations | Boundary/risk |
| --- | --- | --- |
| `include/presonus/frontier01/frontier01_w01.hpp` | `include/presonus/MixerSceneLoader.hpp`<br>`include/presonus/panel/FxPresetComponent.hpp`<br>`include/presonus/panel/SPIControl.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/frontier01/frontier01_w02.hpp` | `include/presonus/mixer/FXBusComponent.hpp`<br>`include/presonus/mixer/GEQLinkHandler.hpp`<br>`include/presonus/mixer/GlobalComponent.hpp`<br>`include/presonus/mixer/RackMixerComponent.hpp`<br>`include/presonus/mixer/SendOutputComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/frontier01/frontier01_w03.hpp` | `include/presonus/AllMutesGroup.hpp`<br>`include/presonus/FileMuteGroup.hpp`<br>`include/presonus/FocusHelperButton.hpp`<br>`include/presonus/McuVpotControl.hpp`<br>`include/presonus/PotControl.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/frontier01/frontier01_w04.hpp` | `include/presonus/FaderUnitComponent.hpp`<br>`include/presonus/MackieControlComponent.hpp`<br>`include/presonus/MackieControlExtender.hpp`<br>`include/presonus/surface/AudioUtilitiesPage.hpp`<br>`include/presonus/surface/FaderUtilitiesPage.hpp`<br>`include/presonus/surface/StartPageComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/rank20cycle01/rank20c01_w02.hpp` | `include/presonus/MackieControlUnit.hpp` | active claims require owner reconciliation |
| `include/presonus/rank20cycle01/rank20c01_w04.hpp` | `include/presonus/surface/DAWLoadDocumentPage.hpp` | active claims require owner reconciliation |
| `include/presonus/rank20cycle01/rank20c01_w05.hpp` | `include/presonus/mixer/FilterGroupManager.hpp` | active claims require owner reconciliation |
| `include/presonus/rank20cycle01/rank20c01_w06.hpp` | `include/presonus/GridPainter.hpp` | active claims require owner reconciliation |
| `include/presonus/reconstruction200/large01_w01.hpp` | `include/presonus/avb/SurfaceAvbComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w02.hpp` | `include/presonus/MackieControlModel.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w03.hpp` | `include/presonus/mixer_dsp/Dsp.hpp`<br>`include/presonus/mixer_dsp/EQControl.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w04.hpp` | `include/presonus/surface/AssignmentHandlerTable.hpp`<br>`include/presonus/surface/DAWMixerHandler.hpp`<br>`include/presonus/surface/MappingComponent.hpp`<br>`include/presonus/surface/PresetsPageComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w05.hpp` | `include/presonus/IDAWTimeInfo.hpp`<br>`include/presonus/surface/TransportHandler.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w06.hpp` | `include/presonus/ColorMapping.hpp`<br>`include/presonus/DisplayCommandList.hpp`<br>`include/presonus/SpectrumPainter.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w07.hpp` | `include/presonus/surface/ScribbleStripController.hpp`<br>`include/presonus/surface/SurfaceChannelComponent.hpp`<br>`include/presonus/surface/SurfaceInputComponent.hpp`<br>`include/presonus/surface/SurfaceOutputComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w08.hpp` | `include/presonus/mixer/AudioSetup.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w09.hpp` | `include/presonus/surface/DAWDialogHandler.hpp`<br>`include/presonus/surface/MarkerPageComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large01_w10.hpp` | `include/presonus/panel/PanelRegistrar.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w01.hpp` | `include/presonus/surface/sl_mixer_encoder.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w03.hpp` | `include/presonus/dsp/Controller.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w04.hpp` | `include/presonus/mixer/AVBRemoteMixerHandler.hpp`<br>`include/presonus/mixer_state/MixerState.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w05.hpp` | `include/presonus/avb/ComponentResource.hpp`<br>`include/presonus/uc/ServerComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w06.hpp` | `include/presonus/panel/ChannelPresetComponent.hpp`<br>`include/presonus/panel/GeqPresetComponent.hpp`<br>`include/presonus/panel/ScenesComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w07.hpp` | `include/presonus/surface/MixerPageComponent.hpp`<br>`include/presonus/surface/SubAssignPageComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w08.hpp` | `include/presonus/MeterScaleControl.hpp`<br>`include/presonus/surface/MuteGroupsComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w09.hpp` | `include/presonus/VUMeterControl.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/reconstruction200/large02_w10.hpp` | `include/presonus/surface_panel/ControlHelpers.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/trial08/DspComponent.hpp` | `include/presonus/DspComponent.hpp`<br>`include/presonus/dsp/IController.hpp`<br>`include/presonus/dspcomponent_port.hpp` | active claims require owner reconciliation |
| `include/presonus/trial08/FXPresetRecallComponent.hpp` | `include/presonus/panel/FXPresetRecallComponent.hpp`<br>`include/presonus/panel/PresetNameCache.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/trial08/MainLCDComponent.hpp` | `include/presonus/LcdView.hpp`<br>`include/presonus/MainLCDComponent.hpp`<br>`include/presonus/PageComponent.hpp` | active claims require owner reconciliation |
| `include/presonus/trial08/MixerComponent.hpp` | `include/presonus/mixer/MixerComponent.hpp` | Root-controlled group; verify consumers before editing |
| `include/presonus/trial08/MixerComponentBase.hpp` | `include/presonus/mixer/ChannelComponent.hpp`<br>`include/presonus/mixer/PermissionsComponent.hpp` | active claims require owner reconciliation |
| `include/presonus/trial08/StormFrontPanelComponent.hpp` | `include/presonus/StormMixSceneComponent.hpp`<br>`include/presonus/StormMuteGroupComponent.hpp`<br>`include/presonus/mixer/ChannelComponent.hpp`<br>`include/presonus/panel/MixerLCD.hpp`<br>`include/presonus/panel/StormFrontPanelComponent.hpp` | active claims require owner reconciliation |
| `src/Presonus/DAWTimeInfoTrial08.cpp` | `src/Presonus/DAWTimeInfo.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/DspComponentTrial08.cpp` | `src/Presonus/DspComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/EQControlTrial08.cpp` | `src/Presonus/EQControl.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/MackieControlModelTrial08.cpp` | `src/Presonus/MackieControlModel.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/MainLCDComponentTrial08.cpp` | `src/Presonus/MainLCDComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/MappingTableTrial08.cpp` | `src/Presonus/MappingTable.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/Mixer/MixerComponentBaseTrial08.cpp` | `src/Presonus/CompletionHandler.cpp`<br>`src/Presonus/Mixer/MixerComponentBase.cpp`<br>`src/Presonus/SaveSceneTask.cpp`<br>`src/Presonus/StorageCompletionHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/Mixer/MixerComponentTrial08.cpp` | `src/Presonus/Mixer/MixerComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/Panel/FXPresetRecallComponentTrial08.cpp` | `src/Presonus/Panel/FXPresetRecallComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/Panel/StormFrontPanelComponentTrial08.cpp` | `src/Presonus/Panel/StormFrontPanelComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/frontier01/frontier01_w01.cpp` | `src/Presonus/MixerSceneLoader.cpp`<br>`src/Presonus/Panel/FxPresetComponent.cpp`<br>`src/Presonus/Panel/PresetComponent.cpp`<br>`src/Presonus/Panel/PresetNameManager.cpp`<br>`src/Presonus/Panel/SPIControl.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/frontier01/frontier01_w02.cpp` | `src/Presonus/Mixer/GEQLinkHandler.cpp`<br>`src/Presonus/Mixer/GlobalComponent.cpp`<br>`src/Presonus/Mixer/RackMixerComponent.cpp`<br>`src/Presonus/Mixer/SendOutputComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/frontier01/frontier01_w03.cpp` | `src/Presonus/AllMutesGroup.cpp`<br>`src/Presonus/FileMuteGroup.cpp`<br>`src/Presonus/FocusHelperButton.cpp`<br>`src/Presonus/McuVpotControl.cpp`<br>`src/Presonus/PotControl.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/frontier01/frontier01_w04.cpp` | `src/Presonus/FaderUnitComponent.cpp`<br>`src/Presonus/MackieControlComponent.cpp`<br>`src/Presonus/MackieControlExtender.cpp`<br>`src/Presonus/MackieControlModel.cpp`<br>`src/Presonus/Surface/AudioUtilitiesPage.cpp`<br>`src/Presonus/Surface/FaderUtilitiesPage.cpp`<br>`src/Presonus/Surface/MidiMixerHandler.cpp`<br>`src/Presonus/Surface/StartPageComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/frontier02/frontier02_w05.cpp` | `src/Presonus/Mixer/FXBusComponent.cpp`<br>`src/Presonus/Mixer/GlobalComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/rank20cycle01/rank20c01_w01.cpp` | `src/Presonus/Mixer/OutputComponent.cpp` | active claims require owner reconciliation |
| `src/Presonus/rank20cycle01/rank20c01_w02.cpp` | `src/Presonus/MackieControlUnit.cpp`<br>`src/Presonus/MeterControl.cpp` | active claims require owner reconciliation |
| `src/Presonus/rank20cycle01/rank20c01_w04.cpp` | `src/Presonus/Surface/DAWLoadDocumentPage.cpp`<br>`src/Presonus/Surface/DAWMixerHandler.cpp`<br>`src/Presonus/Surface/SLMixerHandler.cpp` | active claims require owner reconciliation |
| `src/Presonus/rank20cycle01/rank20c01_w05.cpp` | `src/Presonus/Mixer/FilterGroupManager.cpp` | active claims require owner reconciliation |
| `src/Presonus/rank20cycle01/rank20c01_w06.cpp` | `src/Presonus/GridPainter.cpp`<br>`src/Presonus/MappingTable.cpp`<br>`src/Presonus/Panel/PanelComponent.cpp` | active claims require owner reconciliation |
| `src/Presonus/reconstruction200/large01_w01.cpp` | `src/Presonus/AVB/AvbComponent.cpp`<br>`src/Presonus/AVB/SurfaceAvbComponent.cpp`<br>`src/Presonus/Mixer/NetworkSetupComponent.cpp`<br>`src/Presonus/Surface/NetworkSetupComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w02.cpp` | `src/Presonus/IFaderPanel.cpp`<br>`src/Presonus/MackieControlComponent.cpp`<br>`src/Presonus/MackieControlModel.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w03.cpp` | `src/Presonus/Dsp/EQController.cpp`<br>`src/Presonus/Dsp/ShelbyGEQController.cpp`<br>`src/Presonus/EQControl.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w04.cpp` | `src/Presonus/AssignmentHandlerTable.cpp`<br>`src/Presonus/Surface/DAWMixerHandler.cpp`<br>`src/Presonus/Surface/EQPageComponent.cpp`<br>`src/Presonus/Surface/GeqPageComponent.cpp`<br>`src/Presonus/Surface/MappingComponent.cpp`<br>`src/Presonus/Surface/PresetsPageComponent.cpp`<br>`src/Presonus/Surface/SLMixerHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w05.cpp` | `src/Presonus/DAWTimeInfo.cpp`<br>`src/Presonus/IDAWTimeInfo.cpp`<br>`src/Presonus/Surface/TransportHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w06.cpp` | `src/Presonus/ColorMapping.cpp`<br>`src/Presonus/DisplayCommandList.cpp`<br>`src/Presonus/SpectrumPainter.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w07.cpp` | `src/Presonus/Surface/ScribbleStripController.cpp`<br>`src/Presonus/Surface/SurfaceChannelComponent.cpp`<br>`src/Presonus/Surface/SurfaceInputComponent.cpp`<br>`src/Presonus/Surface/SurfaceOutputComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w08.cpp` | `src/Presonus/Mixer/BeastApplication.cpp`<br>`src/Presonus/Mixer/GambitApplication.cpp`<br>`src/Presonus/Mixer/RogueApplication.cpp`<br>`src/Presonus/Mixer/StormApplication.cpp`<br>`src/Presonus/Mixer/WolverineApplication.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w09.cpp` | `src/Presonus/Surface/DAWDialogHandler.cpp`<br>`src/Presonus/Surface/DawFxPageComponent.cpp`<br>`src/Presonus/Surface/MarkerPageComponent.cpp`<br>`src/Presonus/Surface/MidiMixerHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large01_w10.cpp` | `src/Presonus/Panel/FrontPanelComponent.cpp`<br>`src/Presonus/Panel/PanelRegistrar.cpp`<br>`src/Presonus/Surface/PanelRegistrar.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w01.cpp` | `src/Presonus/Surface/EQPageComponent.cpp`<br>`src/Presonus/Surface/SLMixerHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w02.cpp` | `src/Presonus/Panel/FrontPanelComponent.cpp`<br>`src/Presonus/Panel/PanelComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w03.cpp` | `src/Presonus/Dsp/EQController.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w04.cpp` | `src/Presonus/Mixer.cpp`<br>`src/Presonus/Mixer/AVBCascadeManager.cpp`<br>`src/Presonus/Mixer/AVBRemoteMixerHandler.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w05.cpp` | `src/Presonus/AVB/AvbComponent.cpp`<br>`src/Presonus/UC/ServerComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w06.cpp` | `src/Presonus/Panel/ChannelPresetComponent.cpp`<br>`src/Presonus/Panel/FxPresetComponent.cpp`<br>`src/Presonus/Panel/GeqPresetComponent.cpp`<br>`src/Presonus/Panel/ScenesComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w07.cpp` | `src/Presonus/Surface/MixerPageComponent.cpp`<br>`src/Presonus/Surface/SubAssignPageComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w08.cpp` | `src/Presonus/MeterControl.cpp`<br>`src/Presonus/MeterScaleControl.cpp`<br>`src/Presonus/PanControl.cpp`<br>`src/Presonus/Surface/MuteGroupsComponent.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w09.cpp` | `src/Presonus/VUMeterControl.cpp` | Root-controlled group; verify consumers before editing |
| `src/Presonus/reconstruction200/large02_w10.cpp` | `src/Presonus/Surface/PanelRegistrar.cpp`<br>`src/Presonus/Surface/SurfaceRootComponent.cpp` | Root-controlled group; verify consumers before editing |

## Ordering and proof preservation

1. Confirm no live writers; preserve all active claims and research output. Existing instruction mismatch is an actual gate failure, not a waived warning.
2. Begin with a principal-class migration such as VUMeterControl; record old/new hashes and trash moves. Split mixed files by class, merging existing canonical definitions, never rebuilding already implemented functions.
3. Introduce an explicit exact-path debt inventory and preflight guard. New batch/worker/trial production paths or dependencies on candidates/scratch must fail. No automatic widening of exceptions.
4. Retain old proofs unchanged. Generate fresh affected proofs and run all existing canonical gates before admission/commit. Every migration commit is organizational change, not new reconstruction or readiness credit.
5. Reconcile older active claims before claimed-path groups. Refresh affected graph inputs and prepare new instruction-bound packets before implementation resumes.

## Open audit limitations

Destination proposals still require per-group semantic review of related helper placement and exact split boundaries. The inventory is not edit authorization or a proof of complete transitive runtime behavior. Current compiler input closures and literal include closures are recorded separately. Historical research artifacts are retained; source/API findings do not inherit freshness after a move.
