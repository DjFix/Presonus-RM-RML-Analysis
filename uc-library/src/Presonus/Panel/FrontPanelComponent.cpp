#include "presonus/panel/FrontPanelComponent.hpp"
#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include <cstdint>
#include <cstring>

namespace Presonus::Panel {
using presonus::frontpanel_port::Action;
void FrontPanelComponent::handlePaste() {
  if (!state.copyActive)
    return;
  for (int i = 0; i < state.pasteSelections.count(); ++i) {
    if (state.pasteSelections[i]->getValue() > 0 && state.channels.count()) {
      void *channel = i < state.channels.count() ? state.channels[i] : nullptr;
      if (channel)
        dependencies.paste(channel, state.copyContext, "ignoreAltMemory");
    }
  }
  dependencies.perform(Action::ExitCopy);
}
void FrontPanelComponent::enterPassCodeDigit(int digit) {
  static unsigned int passcodeDigit = 0;
  // The original ARM add wraps before its signed comparison.
  std::uint32_t bits = static_cast<std::uint32_t>(digit) + 1;
  std::int32_t value;
  std::memcpy(&value, &bits, sizeof(value));
  if (value > 9) {
    passcodeDigit = 0;
    return;
  }
  auto *code =
      state.settings.getParameterByTag(static_cast<int>(passcodeDigit + 31));
  auto *lock = state.settings.getParameterByTag(36);
  if (!code || !lock)
    return;
  // Bounded oracle domain: finite values representable by signed int.
  if (static_cast<int>(code->getValue()) != value) {
    passcodeDigit = 0;
    return;
  }
  if (++passcodeDigit == 5) {
    passcodeDigit = 0;
    lock->setValue(lock->getValue() == 0 ? 1.f : 0.f, true);
  }
}
void FrontPanelComponent::updateMixerLocks() {
  Core::DebugPrint("updateMixerLocks\n");
  lockFaders(dependencies.fadersLocked());
  dependencies.perform(Action::LockMasters, mastersLocked());
  dependencies.perform(Action::UpdateFatChannel, 0);
}
bool FrontPanelComponent::mastersLocked() const {
  static auto *lockMastersParam = state.settings.getParameterByTag(37);
  bool locked = lockMastersParam && lockMastersParam->getValue() > 0;
  return mixerLocked() && locked;
}
void FrontPanelComponent::buttonReleased(int group, int button) {
  if (group != 4 || state.heldButton != button)
    return;
  if (dependencies.timerLongEnough())
    dependencies.perform(Action::ExitInterrogate);
  dependencies.perform(Action::EndTimer);
  state.heldButton = -1;
}
void FrontPanelComponent::checkPassCodeEntry(int digit) {
  static auto *lockEnableParam = state.settings.getParameterByTag(30);
  if (!lockEnableParam || !(lockEnableParam->getValue() > 0))
    return;
  if (digit <= 8) {
    auto *page = dependencies.activePageName();
    if (!page)
      return;
    Core::CStringBuffer<64> name(page);
    if (std::strcmp(name, "System_SysLock"))
      return;
  }
  enterPassCodeDigit(digit);
}
void FrontPanelComponent::lockFaders(bool locked) {
  Core::DebugPrintf("lockFaders - %s\n", locked ? "true" : "false");
  if (locked)
    dependencies.perform(Action::DetachFaderGroup, 12);
  else
    dependencies.perform(Action::AttachFaders, 17);
}
void FrontPanelComponent::activateAll() {
  dependencies.perform(Action::BaseActivate);
  dependencies.perform(Action::VirtualActivate);
  dependencies.perform(Action::AttachLCD);
  dependencies.perform(Action::AttachFaders, 17);
  dependencies.perform(Action::AttachPots, 17);
  dependencies.perform(Action::AttachTable, 0);
  dependencies.perform(Action::AttachTable, 1);
  dependencies.perform(Action::AttachMicLine, 4, 304);
  dependencies.perform(Action::AttachMicLine, 3, 350);
  dependencies.perform(Action::AttachMicLine, 20, 307);
  dependencies.perform(Action::AttachMicLine, 21, 307);
  dependencies.perform(Action::VirtualFinish);
  dependencies.perform(Action::UpdateFatChannel, 0);
}
bool FrontPanelComponent::mixerLocked() const {
  static auto *lockStateParam = state.settings.getParameterByTag(36);
  return lockStateParam && lockStateParam->getValue() > 0;
}
void FrontPanelComponent::lockStateChanged() {
  auto *lock = state.settings.getParameterByTag(36);
  if (!lock)
    return;
  float lockValue = lock->getValue();
  auto *first = state.settings.getParameterByTag(37);
  float value = first->getValue();
  bool locked = lockValue > 0;
  first->setMin(locked ? value : 0.f);
  first->setMax(locked ? value : 1.f);
  for (int tag = 38; tag <= 40; ++tag) {
    auto *param = state.settings.getParameterByTag(tag);
    value = param->getValue();
    param->setMin(locked ? value : 0.f);
    param->setMax(locked ? value : 1.f);
  }
  updateMixerLocks();
}
} // namespace Presonus::Panel
