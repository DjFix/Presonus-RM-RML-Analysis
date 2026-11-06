#include "core/portable/corefile.h"
#include "presonus/StormMixSceneComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstring>

namespace Presonus {
Core::Portable::FileName
StormMixSceneComponent::getFileName(unsigned int index) const {
  // ARM SUBS followed by BMI examines the wrapped result's sign bit, not
  // signed comparison of the incoming index. In particular 0x80000000 is
  // an ordinary cache slot whereas 0x80000001 routes to undo.
  const std::uint32_t slot = static_cast<std::uint32_t>(index) - 1U;
  if (slot & UINT32_C(0x80000000))
    return getUndoFileName();
  auto &manager =
      presetNames ? *presetNames : Panel::PresetNameManager::instance();
  if (auto *cache = manager.lookupCache(getName()))
    return cache->buildFileName(slot, "mixscene", "", nullptr, true);
  return Core::Portable::FileName("");
}

Core::Portable::FileName StormMixSceneComponent::getUndoFileName() const {
  // The native guard covers only construction of the empty FileName. Keep
  // lazy population outside that guard: a thrown provider leaves its current
  // partial path, as in the original. Concurrent population is not supported.
  static Core::Portable::FileName s_path;
  if (s_path.isEmpty()) {
    s_path = getFileName(1);
    Core::Portable::FileName name;
    s_path.getName(name);
    // Deliberately the first substring, even if the basename also occurs in
    // an ancestor. Do not canonicalize this into an ordinary parent lookup.
    if (const char *match = std::strstr(s_path.str(), name.str())) {
      const auto index = match - s_path.str() - 1;
      if (index >= 0 && index < s_path.length())
        s_path.truncate(static_cast<int>(index));
    }
    s_path.descend("undo");
    // The original ignores directory-creation failure and still caches the
    // final path. An empty missing-cache result consequently yields /undo.
    (void)Core::Portable::FileUtils::makeDirectory(s_path.str());
    s_path.descend("mixscene.undo");
  }
  return s_path;
}
} // namespace Presonus
