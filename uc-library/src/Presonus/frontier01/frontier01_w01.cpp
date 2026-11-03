#include "presonus/frontier01/frontier01_w01.hpp"
#include "presonus/panel/PresetNameCache.hpp"

MixerSceneLoader::~MixerSceneLoader() = default;
namespace Presonus::Panel {
SPIControl::~SPIControl() = default;
Core::Portable::FileName
PresetComponent::getFileNameForSlot(unsigned int slot) const {
  return getCache()->getFileNameForSlot(slot, true);
}
void PresetNameManager::rebuildAllCaches() const {
  auto *const *items = caches.getItems();
  const int count = caches.count();
  for (int i = 0; i < count; ++i) {
    items[i]->dirty = true;
    items[i]->rebuild();
  }
}
void FxPresetComponent::presetStored(const PresetComponent &, int) {
  auto *const *items = recalls.getItems();
  const int count = recalls.count();
  for (int i = 0; i < count; ++i)
    items[i]->updateFxName();
}
} // namespace Presonus::Panel
