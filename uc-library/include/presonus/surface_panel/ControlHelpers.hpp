#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/pot_fader_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/switch_control.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
struct Touchscreen_Type;
namespace Core::Portable {
class SettingFile;
}

// Portable class declarations for the evidenced methods only. These do
// not reproduce original inheritance, object storage, vtables or ARM32 layouts.
namespace presonus::panel_binding {
struct RegistrarGroupRegistry;
struct SevenSegControlAccess;
} // namespace presonus::panel_binding
namespace Presonus {
struct TouchInputEvent;
class WIFIManager;
} // namespace Presonus
namespace Presonus::Panel {
class EncoderControl;
class ControlGroup;
class ControlRegistrar {
public:
  // Portable callback interface with the observed typed virtual defaults.
  // Original return declarations and vtable layout remain unresolved.
  class Delegate {
  public:
    // Portable default callback; the original return and dispatch declarations
    // remain unresolved.
    void controlChanged(const ControlRegistrar &, unsigned char,
                        unsigned char *);
    void encoderChanged(const ControlRegistrar &, int, int, EncoderControl *);
    void lineSenseChanged(const ControlRegistrar &, int, int);
    void faderSensitivityReported(const ControlRegistrar &, int);
    void faderSpeedReported(const ControlRegistrar &, int);
    void faderStatusChanged(const ControlRegistrar &, int, unsigned char,
                            FaderControl *);
    virtual void faderChanged(const ControlRegistrar &, int, int,
                              FaderControl *);
    virtual void switchChanged(const ControlRegistrar &, int, int, bool,
                               SwitchControl *);
    virtual void potChanged(const ControlRegistrar &, int, int, PotControl *);
    virtual void screenTouched(const ControlRegistrar &, TouchInputEvent);
  };

