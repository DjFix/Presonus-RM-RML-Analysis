#include "presonus/PanControl.hpp"
#include <cstdio>
#include <stdexcept>
#include <utility>

namespace Presonus {
bool PanControl::isStereo() const {
  return parameters_[0] && parameters_[0]->getValue() != 0.f;
}
bool PanControl::isLinked() const {
  return parameters_[1] && parameters_[1]->getValue() != 0.f;
}
float PanControl::computeLinkedPanValue(float value) const {
  const float half = value * 0.5f;
  return isRightSideOfLink() ? half + 0.5f : 0.5f - half;
}
bool PanControl::isRightSideOfLink() const {
  if (parameters_[3])
    return parameters_[3]->getValue() != 0.f;
  auto *label = parameters_[2];
  if (!label)
    return false;
  char text[64] = {};
  label->toString(text, sizeof(text));
  if (!text[0])
    return true;
  long long number = 0;
  if (std::sscanf(text, "%lld", &number) == 1)
    return (static_cast<unsigned long long>(number) & 1) == 0;
  if (!label->getOriginal())
    return true;
  auto *controller = label->getOriginal()->getController();
  if (!controller)
    return true;
  if (!channelSideResolver_)
    throw std::logic_error(
        "PanControl channel/group source binding unresolved");
  return channelSideResolver_(controller);
}
void PanControl::paramChanged(Parameter *p, int msg) {
  if (msg == Parameter::kChanged) {
    for (auto *parameter : parameters_)
      if (parameter == p) {
        invalidate();
        break;
      }
  } else if (msg == Parameter::kDestroyed) {
    for (auto &parameter : parameters_)
      if (parameter == p) {
        parameter = nullptr;
        break;
      }
  }
  Core::Portable::Control::paramChanged(p, msg);
}
void PanControl::bindPanParameters(
    const std::array<Parameter *, 5> &parameters) {
  parameters_ = parameters;
}
const std::array<PanControl::Parameter *, 5> &
PanControl::panParameters() const {
  return parameters_;
}
void PanControl::setChannelSideResolver(ChannelSideResolver resolver) {
  channelSideResolver_ = std::move(resolver);
}
} // namespace Presonus
