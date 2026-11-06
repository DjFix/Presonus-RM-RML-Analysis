#include "presonus/mixer/GEQPresetFilter.hpp"
#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/StorageFilterForwarding.hpp"
#include <cstring>
using namespace Core::Portable;
namespace Presonus::Mixer {
bool GEQPresetFilter::shouldLoad(int typeId, const char *name,
                                 void *object) const {
  if (typeId == Component::kTypeID)
    return true;
  if (typeId != Parameter::kTypeID)
    return false;
  const char *value = name ? name : "";
  return std::strncmp(value, "gain", 4) == 0 || std::strcmp(value, "on") == 0;
}
bool GEQPresetFilter::shouldSave(int typeId, const char *name,
                                 void *object) const {
  return presonus::mixer::forwardStorageSave(*this, typeId, name, object);
}
} // namespace Presonus::Mixer