  // Independent borrowed setup only; original lifecycle/layout unresolved.
  ControlRegistrar() = default;
  explicit ControlRegistrar(
      presonus::panel_binding::RegistrarGroupRegistry &state)
      : groupRegistry_(&state) {}
  // Source-port virtual binding, not the original abstract vtable/layout.
  // Standalone count/at clients remain constructible; operational messaging
  // requires an explicit borrowed port binding. An explicitly bound null port
  // retains the original conditional no-send behavior.
  virtual ~ControlRegistrar() = default;
  void bindPort(Presonus::IPanelPort *port) {
    port_ = port;
    portBound_ = true;
  }
  virtual Presonus::IPanelPort *getPort() const {
    if (!portBound_)
      throw std::logic_error("ControlRegistrar port is not bound");
    return port_;
  }
  // Direct source-port defaults. Original return and dispatch remain pending.
  void handleMovingFaderMcuStatus(unsigned char, unsigned char, unsigned char);
  void handleKeyValue(unsigned char, unsigned short);
  void init();
  void handleVersion(int, Uart_Msg_Type &);
  void *castTo(int id);
  bool sourcePortInitialized() const { return initialized_; }
  std::uint32_t sourcePortVersion() const { return version_; }
  virtual void writeDualMsg(Uart_Msg_Type &);
  virtual void setAllLeds(bool);
  virtual void setAllMeters(bool);
  virtual void scanSurface();
  virtual void scanFaders();
  virtual void scanSwitches();
  void handleGlobalResponse(int, Uart_Msg_Type &);
  // Original return spellings are unencoded; these are portable declarations.
  int count() const;
  ControlGroup *at(int index) const;
  // Original nested enum identity is encoded in the method's mangled name.
  // Original enumerator names/range/underlying declaration are unresolved;
  // the portable int32 domain preserves the observed ARM register behavior.
  enum ControlType : int {};

private:
  Presonus::IPanelPort *port_ = nullptr;
  bool portBound_ = false;
  bool initialized_ = false;
  std::uint32_t version_ = 0;
  presonus::panel_binding::RegistrarGroupRegistry *groupRegistry_ = nullptr;
};
class SevenSegControl : public Control {
public:
  SevenSegControl();
  explicit SevenSegControl(int tag);
  ~SevenSegControl() override;
  // The ARM implementation returns a zero-extended 16-bit bitmap. Its exact
  // original C++ return declaration is not encoded in the symbol name.
  std::uint16_t convertCharToBmp(char character, bool decimalPoint) const;

private:
  // Portable storage for the per-digit bitmaps initialized by the constructor.
  std::array<std::uint16_t, 2> digitBitmaps_{};
  friend struct presonus::panel_binding::SevenSegControlAccess;
};
} // namespace Presonus::Panel
namespace Presonus {
class IPanelPort;
}
namespace presonus::surface {
// Independent borrowed live port selection, not original registrar fields.
// Independent boundary for unrecovered original registrar virtual services.
// Required callbacks are live operations, not fallback no-op providers.
struct RegistrarServices {
  void *context;
  void (*send)(void *, Uart_Msg_Type &);
  void (*testMode)(void *, bool);
  void (*touchscreen)(void *, Touchscreen_Type &);
  Presonus::Panel::IPanelIO *io;
};
struct RegistrarTestState {
  explicit RegistrarTestState(RegistrarServices value) : services(value) {}
  RegistrarServices services;
  Presonus::DelayTimer touchTimer{0}, rgbTimer{0}, scribbleTimer{0};
  bool touchscreen = false, scribble = false, rgb = false, controls = false;
  unsigned char color = 0;
  std::array<std::uint32_t, 22> controlValues{};
  std::array<unsigned char, 19> switchValues{};
  std::vector<std::unique_ptr<Presonus::Panel::ControlGroup>> groups;
  std::vector<std::unique_ptr<Presonus::Panel::SwitchControl>> switches;
};
struct PanelRegistrarCommandState {
  Presonus::IPanelPort *port = nullptr;
};
} // namespace presonus::surface
namespace Presonus::Surface {
class MainScreenComponent;
class MappingComponent;
class NetworkSetupComponent;
class MidiMixerHandler;
} // namespace Presonus::Surface
namespace presonus::surface {
// Unrecovered application service boundaries; no fabricated class definition.
// Explicit borrowed typed-reference attestations; no MainScreen definition,
// fabricated inheritance or native object-layout interpretation is needed.
struct MainScreenReference {
  Core::Portable::Component *component = nullptr;
  Presonus::Surface::MainScreenComponent *reference = nullptr;
  std::string elfSha256;
  std::string nativeType;
  std::uint32_t nativeTypeAddress = 0;
};
// Independent source-port data for only the observed downstream label and
// alternate-parameter effects. These are NOT recovered original fields/layout.
struct FocusInfoState {
  Core::CString32 label;
  Core::Portable::Parameter *alternateOriginal = nullptr;
};
} // namespace presonus::surface
namespace Presonus {
// Portable carrier required by the actual existing virtual interface. The
// original FocusInfo declaration, field names, layout and ARM ABI stay unknown.
struct MixerAssignmentHandler::FocusInfo {
  presonus::surface::FocusInfoState sourcePort;
};
} // namespace Presonus
namespace presonus::surface {
struct FocusState {
  Core::Portable::AliasParam *alias = nullptr;
  Core::Portable::StringParam *label = nullptr;
  Core::Vector<Presonus::AssignmentHandler *> *handlers = nullptr;
};
struct RootServices {
  // Borrowed real CCL ports; independent storage, not original member layout.
  Core::Portable::Component *rootParameters = nullptr;
  Core::Portable::IParamObserver *observer = nullptr;
  bool touchscreenActive = false;
  FocusState *focus = nullptr;
  Core::Portable::Component *children = nullptr;
  std::vector<MainScreenReference> mainScreens;
  // Borrowed canonical children eligible for the corresponding typed lookup.
  // The portable CCL provider is built without C++ RTTI. Bindings must outlive
  // the lookups. The actual CCL child pointer is checked against each binding.
  std::vector<Presonus::Surface::MappingComponent *> mappingComponents;
  std::vector<Presonus::Surface::NetworkSetupComponent *>
      networkSetupComponents;
  // Borrowed application settings and the existing root CCL parameter tree.
  Core::Portable::SettingFile *settings = nullptr;
};
} // namespace presonus::surface
namespace Presonus::Surface {
class PanelRegistrar {
public:
  // Operational, independent MIDI source-port registration. Genuine CCL
  // vector preserves insertion order, duplicates and null entries. Removing
  // a pointer removes only its first occurrence; no ownership is transferred.
  // A handler bound through initializeOwnedParameters must have one live entry
  // at destruction. Remove extra registrations before destroying the handler.
  bool addMidiHandler(MidiMixerHandler *);
  bool removeMidiHandler(MidiMixerHandler *);
  int countMidiHandlers() const;
  MidiMixerHandler *getMidiHandler(int) const;
  void dispatchMidiSwitch(const Presonus::Panel::ControlRegistrar &, int, int,
                          bool, Presonus::Panel::SwitchControl *);
  void dispatchMidiEncoder(const Presonus::Panel::ControlRegistrar &, int, int,
                           Presonus::Panel::EncoderControl *);

