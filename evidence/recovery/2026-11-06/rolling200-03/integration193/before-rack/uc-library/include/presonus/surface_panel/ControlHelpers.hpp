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
#include <string>
#include <vector>
struct Touchscreen_Type;

// Portable class declarations for the evidenced methods only. These do
// not reproduce original inheritance, object storage, vtables or ARM32 layouts.
namespace presonus::panel_binding {
struct RegistrarGroupRegistry;
}
namespace Presonus::Panel {
class EncoderControl;
class ControlGroup;
class ControlRegistrar {
public:
  // Independent borrowed setup only; original lifecycle/layout unresolved.
  ControlRegistrar() = default;
  explicit ControlRegistrar(
      presonus::panel_binding::RegistrarGroupRegistry &state)
      : groupRegistry_(&state) {}
  // Original return spellings are unencoded; these are portable declarations.
  int count() const;
  ControlGroup *at(int index) const;
  // Original nested enum identity is encoded in the method's mangled name.
  // Original enumerator names/range/underlying declaration are unresolved;
  // the portable int32 domain preserves the observed ARM register behavior.
  enum ControlType : int {};

private:
  presonus::panel_binding::RegistrarGroupRegistry *groupRegistry_ = nullptr;
};
class SevenSegControl {
public:
  // The ARM implementation returns a zero-extended 16-bit bitmap. Its exact
  // original C++ return declaration is not encoded in the symbol name.
  std::uint16_t convertCharToBmp(char character, bool decimalPoint) const;
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
  FocusState *focus = nullptr;
  Core::Portable::Component *children = nullptr;
  std::vector<MainScreenReference> mainScreens;
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
class SurfaceRootComponent {
public:
  SurfaceRootComponent() = default;
  explicit SurfaceRootComponent(PanelRegistrar &registrar)
      : registrar_(&registrar) {}
  int bumpFaderSpeed(int);
  void bindServices(presonus::surface::RootServices &value) {
    services_ = &value;
  }
  void updateFocusParams(Presonus::Panel::Control *);
  void faderChanged(const Presonus::Panel::ControlRegistrar &, int, int,
                    Presonus::Panel::FaderControl *);
  void switchChanged(const Presonus::Panel::ControlRegistrar &, int, int, bool,
                     Presonus::Panel::SwitchControl *);
  MainScreenComponent *getMainScreenComponent() const;
  int bumpFaderTouchSensitivity(int);
  void paramChangedLcdBrightness(Core::Portable::Parameter *);
  // Observed 0/1 predicate result; original return spelling unresolved.
  bool isTransportControl(const char *controlName);
  // Portable bool declaration; original return spelling remains unresolved.
  bool isMappableControl(const char *controlName);

private:
  PanelRegistrar *registrar_ = nullptr;
  presonus::surface::RootServices *services_ = nullptr;
};
} // namespace Presonus::Surface
