#include "presonus/surface/MappingComponent.hpp"
#include "core/public/corestringbuffer.h"
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace Presonus::Surface {
// Original scopes and encoded parameter identities. Return spellings, storage
// and provider boundaries are an intentional portable source contract.
void MappingComponent::onSelectedChannelChanged() {
  if (selectedHandler_)
    selectedHandler_->selectedChanged();
}
void MappingComponent::setDefaultMapping() {
  if (displayHandler_)
    displayHandler_->defaultMapping();
  if (secondaryHandler_)
    secondaryHandler_->defaultMapping();
}
void MappingComponent::updateDisplayEncoderAssignment() {
  if (displayHandler_)
    displayHandler_->displayAssignment();
}
void MappingComponent::connectControl(int tag, const char *name,
                                      const char *color) {
  if (!bindings_)
    throw std::logic_error("mapping bindings required");
  auto *p = countParameters() > 0 ? getParameterByTag(tag) : nullptr;
  if (!p)
    return;
  bindings_->connect(name, p, nullptr, false);
  if (color)
    bindings_->color(name, color, true);
}
void MappingComponent::onDeviceDisconnected() {
  if (!bindings_)
    throw std::logic_error("mapping bindings required");
  bindings_->disconnectMixerParams();
  for (int i = 1; i <= 16; ++i) {
    Core::CStringBuffer<32> name;
    name.appendFormat("%s_%02d", "scribble_number", i);
    bindings_->connect(
        name, countParameters() > 0 ? getParameterByTag(9999 + i) : nullptr,
        nullptr, false);
  }
}
void MappingComponent::onFootswitchModeChanged(int mode) {
  if (!bindings_)
    throw std::logic_error("mapping bindings required");
  auto *p = countParameters() > 0 ? getParameterByTag(39) : nullptr;
  bindings_->connect("page:fxedit.footswitch", mode == 0 ? p : nullptr, nullptr,
                     false);
  bindings_->connect("page:scenes.fsw_load", mode == 2 ? p : nullptr, nullptr,
                     false);
}
int MappingComponent::getModifiers() const {
  if (countParameters() <= 0)
    throw std::logic_error("mapping modifier parameters required");
  int result = 0;
  for (auto tag : {9, 10, 8}) {
    auto *p = getParameterByTag(tag);
    if (!p)
      throw std::logic_error("mapping modifier parameters required");
    if (p->getValue() != 0.f)
      result |= tag == 9 ? 1 : tag == 10 ? 2 : 4;
  }
  return result;
}
void MappingComponent::connectControls() {
  if (!bindings_)
    throw std::logic_error("mapping bindings required");
  for (int i = 1; i <= 16; ++i) {
    Core::CStringBuffer<32> name;
    name.appendFormat("%s_%02d", "strip_mixselect", i);
    connectControl(i + 12, name, nullptr);
  }
  for (int i = 1; i <= 4; ++i) {
    Core::CStringBuffer<32> name;
    name.appendFormat("%s_%02d", "fx_mixselect", i);
    connectControl(i + 28, name, nullptr);
  }
  connectControl(33, "main_mix", nullptr);
  connectControl(11, "fx_tap", nullptr);
  connectControl(8, "mod_option", nullptr);
  connectControl(9, "mod_control", nullptr);
  connectControl(10, "mod_shift", nullptr);
  connectControl(0, "mapping_bank_a", "green");
  connectControl(1, "mapping_bank_b", "blue");
  connectControl(2, "mapping_bank_c", "lightblue");
  connectControl(3, "mapping_bank_d", "purple");
  connectControl(12, "quick_recall", "yellow");
  connectControl(4, "mapping_return", "yellow");
  connectControl(5, "mapping_mixmasters", nullptr);
  connectControl(6, "mapping_groupmasters", nullptr);
  if (auto *screen = bindings_->mainScreen(getRootComponent())) {
    if (auto *p = screen->countParameters() > 0 ? screen->getParameterByTag(19)
                                                : nullptr)
      bindings_->connect("marker", p, nullptr, false);
  }
}
void MappingComponent::paramChanged(Core::Portable::Parameter *p, int msg) {
  Core::Portable::Component::paramChanged(p, msg);
  const int tag = p->getTag();
  if (msg == 0) {
    if (tag == 33)
      holdTimer_.beginAction(-1.f);
    return;
  }
  if (msg == 3) {
    if (tag == 38) {
      const float f = p->getValue();
      if (!std::isfinite(f) || f < -2147483648.f || f >= 2147483648.f)
        throw std::domain_error("finite int32 footswitch mode required");
      onFootswitchModeChanged(static_cast<int>(f));
    } else if (tag == 39)
      handleFootswitch(p->getValue() != 0.f);
    return;
  }
  if (msg == 1) {
    if (tag == 11) {
      p->resetValue(false);
      return;
    }
    if (tag != 33)
      return;
    if (!holdTimer_.wasLongEnough()) {
      verifyRadioParam(p);
      if (displayHandler_)
        displayHandler_->mappingParamChanged(p);
    }
    if (!blinkTimer_.isExecuting()) {
      if (auto *main = countParameters() > 0 ? getParameterByTag(33) : nullptr)
        main->enable(true);
    }
    holdTimer_.reset();
    return;
  }
  if (msg != 2)
    return;
  const std::uint32_t shifted = static_cast<std::uint32_t>(tag) - 7U;
  if (shifted <= 26U) {
    const auto bit = 1U << shifted;
    if (bit & 0x04000030U)
      return;
    if (bit & 0xeU) {
      if (displayHandler_)
        displayHandler_->modifiersChanged();
      if (secondaryHandler_)
        secondaryHandler_->modifiersChanged();
      return;
    }
    if (bit & 1U) {
      if (!bindings_)
        throw std::logic_error("mapping bindings required");
      bindings_->updateDAW(p->getValue() != 0.f);
      p->setValue(displayHandler_ != dawHandler_ ? 1.f : 0.f, false);
      return;
    }
  }
  verifyRadioParam(p);
  if (displayHandler_)
    displayHandler_->mappingParamChanged(p);
}
void MappingComponent::onIdle() {
  Core::Portable::Component::onIdle();
  if (displayHandler_)
    displayHandler_->idle();
  if (secondaryHandler_)
    secondaryHandler_->idle();
  if (holdTimer_.isExecuting() && holdTimer_.isLongEnoughYet()) {
    blinkTimer_.beginAction(-1.f);
    holdTimer_.endAction();
    if (!bindings_)
      throw std::logic_error("mapping bindings required");
    bindings_->blink("main_mix", "blink");
    if (auto *p = countParameters() > 0 ? getParameterByTag(33) : nullptr)
      p->enable(false);
    blinkState_ = !blinkState_;
    if (displayHandler_)
      displayHandler_->defaultMapping();
  }
  if (blinkTimer_.isExecuting() && blinkTimer_.isLongEnoughYet()) {
    blinkTimer_.endAction();
    if (!bindings_)
      throw std::logic_error("mapping bindings required");
    bindings_->blink("main_mix", "off");
  }
}
} // namespace Presonus::Surface