  // Independent constructors; original AppMode lifecycle remains unrecovered.
  PanelRegistrar() = default;
  explicit PanelRegistrar(presonus::surface::PanelRegistrarCommandState &state)
      : commandState_(&state) {}
  // Independent borrowed CCL list adapter; no original layout/lifecycle claim.
  // Both selected tags must exist and yield finite signed32-representable
  // values.
  explicit PanelRegistrar(const Core::Portable::ParamList &parameters)
      : parameters_(&parameters) {}
  // Independent combined borrowed-state constructor; not original lifecycle.
  PanelRegistrar(const Core::Portable::ParamList &parameters,
                 presonus::surface::PanelRegistrarCommandState &state)
      : commandState_(&state), parameters_(&parameters) {}
  // Independent state injection; no original field/layout claim.
  void bindTests(presonus::surface::RegistrarTestState &state) {
    tests_ = &state;
  }
  enum TestMode : int {};
  void runTest(TestMode, bool);
  void setColorRgbLeds(unsigned char);
  void turnOnRgbLeds(bool);
  void invokeTestTouchscreen(bool);
  void invokePanelTest(TestMode, bool);
  void addSwitchControlGroup(int, const Core::Portable::ParamInfo *, int);
  void adjustLcdBrightness(int);
  void invoke48vTest(bool);
  void invokeCalibrateTouchTest(bool);
  void handleTouchscreen(Touchscreen_Type &);
  Core::Portable::Parameter *findParameter(const char *) const;
  Core::Portable::Parameter *getParameterByTag(int) const;
  void invokeScribbleStripTest(bool);
  void invokeControlSurfaceTest(bool);
  void invokeRgbTest(bool);
  // Incidental signed32 result observed; original return spelling unresolved.
  void handleCalibrateTouchscreenProgress(unsigned char panel,
                                          unsigned short progress);
  int bumpFaderTouchSensitivity(int delta);
  int bumpFaderSpeed(int delta);
  // Observed signed32 conversion results; original return declarations
  // unresolved.
  Presonus::IPanelPort *getPort() const;
  int getFaderSensitivity();
  int getFaderSpeed();
  // void returns are portable choices; ordinary original returns are
  // unresolved.
  void sendFaderFunctionMessage(unsigned char);
  void requestUpdatedFaderParameters();
  void invokeFaderCalibration(bool);
  // Observed signed 32-bit mapping result; original return spelling unresolved.
  int mapGroupIdToControlType(
      Presonus::Panel::ControlRegistrar::ControlType group) const;

private:
  Core::Vector<MidiMixerHandler *> midiHandlers_;
  presonus::surface::RegistrarTestState *tests_ = nullptr;
  presonus::surface::PanelRegistrarCommandState *commandState_ = nullptr;
  const Core::Portable::ParamList *parameters_ = nullptr;
};
class SurfaceRootComponent
    : public Presonus::Panel::ControlRegistrar::Delegate {
public:
  SurfaceRootComponent() = default;
  explicit SurfaceRootComponent(PanelRegistrar &registrar)
      : registrar_(&registrar) {}
  // Portable void declarations; original return declarations remain unresolved.
  void terminateTestTouchscreen();
  void manageUtilPageObserver(bool);
  int bumpFaderSpeed(int);
  void bindServices(presonus::surface::RootServices &value) {
    services_ = &value;
  }
  void updateFocusParams(Presonus::Panel::Control *);
  void networkChanged(const Presonus::WIFIManager &);
  void screenTouched(const Presonus::Panel::ControlRegistrar &, int, int, int,
                     int);
  // Direct source-port callback with provisional void return.
  void controlChanged(const Presonus::Panel::ControlRegistrar &, unsigned char,
                      unsigned char *);
  void faderChanged(const Presonus::Panel::ControlRegistrar &, int, int,
                    Presonus::Panel::FaderControl *) override;
  void switchChanged(const Presonus::Panel::ControlRegistrar &, int, int, bool,
                     Presonus::Panel::SwitchControl *) override;
  MainScreenComponent *getMainScreenComponent() const;
  MappingComponent *getMappingComponent() const;
  NetworkSetupComponent *getNetworkSetupComponent() const;
  // Portable callback declarations. Original return declarations are unknown.
  void paramChangedScribbleStripImageTest(bool);
  void paramChangedLaunchTestTouchscreen(bool);
  void stopAllTests();
  void paramChangedLaunchMardiGras(bool);
  void paramChangedExitUtilPage(Core::Portable::Parameter *);
  void paramChangedExitAudioUtilitiesPage();
  void paramChangedExitDiagnositcsPage(Core::Portable::Parameter *);
  void paramChangedLaunchAudioUtilities();
  void paramChangedLaunchFaderUtilities(bool);
  void paramChangedQuitTestTouchscreen();
  void paramChangedLaunchCalibrateTouchPage(bool);
  void paramChangedExitTestTouchscreenPage(Core::Portable::Parameter *);
  void paramChangedExitFaderUtilitiesPage(Core::Portable::Parameter *);
  void paramChangedExitCalibrateTouchPage(Core::Portable::Parameter *);
  void paramChangedCalibrationTarget(Core::Portable::Parameter *);
  void paramChangedDiagnositcsPage();
  void onMainScreenParamChanged(Core::Portable::Parameter *);
  void storeSettings() const;
  int bumpFaderTouchSensitivity(int);
  void paramChangedLcdBrightness(Core::Portable::Parameter *);
  // Observed 0/1 predicate result; original return spelling unresolved.
  bool isTransportControl(const char *controlName);
  // Portable bool declaration; original return spelling remains unresolved.
  bool isMappableControl(const char *controlName);

private:
  Core::Portable::Parameter &mainScreenParameter(int tag) const;
  Core::Portable::IParamObserver *pageObserver() const;
  Core::Portable::Parameter &rootParameter(int tag) const;
  PanelRegistrar *registrar_ = nullptr;
  presonus::surface::RootServices *services_ = nullptr;
};
} // namespace Presonus::Surface
