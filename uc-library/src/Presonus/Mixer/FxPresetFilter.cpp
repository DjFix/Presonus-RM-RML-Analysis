#include "presonus/mixer/FxPresetFilter.hpp"
#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/StorageFilterForwarding.hpp"
#include <cstring>
using namespace Core::Portable;
namespace Presonus::Mixer {
bool FxPresetFilter::shouldLoad(int typeId, const char *name,
                                void *object) const {
  return typeId != Parameter::kTypeID || !object ||
         std::strcmp(static_cast<Parameter *>(object)->getName()
                         ? static_cast<Parameter *>(object)->getName()
                         : "",
                     "loaded_num") != 0;
}
bool FxPresetFilter::shouldSave(int typeId, const char *name,
                                void *object) const {
  return presonus::mixer::forwardStorageSave(*this, typeId, name, object);
}
} // namespace Presonus::Mixer
