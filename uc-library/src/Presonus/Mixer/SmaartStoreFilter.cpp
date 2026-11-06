#include "presonus/mixer/SmaartStoreFilter.hpp"
#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/StorageFilterForwarding.hpp"
#include <cstring>
using namespace Core::Portable;
namespace Presonus::Mixer {
bool SmaartStoreFilter::shouldLoad(int typeId, const char *name,
                                   void *object) const {
  if (typeId == Parameter::kTypeID) {
    if (!object)
      return true;
    int tag = static_cast<Parameter *>(object)->getTag();
    return tag != 400 && tag != 420;
  }
  if (typeId != Component::kTypeID || !name || std::strcmp(name, "eq") != 0)
    return true;
  // Native eq/null-object dereferences invalid memory; outside validated
  // domain.
  if (!object)
    return false;
  auto *component = static_cast<Component *>(object);
  auto *controller =
      core_cast<ChannelParameterController>(component->getParent());
  return controller && static_cast<unsigned>(controller->channelIndex()) == 0;
}
bool SmaartStoreFilter::shouldSave(int typeId, const char *name,
                                   void *object) const {
  return presonus::mixer::forwardStorageSave(*this, typeId, name, object);
}
} // namespace Presonus::Mixer
