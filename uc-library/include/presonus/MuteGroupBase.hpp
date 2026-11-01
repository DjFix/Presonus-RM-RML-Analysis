#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"

namespace presonus::mute_group_port {
// Independent source-port state. No original class layout or ownership claim.
struct State {
  Core::Portable::Parameter *active = nullptr;
  Core::Portable::Parameter *status = nullptr;
  Core::Portable::Parameter *alternateStatus = nullptr;
  Core::Vector<Core::Portable::Parameter *> members;
};
} // namespace presonus::mute_group_port

namespace Presonus {
// Original method scopes and encoded arguments; unencoded returns and layout
// remain unresolved. Provider API selection is an intentional source
// adaptation.
class MuteGroupBase {
public:
  explicit MuteGroupBase(presonus::mute_group_port::State &state)
      : state(state) {}
  void updateActive();
  void updateStatus();
  bool groupDirty() const;
  bool validStatus(Core::Portable::Parameter *parameter) const;
  void deactivate();

private:
  presonus::mute_group_port::State &state;
};
} // namespace Presonus
