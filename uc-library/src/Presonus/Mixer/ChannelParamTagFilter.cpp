#include "presonus/mixer/ChannelParamTagFilter.hpp"
#include "core/portable/coreparams.h"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/StorageFilterForwarding.hpp"
#include <cstring>
using namespace Core::Portable;
namespace Presonus::Mixer {
bool ChannelParamTagFilter::shouldLoad(int typeId, const char *name,
                                       void *object) const {
  if (typeId != Parameter::kTypeID)
    return true;
  if (!object)
    return false;
  auto *parameter = static_cast<Parameter *>(object);
  auto *controller =
      core_cast<ChannelParameterController>(parameter->getController());
  return controller && parameter->getTag() == tag_ &&
         (channelIndex_ < 0 || controller->channelIndex() == channelIndex_);
}
bool ChannelParamTagFilter::shouldSave(int typeId, const char *name,
                                       void *object) const {
  return presonus::mixer::forwardStorageSave(*this, typeId, name, object);
}
} // namespace Presonus::Mixer
