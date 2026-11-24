#include "presonus/MappableMixer.hpp"

namespace Presonus {
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
