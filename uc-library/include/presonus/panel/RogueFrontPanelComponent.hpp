#pragma once
#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstdint>
namespace presonus::panel {
// Independent borrowed source-port bindings, not recovered fields/ARM layout.
// The real mixer inputChannels vector is the sole viewport-count authority.
struct RogueGeqViewportState {
  Core::Portable::NumericParam *selected;
  Presonus::Mixer::MixerComponentBase &mixer;
  std::int32_t offset;
};
} // namespace presonus::panel
namespace Presonus::Panel {
// Partial source port. Original inheritance, constructor/lifecycle and ARM ABI
// remain unresolved. All return declarations are provisional source choices.
class RogueFrontPanelComponent {
public:
  struct SourcePortConstruction {};
  explicit RogueFrontPanelComponent(SourcePortConstruction) {}
  explicit RogueFrontPanelComponent(
      presonus::panel::RogueGeqViewportState &state)
      : viewport_(&state) {}
  bool checkGeqViewRange();
  // Count is a native output value, not a safe extent for either returned
  // table. Each readonly table ends in -1; all original data identities are
  // retained.
  virtual void getTablesForGroup(int group, const int *&first,
                                 const int *&second, int &count) const;

private:
  presonus::panel::RogueGeqViewportState *viewport_ = nullptr;
};
} // namespace Presonus::Panel
