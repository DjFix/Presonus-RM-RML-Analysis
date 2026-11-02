#include "presonus/panel/PresetNameManager.hpp"
namespace Presonus::Panel {
PresetNameCache *PresetNameManager::getCache(int index) const {
  return caches.at(index);
}
} // namespace Presonus::Panel
