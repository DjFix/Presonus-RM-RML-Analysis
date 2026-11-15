#pragma once
#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
namespace Presonus::Panel {
// Independent initialized portable binding; no original constructor/layout
// claim.
class BeastFrontPanelComponent {
public:
  explicit BeastFrontPanelComponent(
      Mixer::MixerComponentBase &mixer,
      Core::Portable::NumericParam *band = nullptr, int offset = 0)
      : mixer(mixer), band(band), offset(offset) {}
  // Ordinary original return declarations remain pending.
  bool checkGeqViewRange();
  void getTablesForGroup(int group, const int *&first, const int *&second,
                         int &count) const;
  int scrollOffset() const { return offset; }

private:
  Mixer::MixerComponentBase &mixer;
  Core::Portable::NumericParam *band;
  int offset;
};
} // namespace Presonus::Panel
