#include "presonus/panel/GeqPresetComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstring>

namespace Presonus::Panel {
GeqPresetComponent::~GeqPresetComponent() = default;
bool GeqPresetComponent::store() {
  const int index = state.selection ? integerValue(*state.selection) : 0;
  if (index < 0 || index >= state.equalizers.count())
    return false;
  auto *equalizer = state.equalizers.at(index);
  if (!equalizer)
    return false;

  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::AttributesBuilder builder(attributes);
  Core::Portable::OutputStorage storage(builder);
  storage.setMode("ignoreAltMemory");
  equalizer->save(storage);

  Core::CString256 name;
  required(*this, 2).toString(name.getBuffer(), name.getSize());
  doPresetSave(name, "", attributes);
  return true;
}
bool GeqPresetComponent::recall(Core::Portable::Attributes &attributes, bool) {
  const int index = state.selection ? integerValue(*state.selection) : 0;
  if (index < 0 || index >= state.equalizers.count())
    return false;
  auto *equalizer = state.equalizers.at(index);
  if (!equalizer)
    return false;
  Core::Portable::InputStorage storage(attributes);
  storage.setMode("ignoreAltMemory");
  if (!equalizer->load(storage))
    return false;
  presetRecalled();
  return true;
}
} // namespace Presonus::Panel
