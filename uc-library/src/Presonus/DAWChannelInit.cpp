#include "presonus/DAWChannel.hpp"

#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/mixer_dsp/Formatters.hpp"

#include <iterator>

namespace Presonus {
namespace {

using Core::Portable::Parameter;
using Core::Portable::ParamInfo;

constexpr ParamInfo channelExtensions[] = {
    {ParamInfo::kFloat, 1000, "combined-meter", 0, 1, 0, 0, 0, 0, nullptr,
     nullptr, nullptr, nullptr, nullptr},
    {ParamInfo::kInt, 1001, "input-select-inc-dec", -1, 1, 0, 0, 1, 0, nullptr,
     nullptr, nullptr, nullptr, nullptr},
    {ParamInfo::kInt, 1002, "output-select-inc-dec", -1, 1, 0, 0, 1, 0, nullptr,
     nullptr, nullptr, nullptr, nullptr},
};

void enableFeedback(Parameter *parameter) {
  if (parameter)
    parameter->setFeedbackNeeded(true);
}

} // namespace

void DAWChannel::init(bool removeControls) {
  if (removeControls) {
    for (int tag : {8, 9, 5, 21, 18}) {
      if (auto *parameter = paramList.byTag(tag)) {
        paramList.remove(parameter);
        delete parameter;
      }
    }
  }

  static Dsp::GainDBFormatter gainFormatter(true);
  if (auto *gain = paramList.byTag(8))
    gain->setFormatter(&gainFormatter);

  cachedParameters_[channelStateCache] = paramList.byTag(0);
  enableFeedback(cachedParameters_[channelStateCache]);
  cachedParameters_[idCache] = paramList.byTag(22);
  enableFeedback(cachedParameters_[idCache]);
  enableFeedback(paramList.byTag(18));
  enableFeedback(paramList.byTag(5));
  cachedParameters_[selectedCache] = paramList.byTag(6);
  enableFeedback(cachedParameters_[selectedCache]);
  enableFeedback(paramList.byTag(23));

  if (auto *range = paramList.byTag(21)) {
    range->setMin(0.f);
    range->setMax(1.f);
  }

  paramList.add(channelExtensions,
                static_cast<int>(std::size(channelExtensions)), false);

  const int childCount = countChildren();
  for (int index = 0; index < childCount; ++index) {
    if (auto *child = getChild(index)) {
      if (auto *folder = static_cast<DAWDeviceFolder *>(
              child->castTo(DAWDeviceFolder::kTypeID)))
        folder->init();
    }
  }
}

} // namespace Presonus
