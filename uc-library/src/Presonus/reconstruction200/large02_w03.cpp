#include "presonus/reconstruction200/large02_w03.hpp"
#include <bit>
#include <stdexcept>
namespace Presonus::Dsp {
EQController::EQController(int count, int flags,
                           const ParamDescriptorList *list)
    : Controller(flags, list), controllerState_(Controller::sourceState()) {
  if (count < 0 || count > 8)
    throw std::out_of_range("EQ band count");
  bands_.resize(static_cast<unsigned>(count));
  for (auto &b : bands_) {
    b.frequency = std::bit_cast<float>(0x44960000u);
    b.q = std::bit_cast<float>(0x3f3504f3u);
    b.type = 6;
    // Explicit source-state adaptation to the existing calculator provider.
    // The view is const, but this newly constructed provider is mutable.
    if (!usedInProcessContext())
      const_cast<presonus::dsp::BiquadState<double> &>(
          b.calculator.portableState())
          .byte48 = 1;
  }
}
EQController::~EQController() = default;
float EQController::getValue(int tag) const {
  if (tag == 0)
    return enabled_ ? 1.f : 0.f;
  if (tag < 0)
    return 0.f;
  unsigned i = static_cast<unsigned>(tag - 1) / 6;
  if (i >= bands_.size())
    throw std::out_of_range("Unchecked native band index");
  const auto &b = bands_[i];
  switch ((tag - 1) % 6) {
  case 0:
    return static_cast<float>(getEQType(static_cast<DSP::BiquadType>(b.type)));
  case 1:
    return b.gain;
  case 2:
    return b.q;
  case 3:
    return b.frequency;
  case 4:
    return b.enabled ? 1.f : 0.f;
  case 5:
    return b.edgeSelectable ? 1.f : 0.f;
  }
  return 0.f;
}
float EQController::setValue(int tag, float value) {
  if (tag == 0) {
    enabled_ = value != 0.f;
    for (auto &b : bands_)
      b.dirty = 1;
    controllerState_.processDirty = 1;
    return value;
  }
  if (tag < 0)
    return value;
  unsigned i = static_cast<unsigned>(tag - 1) / 6;
  if (i >= bands_.size())
    throw std::out_of_range("Unchecked native band index");
  auto &b = bands_[i];
  const int local = (tag - 1) % 6 + 1;
  b.dirty = 1;
  if (!controllerState_.processDirty)
    controllerState_.processDirty = enabled_ && (b.enabled || local == 5);
  switch (local) {
  case 1:
    b.type = getBiquadType(static_cast<int>(value + .5f));
    break;
  case 2:
    b.gain = value;
    break;
  case 3:
    b.q = value;
    break;
  case 4:
    b.frequency = value;
    break;
  case 5:
    b.enabled = value != 0.f;
    break;
  case 6:
    b.edgeSelectable = value != 0.f;
    triggerOption(static_cast<int>(i));
    break;
  }
  return value; // provisional source contract; native return declaration
                // pending
}
void EQController::doUpdates() {
  ChannelProperty p;
  p.type = 0x6d627164;
  p.size = 0xd0;
  for (unsigned i = 0; i < bands_.size(); ++i) {
    auto &b = bands_[i];
    if (!b.dirty)
      continue;
    b.calculator.setParams(b.type, b.frequency, b.q, b.gain);
    b.dirty = 0;
    if (p.count <= 7) {
      auto &e = p.entries[static_cast<unsigned>(p.count++)];
      e.band = static_cast<int>(i) + 1;
      e.coefficients = {1.f, 0.f, 0.f, 0.f, 0.f};
      if (enabled_ && b.enabled)
        for (unsigned k = 0; k < 5; ++k)
          e.coefficients[k] =
              static_cast<float>(b.calculator.portableState().coefficients[k]);
    }
    if (b.dirty)
      controllerState_.processDirty = 1;
  }
  if (p.count)
    sendProperty(p, true);
}
} // namespace Presonus::Dsp
