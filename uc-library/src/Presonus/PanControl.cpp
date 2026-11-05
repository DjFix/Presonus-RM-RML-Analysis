#include "presonus/PanControl.hpp"
#include <cmath>
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
void PanControl::draw(const Core::Portable::DrawEvent &event) {
  auto *parameter = getParameter();
  if (!parameter || !parameter->isEnabled() || !isEnabled())
    return;
  if (getImage().getBitmap()) {
    drawImagePanner(event);
  } else {
    // Native PanControl and ValueBar vtables both bind this inherited slot to
    // ValueBar::drawBackground. Use the pinned provider and its real state.
    drawBackground(event);
    Core::Rect client;
    getClientRect(client);
    float value = parameter->getNormalized();
    if (parameters_[4] && (isLinked() || isStereo()))
      value = parameters_[4]->getNormalized();
    const int width = client.getWidth();
    const int center = width / 2;
    int left, right;
    if (isStereo()) {
      const int amount =
          static_cast<int>(static_cast<float>(width) * (value * 0.5f));
      left = center - amount;
      right = center + amount;
    } else {
      if (isLinked())
        value = computeLinkedPanValue(value);
      const int amount =
          static_cast<int>((value - 0.5f) * static_cast<float>(width));
      left = right = center;
      if (value < 0.5f)
        left += amount;
      else
        right += amount;
    }
    --left;
    ++right;
    if (left < right && client.getHeight() > 0)
      event.graphics.fillRect(Core::Rect(left, 0, right, client.getHeight()),
                              getStyle().getTextColor());
  }
  drawValueMark(event);
  if (isFocused())
    drawFocusFrame(event);
}

void PanControl::drawValueMark(const Core::Portable::DrawEvent &event) {
  if (valueBarWidth_ <= 0)
    return;
  float value = getParameter()->getNormalized();
  if (isLinked())
    value = computeLinkedPanValue(value);
  Core::Rect client;
  getClientRect(client);
  const int width = client.getWidth();
  const int position = static_cast<int>(static_cast<float>(width) * value);
  const int half = valueBarWidth_ / 2;
  int left = position - half;
  int right;
  if (left < 0) {
    left = 0;
    right = valueBarWidth_;
  } else
    right = position + half;
  if (right > width) {
    left = width - valueBarWidth_;
    right = width;
  }
  if (left < right && client.getHeight() > 0)
    event.graphics.fillRect(Core::Rect(left, 0, right, client.getHeight()),
                            getStyle().getTextColor());
}

void PanControl::drawImagePanner(const Core::Portable::DrawEvent &event) {
  auto *parameter = getParameter();
  auto *bitmap = getImage().getBitmap();
  if (!parameter || !bitmap || !parameter->isEnabled())
    return;
  Core::Rect client;
  getClientRect(client);
  const int center = client.left + client.getWidth() / 2;
  float value = parameter->getNormalized();
  if (parameters_[4] && (isLinked() || isStereo()))
    value = parameters_[4]->getNormalized();
  if (isStereo()) {
    Core::Rect first(0, 0, bitmap->getWidth(), bitmap->getHeight());
    Core::Rect second(first);
    if (bitmap->getFrameCount() > 1) {
      first.bottom /= bitmap->getFrameCount();
      second.top = first.bottom;
      second.bottom = first.bottom * 2;
    }
    const int amount =
        static_cast<int>(static_cast<float>(first.right) * value);
    const int start = first.right - amount;
    first.left = start;
    first.right = start + amount;
    event.graphics.drawBitmap(Core::Point(start, 0), *bitmap, first, nullptr);
    second.right = second.left + amount;
    event.graphics.drawBitmap(Core::Point(center + 1, 0), *bitmap, second,
                              nullptr);
  } else {
    if (isLinked())
      value = computeLinkedPanValue(value);
    const float distance = value - 0.5f;
    // Native threshold literal is bound in the oracle proof.
    if (static_cast<double>(std::fabs(distance)) >= 0.01) {
      Core::Rect source;
      if (value > 0.5f) {
        bitmap->getFrame(source, 1);
        source.right = source.left +
                       static_cast<int>(static_cast<float>(source.getWidth()) *
                                        (distance + distance));
        if (source.getWidth() > 0 && source.getHeight() > 0)
          event.graphics.drawBitmap(Core::Point(center, 0), *bitmap, source,
                                    nullptr);
      } else {
        bitmap->getFrame(source, 0);
        const float doubled = value + value;
        const int start = center - static_cast<int>(static_cast<float>(center) *
                                                    (1.f - doubled));
        source.left = start;
        source.right = center;
        if (source.getWidth() > 0 && source.getHeight() > 0)
          event.graphics.drawBitmap(Core::Point(start, 0), *bitmap, source,
                                    nullptr);
      }
    }
  }
  event.graphics.drawLine(Core::Point(center, 1),
                          Core::Point(center, client.bottom - 1),
                          getStyle().getBackColorDisabled());
}
} // namespace Presonus
