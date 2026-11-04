#include "presonus/panel/ScenesComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstring>

namespace Presonus::Panel {
ScenesComponent::~ScenesComponent() = default;
bool ScenesComponent::store() {
  const int slot = getSlotNum();
  if (!slot)
    return false;
  Core::CString256 name;
  required(*this, 2).toString(name.getBuffer(), name.getSize());
  auto *cache = getCache();
  const auto filename = cache->buildFileName(static_cast<unsigned>(slot), name,
                                             "", nullptr, true);
  const auto previous = getFileNameForSlot(static_cast<unsigned>(slot));
  if (!previous.isEmpty() && std::strcmp(filename.str(), previous.str()) != 0)
    Core::Portable::FileUtils::deleteFile(previous.str());
  mixer.saveScene(filename, name, true);
  getCache()->cachePreset(name, "", slot);
  presetStored();
  return true;
}
} // namespace Presonus::Panel
