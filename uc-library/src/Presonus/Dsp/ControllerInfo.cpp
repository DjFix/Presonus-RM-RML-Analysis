#include "presonus/dsp/ControllerInfo.hpp"
#include <cstdio>
namespace Presonus::Dsp {
void Controller::printValue(Presonus::StringResult &result, int tag,
                            float value) const {
  const auto &state = descriptor(tag).sourceState();
  if (state.formatter) {
    Core::Formatter::Range range{
        state.interpolator ? state.interpolator->getMinRange() : 0.f,
        state.interpolator ? state.interpolator->getMaxRange() : 1.f};
    Core::Formatter::Data data{nullptr, result.buffer, result.capacity, value,
                               &range};
    state.formatter->print(data);
  } else if (state.word10) {
    // Bounded domain: finite values representable as int32 after truncation.
    std::snprintf(result.buffer, result.capacity, "%d",
                  static_cast<int>(value));
  } else {
    std::snprintf(result.buffer, result.capacity, "%.2f",
                  static_cast<double>(value));
  }
}
void Controller::getParameterInfo(ParamInfo &info, int index) const {
  const auto requested = info.flags & 0x20u;
  const ParamDescriptor *selected = nullptr;
  // Native info lookup always uses the index, independently of tag mode.
  if (state_.descriptors)
    selected = state_.descriptors->at(index);
  const auto &state =
      (selected ? selected : ParamDescriptorList::getError())->sourceState();
  info.tag = state.tag;
  info.text0 = state.text0;
  info.text1 = state.text1;
  info.flags = state.flags;
  info.word10 = state.word10;
  info.word14 = state.word14;
  if (!state_.descriptors) {
    info.flags |= requested;
    return;
  }
  info.flags = (info.flags & ~(0x10000u | 0x20u)) | requested;
  if (static_cast<std::uint32_t>(state.tag) == state_.word08)
    info.flags |= 8u;
  if ((info.flags & 0x20u) && info.byteSize > 31u)
    info.text2 = state.text2;
}
float Controller::getValue(int) const { return 0.f; }
bool Controller::scanValue(float &value, int tag, const char *input) const {
  const auto &state = descriptor(tag).sourceState();
  value = 0.f;
  if (state.formatter) {
    Core::Formatter::Range range{
        state.interpolator ? state.interpolator->getMinRange() : 0.f,
        state.interpolator ? state.interpolator->getMaxRange() : 1.f};
    // CCL's scan API borrows a char*, while the original input is const.
    Core::Formatter::Data data{nullptr, const_cast<char *>(input), -1, 0.f,
                               &range};
    if (!state.formatter->scan(data))
      return false;
    value = data.value;
    return true;
  }
  return std::sscanf(input, "%f", &value) == 1;
}
} // namespace Presonus::Dsp
