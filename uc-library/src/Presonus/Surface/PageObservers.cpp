#include "core/portable/gui/coreview.h"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <algorithm>
#include <cstdint>
namespace Presonus::Surface {
void EQPageComponent::removeObserver(IObserver *observer) {
  observers_.remove(observer);
}
void GeqPageComponent::removeObserver(IObserver *observer) {
  observers_.remove(observer);
}
void GeqPageComponent::updateBands() {
  if (!page_ || !page_->isVisible())
    return;
  // Negative offsets are excluded by the configured source-port domain.
  listOffset_ = std::min(listOffset_, 15);
  if (listOffset_ != notifiedOffset_) {
    notifiedOffset_ = listOffset_;
    const int count = observers_.count();
    auto *const *observers = observers_.getItems();
    for (int index = 0; index < count; ++index)
      observers[index]->onGeqScrollOffsetChanged();
  }

  constexpr int frequencies[] = {
      20,   25,   32,   40,   50,   63,    80,    100,   125,  160,  200,
      250,  320,  400,  500,  640,  800,   1000,  1300,  1600, 2000, 2500,
      3000, 4000, 5000, 6400, 8000, 10000, 13000, 16000, 20000};
  for (int row = 0; row < 16; ++row) {
    auto *label = bandParameters_.byTag(2 * row);
    auto *alias = bandParameters_.getAlias(2 * row + 1);
    const int index = row + listOffset_;
    const int frequency = frequencies[index];
    Core::CString64 text;
    if (frequency < 1000)
      text.appendFormat("%d", frequency);
    else if (frequency % 1000 == 0)
      text.appendFormat("%dk", frequency / 1000);
    else
      text.appendFormat("%.1fk", static_cast<float>(frequency) / 1000.f);
    Core::CString32 name;
    name.appendFormat("band_gain_%02d", index + 1);
    // A configured band list supplies every label and alias. Missing named
    // targets are valid and disconnect the corresponding alias.
    label->fromString(text, false);
    alias->setOriginal(parameters_.findParameter(name));
  }
}

void GeqPageComponent::addListOffset(int delta) {
  const auto sum = static_cast<std::uint32_t>(listOffset_) +
                   static_cast<std::uint32_t>(delta);
  const int offset = std::clamp(static_cast<std::int32_t>(sum), 0, 15);
  if (offset != listOffset_) {
    listOffset_ = offset;
    updateBands();
  }
}

void GeqPageComponent::onWheelInput(const Core::Portable::WheelEvent &event) {
  addListOffset(event.delta);
}

void GeqPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                    int message) {
  parameters_.paramChanged(parameter, message);
  const int tag = parameter->getTag();
  if (message == 2 && (tag == 1000 || tag == 1001) &&
      parameter->getValue() > 0.f)
    addListOffset(tag == 1000 ? -16 : 16);
}
} // namespace Presonus::Surface
