#include "presonus/AltMemoryFilter.hpp"
#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/StorageFilterForwarding.hpp"
#include <cstring>
using namespace Core::Portable;
bool AltMemoryFilter::shouldLoad(int typeId, const char *name,
                                 void *object) const {
  return typeId != Parameter::kTypeID ||
         (object && static_cast<Parameter *>(object)->isUserFlag1());
}
bool AltMemoryFilter::shouldSave(int typeId, const char *name,
                                 void *object) const {
  return presonus::mixer::forwardStorageSave(*this, typeId, name, object);
}
