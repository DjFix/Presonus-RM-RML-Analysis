#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <array>
#include <functional>
#include <string>
#include <vector>
namespace Presonus::Dsp {
class MultiParamProperty;
}
namespace presonus::mixer_port {
// Independent source-port state. None of these fields claims an ARM layout.
struct MasterProperty {
  struct Entry {
    int index;
    float value;
  };
  std::vector<Entry> entries;
  int count = 0;
};
struct MasterBindings {
  Core::Portable::Component &parameters;
  std::array<Core::Portable::Parameter *, 16> slots;
  Presonus::DelayTimer &timer;
  std::function<void(Core::Portable::ListParam &)> populateRoutes;
  std::function<int(int)> countSolos;
  std::function<bool()> isSlave, isMaster, isSubgroupMerge, solosBlocked;
  std::function<void()> clearSIPSolos, clearSolos, targetedIdle;
  std::function<void(const Presonus::UC::MessageAttributes &, int, int)>
      sendSolo;
  std::function<int()> slaveID;
  std::function<Core::Portable::Component *()> globalComponent;
  std::function<void(const MasterProperty &)> submitProperty;
  std::function<MasterProperty &(Presonus::Dsp::MultiParamProperty &)> property;
  // Each entry denotes presence and its optional stereo-link parameter.
  struct Channel {
    bool present;
    Core::Portable::Parameter *linked;
  };
  std::vector<Channel> channels;
  std::array<std::string, 5> labels{{"Aux", "Main", "Digital", "Solo", "Tape"}};
  std::string pairSeparator = "/";
  std::array<float, 13> cache{};
  bool dirty = false;
};
} // namespace presonus::mixer_port
namespace Presonus::Mixer {
// Encoded original method identities, with independent explicit bindings.
// Original ordinary returns, inheritance, layout and ARM ABI remain unresolved.
class MasterSectionComponent {
public:
  explicit MasterSectionComponent(
      presonus::mixer_port::MasterBindings &bindings)
      : b(bindings) {}
  void populateRouteList(int);
  void localSoloChanged();
  void remoteSoloChanged(int, int, int);
  void buildRemoteMonitorSelectList();
  void onMonitorSelectChanged();
  void rebuildMonitorSelectList();
  void addControlRmProperty(Presonus::Dsp::MultiParamProperty &, int, float);
  void doUpdates();
  void onIdle();
  void updateControlRoom();

private:
  presonus::mixer_port::MasterBindings &b;
  Core::Portable::Parameter &p(int slot) const { return *b.slots.at(slot); }
  void addProperty(presonus::mixer_port::MasterProperty &, int, float);
};
} // namespace Presonus::Mixer
