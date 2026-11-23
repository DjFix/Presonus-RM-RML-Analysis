#include "presonus/ColorButton.hpp"
#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"

void ColorButton::paramChanged(Core::Portable::Parameter *parameter,
                               int message) {
  Control::paramChanged(parameter, message);
  if (message == Core::Portable::Parameter::kChanged &&
      parameter == colorParameter_) {
    View::invalidate();
  }
}

void ColorButton::draw(const Core::Portable::DrawEvent &event) {
  Core::Rect client;
  getClientRect(client);
  if (!mixer_) {
    event.graphics.fillRect(client, getStyle().getBackColor());
    return;
  }

  const auto *channel = mixer_->getSelectedChannel();
  if (!channel)
    return;

  if (channel->getColorIndex() != 0) {
    event.graphics.fillRect(client, channel->getColor());
  } else if (fallbackBitmap_) {
    Core::Rect source;
    fallbackBitmap_->getFrame(source);
    event.graphics.drawBitmap(Core::Point(0, 0), *fallbackBitmap_, source);
  } else {
    event.graphics.fillRect(client, getStyle().getBackColor());
  }
  if (isFocused())
    drawFocusFrame(event);
}
