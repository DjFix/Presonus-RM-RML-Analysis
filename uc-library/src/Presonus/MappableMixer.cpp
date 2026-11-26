#include "presonus/MappableMixer.hpp"

namespace Presonus {
MappableMixer::MappableMixer() = default;
MappableMixer::~MappableMixer() = default;
void MappableMixer::sendObjectChangeMessage(
    IMixerComponentObserver::ObjectChangeMessage message) {
  auto *items = observers_.getItems();
  auto count = observers_.count();
  if (static_cast<int>(message) == 13) {
    for (int i = 0; i < count; ++i)
      items[i]->onSelectionChanged();
    items = observers_.getItems();
    count = observers_.count();
  }
  for (int i = 0; i < count; ++i)
    items[i]->onObjectChanged(message);
}

IColorConverter *MappableMixer::getColorConverter() const {
  return colorConverter_;
}
void MappableMixer::setColorConverter(IColorConverter *converter) {
  colorConverter_ = converter;
}

void MappableMixer::setPresetHandler(IPresetHandler *handler) {
  presetHandler_ = handler;
}
IPresetHandler *MappableMixer::getPresetHandler() const {
  return presetHandler_;
}

SLChannelBase *MappableMixer::getSelectedGeq() const { return nullptr; }
int MappableMixer::countAllChannels() const { return 0; }
SLChannelBase *MappableMixer::getChannelIndexed(int) const { return nullptr; }
} // namespace Presonus
