#pragma once
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <array>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>
namespace Presonus {
class MappingTable;
class MackieControlComponent;
namespace Panel {
class ControlRegistrar;
class SwitchControl;
class EncoderControl;
} // namespace Panel
} // namespace Presonus
namespace presonus::surface::midi_port {
// Independent source-port state; no original layout or ownership claim.
struct State {
  bool enabled{};
  std::uint8_t mappingCount{};
  std::int32_t activeMapping{-1};
  // Borrowed terminated 44-byte descriptions. Only byte 0 (name) and byte
  // 37 (eligibility) are interpreted; this is an independent portable record.
  // The caller supplies a readable terminator and valid terminated names.
  const std::array<unsigned char, 44> *controlDescriptions{};
  Presonus::MappingTable *mappingTable{};
  Core::Portable::Component *normalParameters{};
  Core::Portable::Component *alternateParameters{};
  std::array<std::uint32_t, 17> accumulation{};
  std::vector<std::string> colorControls;
  // Borrowed actual CCL provider for the original local Component boundary.
  // Independent source-port binding, not the original this+0xc layout.
  Core::Portable::Component *localParameters{};
  // Explicit independent borrowed dispatch setup. These are actual concrete
  // providers, never casts from normalParameters/alternateParameters. All must
  // outlive dispatch; model release callbacks must invoke real model
  // operations.
  Presonus::MackieControlComponent *normalMackie{};
  Presonus::MackieControlComponent *alternateMackie{};
  Presonus::IMappingController *controller{};
};
struct Services {
  virtual ~Services() = default;
  virtual void setDefaultColor(const std::string &) = 0;
  virtual bool recordParameterPresent() = 0;
  virtual float recordParameterValue() = 0;
  virtual void updateRecordMapping(bool vpot) = 0;
  // Resolve each slot at the time it is visited, permitting first-call
  // mutation.
  virtual bool idleSlotPresent(unsigned slot) = 0;
  virtual void invokeIdleSlot(unsigned slot) = 0;
};
} // namespace presonus::surface::midi_port
namespace Presonus::Surface {
class PanelRegistrar;
class MidiMixerHandler {
public:
  // Intentional portable constructor and return choices, declarations pending.
  MidiMixerHandler(presonus::surface::midi_port::State &state,
                   presonus::surface::midi_port::Services &services)
      : state_(state), services_(services), observer_(*this) {}
  // Host virtual destruction provides D0/D1/D2 identities. This portable class
  // and observer composition do not reproduce original inheritance/ARM layout.
  virtual ~MidiMixerHandler();
  MidiMixerHandler(const MidiMixerHandler &) = delete;
  MidiMixerHandler &operator=(const MidiMixerHandler &) = delete;
  // Explicit source-port setup, not reconstruction of an original constructor.
  // Transfer a genuine local CCL component; its children/parameters are owned
  // by CCL. Normal/alternate providers and registrar remain borrowed and must
  // outlive this handler. Normal tag 0xa007 must keep its identity while bound.
  // Local tags required by encoder/parameter callbacks must be supplied.
  // Do not rebind this state or mutate registration during callback dispatch.
  // On teardown, restore the previous borrowed localParameters binding.
  void
  initializeOwnedParameters(std::unique_ptr<Core::Portable::Component> local,
                            PanelRegistrar &registrar);
  // Independent portable record. ARM offsets/stride are not asserted.
  // Borrowed terminated names/colors and a first-byte-empty terminator are
  // required; selected component and mappingTable must be live.
  struct MappingItem {
    char name[32]{};
    std::int32_t tag{};
    std::uint8_t alternate{};
    std::uint8_t disable{};
    const char *color{};
  };
  void updateMapping(const MappingItem *);
  bool getParamFocusInfo(Presonus::MixerAssignmentHandler::FocusInfo &,
                         Core::Portable::Parameter *);
  void connect();
  // Provisional void returns: original ordinary return declarations unresolved.
  // Missing concrete bindings throw at the guarded provider boundary, outside
  // the native valid-receiver domain. Enabled switch dispatch needs a live
  // control; enabled encoder dispatch needs live localParameters. No original
  // constructor credit.
  void disconnect();
  void setController(Presonus::IMappingController *);
  void switchChanged(const Presonus::Panel::ControlRegistrar &, int, int, bool,
                     Presonus::Panel::SwitchControl *);
  void encoderChanged(const Presonus::Panel::ControlRegistrar &, int, int,
                      Presonus::Panel::EncoderControl *);
  int countMappings() const;
  const char *getName() const;
  bool canActivate() const;
  int getActiveMapping() const;
  void setActiveMapping(int);
  void setControlsEnabled(bool);
  void resetColors();
  const char *getMappingName(int);
  void resetAccumulation();
  void updateRecordReadyMappings();
  void onIdle();
  // Provisional void return; original unencoded return declaration unresolved.
  // Formatting requires live localParameters and its tag-2 output parameter.
  void paramChanged(Core::Portable::Parameter *, int);

private:
  class Observer final : public Core::Portable::ParamObserverBase {
  public:
    explicit Observer(MidiMixerHandler &owner) : owner_(owner) {}
    void paramChanged(Core::Portable::Parameter *, int) override;

  private:
    MidiMixerHandler &owner_;
  };
  presonus::surface::midi_port::State &state_;
  presonus::surface::midi_port::Services &services_;
  Observer observer_;
  PanelRegistrar *registrar_ = nullptr;
  Core::Portable::Component *previousLocal_ = nullptr;
  std::unique_ptr<Core::Portable::Component> ownedLocal_;
};
} // namespace Presonus::Surface
