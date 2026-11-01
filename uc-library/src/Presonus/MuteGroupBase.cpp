#include "presonus/MuteGroupBase.hpp"

namespace Presonus {
bool MuteGroupBase::validStatus(Core::Portable::Parameter *p) const {
  if (!p)
    return false;
  if (p->getMax() == 0.f && p->getValue() == -1.f)
    return true;
  return p->getMax() > 0.f && p->getValue() >= 0.f;
}
void MuteGroupBase::updateActive() {
  if (!validStatus(state.status) || !validStatus(state.alternateStatus))
    return;
  bool any = state.status && state.status->getValue() > 0.f;
  if (state.alternateStatus && state.alternateStatus->getValue() > 0.f)
    any = true;
  if (state.active && !any)
    state.active->setValue(0.f, false);
}
bool MuteGroupBase::groupDirty() const {
  if (state.active && state.active->getValue() == 0.f)
    return false;
  for (int i = 0; i < state.members.count(); ++i)
    if (state.members[i]->getValue() == 0.f)
      return true;
  return false;
}
void MuteGroupBase::updateStatus() {
  if (!state.status)
    return;
  const int count = state.members.count();
  int positive = 0;
  for (int i = 0; i < count; ++i)
    if (state.members[i]->getValue() > 0.f)
      ++positive;
  if (count && state.status->getMax() == static_cast<float>(count)) {
    state.status->setValue(static_cast<float>(positive), false);
    return;
  }
  state.status->resetValue(false);
  state.status->setMax(static_cast<float>(count));
  state.status->rangeChanged();
}
void MuteGroupBase::deactivate() { state.members.empty(); }
} // namespace Presonus
